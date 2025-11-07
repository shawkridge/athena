/**
 * Code Executor
 *
 * Main execution pipeline orchestrator.
 * Coordinates validation, execution, filtering, and result return.
 *
 * Execution Flow:
 * 1. Validate code (syntax, patterns, AST)
 * 2. Prepare code (inject session context, tool imports)
 * 3. Execute in sandbox (Deno worker with limits)
 * 4. Filter output (remove secrets, tokenize PII, compress)
 * 5. Validate result (check size, format)
 * 6. Return to client
 *
 * @see docs/MCP_CODE_EXECUTION_ARCHITECTURE.md for design
 * @see src/runtime/deno_executor.ts for sandbox
 */

import { CodeValidator, ValidationResult } from "./code_validator.ts";
import { DenoExecutor, ExecutionContext, ExecutionResult } from "../runtime/deno_executor.ts";
import type {
  CodeExecutionRequest,
  CodeExecutionResult,
  ExecutionError,
  ToolContext,
} from "../interfaces/execution.ts";

/**
 * Executor Configuration
 */
export interface ExecutorConfig {
  /** Enable code validation */
  validateCode: boolean;

  /** Maximum code length */
  maxCodeLength: number;

  /** Enable output filtering */
  enableOutputFiltering: boolean;

  /** Maximum result size */
  maxResultSize: number;

  /** Default timeout (ms) */
  defaultTimeout: number;

  /** Log level */
  logLevel: "debug" | "info" | "warn" | "error";
}

/**
 * Code Executor
 *
 * Orchestrates the complete code execution pipeline.
 */
export class CodeExecutor {
  private validator: CodeValidator;
  private denoExecutor: DenoExecutor;
  private config: ExecutorConfig;

  constructor(
    denoExecutor: DenoExecutor,
    config: Partial<ExecutorConfig> = {}
  ) {
    this.denoExecutor = denoExecutor;

    this.config = {
      validateCode: true,
      maxCodeLength: 100 * 1024,
      enableOutputFiltering: true,
      maxResultSize: 10 * 1024 * 1024, // 10MB
      defaultTimeout: 5000,
      logLevel: "info",
      ...config,
    };

    // Initialize validator
    this.validator = new CodeValidator({
      maxCodeLength: this.config.maxCodeLength,
    });
  }

  /**
   * Execute code with complete pipeline
   */
  async execute(
    request: CodeExecutionRequest,
    toolContext: ToolContext
  ): Promise<CodeExecutionResult> {
    const executionId = this.generateExecutionId();
    const startTime = Date.now();

    try {
      this.log(
        "info",
        `Starting execution: ${executionId}`
      );

      // Step 1: Validate code
      if (this.config.validateCode) {
        const validation = this.validator.validate(request.code);
        if (!validation.valid) {
          return {
            success: false,
            output: null,
            errors: validation.errors.map((e) => ({
              type: "validation_error" as const,
              message: e.message,
              details: { line: e.line, column: e.column },
            })),
            logs: [],
            metrics: {
              executionTimeMs: Date.now() - startTime,
              memoryPeakMb: 0,
              toolCallsCount: 0,
              avgToolLatencyMs: 0,
              timeoutCount: 0,
              errorCount: 1,
              resultSizeBytes: 0,
            },
            sessionState: toolContext.sessionState,
          };
        }

        this.log(
          "debug",
          `Code validation passed (${validation.metrics.codeSize} bytes)`
        );
      }

      // Step 2: Prepare code (inject context, imports)
      const preparedCode = this.prepareCode(request.code, toolContext);

      // Step 3: Execute in sandbox
      const executionContext: ExecutionContext = {
        id: executionId,
        sessionId: toolContext.sessionId,
        code: preparedCode,
        timeout: request.timeout || this.config.defaultTimeout,
        memoryLimit: 100,
        maxResultSize: request.maxResultSize || this.config.maxResultSize,
        toolContext,
      };

      const executionResult = await this.denoExecutor.execute(executionContext);

      this.log(
        "debug",
        `Execution completed: ${executionId} (${executionResult.metrics.executionTimeMs}ms)`
      );

      // Step 4: Filter output if enabled
      let filteredOutput = executionResult.output;
      let wasFiltered = false;
      let originalSize = JSON.stringify(executionResult.output).length;
      let filteredSize = originalSize;

      if (this.config.enableOutputFiltering && executionResult.success) {
        const filterResult = this.filterOutput(
          executionResult.output,
          toolContext
        );
        filteredOutput = filterResult.output;
        wasFiltered = filterResult.wasFiltered;
        filteredSize = JSON.stringify(filteredOutput).length;

        this.log(
          "debug",
          `Output filtering: ${originalSize}B → ${filteredSize}B (filtered: ${wasFiltered})`
        );
      }

      // Step 5: Validate result size
      if (filteredSize > this.config.maxResultSize) {
        return {
          success: false,
          output: null,
          errors: [
            {
              type: "resource_error",
              message: `Result size exceeds limit: ${filteredSize} > ${this.config.maxResultSize} bytes`,
            },
          ],
          logs: executionResult.logs,
          metrics: executionResult.metrics,
          sessionState: toolContext.sessionState,
        };
      }

      // Step 6: Return result
      return {
        success: executionResult.success,
        output: filteredOutput,
        errors: executionResult.error ? [executionResult.error] : [],
        logs: executionResult.logs,
        metrics: executionResult.metrics,
        sessionState: toolContext.sessionState,
        wasFiltered,
        originalSizeBytes: originalSize,
        filteredSizeBytes: filteredSize,
      };
    } catch (error) {
      this.log(
        "error",
        `Execution failed: ${executionId}: ${error}`
      );

      return {
        success: false,
        output: null,
        errors: [
          {
            type: "runtime_error",
            message: `Execution failed: ${error}`,
          },
        ],
        logs: [],
        metrics: {
          executionTimeMs: Date.now() - startTime,
          memoryPeakMb: 0,
          toolCallsCount: 0,
          avgToolLatencyMs: 0,
          timeoutCount: 0,
          errorCount: 1,
          resultSizeBytes: 0,
        },
        sessionState: toolContext.sessionState,
      };
    }
  }

  /**
   * Prepare code by injecting session context and tool imports
   */
  private prepareCode(code: string, toolContext: ToolContext): string {
    // Wrap code with session context
    return `
// Auto-generated session context
const __SESSION_ID__ = '${toolContext.sessionId}';
const __TOOLS__ = ${JSON.stringify(this.serializeToolContext(toolContext))};
const __STATE__ = ${JSON.stringify(toolContext.sessionState || {})};

// User code
${code}
`;
  }

  /**
   * Serialize tool context for injection
   */
  private serializeToolContext(context: ToolContext): any {
    return {
      sessionId: context.sessionId,
      userId: context.userId,
      toolNames: context.availableTools?.map((t) => t.id) || [],
    };
  }

  /**
   * Filter output to remove sensitive data
   */
  private filterOutput(
    output: unknown,
    toolContext: ToolContext
  ): {
    output: unknown;
    wasFiltered: boolean;
  } {
    if (!output || typeof output !== "object") {
      return { output, wasFiltered: false };
    }

    // Simple filtering: remove common sensitive field names
    const sensitiveFields = [
      "password",
      "token",
      "api_key",
      "apiKey",
      "secret",
      "auth",
      "authorization",
      "access_token",
      "refresh_token",
    ];

    let wasFiltered = false;
    const filtered = this.recursiveFilter(output, sensitiveFields);

    return { output: filtered, wasFiltered };
  }

  /**
   * Recursively filter sensitive fields from object
   */
  private recursiveFilter(
    obj: any,
    sensitiveFields: string[]
  ): any {
    if (obj === null || obj === undefined) {
      return obj;
    }

    if (typeof obj !== "object") {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map((item) =>
        this.recursiveFilter(item, sensitiveFields)
      );
    }

    const filtered: any = {};
    for (const [key, value] of Object.entries(obj)) {
      if (
        sensitiveFields.some(
          (field) =>
            key.toLowerCase().includes(field.toLowerCase())
        )
      ) {
        filtered[key] = "[REDACTED]";
      } else if (typeof value === "object" && value !== null) {
        filtered[key] = this.recursiveFilter(value, sensitiveFields);
      } else {
        filtered[key] = value;
      }
    }

    return filtered;
  }

  /**
   * Generate unique execution ID
   */
  private generateExecutionId(): string {
    return `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Log message
   */
  private log(level: string, message: string): void {
    if (
      (level === "debug" && this.config.logLevel === "debug") ||
      (["info", "warn", "error"].includes(level) &&
        ["debug", "info", "warn", "error"].includes(this.config.logLevel))
    ) {
      console.log(`[CodeExecutor] [${level.toUpperCase()}] ${message}`);
    }
  }
}

export default CodeExecutor;
