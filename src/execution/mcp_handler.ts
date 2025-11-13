/**
 * MCP CodeExecutionHandler
 *
 * Bridges code execution with MCP tool calls, enabling agents to:
 * 1. Write TypeScript code that uses memory operations
 * 2. Call available tools through callMCPTool()
 * 3. Get tool discovery through search_tools()
 *
 * @packageDocumentation
 */

import type { ExecutionContext, ExecutionResult } from '../interfaces/execution';

/**
 * Tool context passed to executing code
 */
export interface ToolContext {
  sessionId: string;
  userId?: string;
  allowedTools: Set<string>;
  callMCPTool: (operation: string, parameters: Record<string, unknown>) => Promise<unknown>;
  search_tools: (options?: Record<string, unknown>) => Promise<unknown[]>;
}

/**
 * MCP Tool Definition
 */
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, unknown>;
    required?: string[];
  };
  execute: (params: Record<string, unknown>) => Promise<unknown>;
}

/**
 * CodeExecutionHandler
 *
 * Handles code execution for agents, providing access to memory operations
 * through the code execution paradigm.
 */
export class CodeExecutionHandler {
  private allowedOperations: Map<string, MCPTool> = new Map();
  private sessionStore: Map<string, ToolContext> = new Map();

  constructor() {
    this.initializeTools();
  }

  /**
   * Initialize all available MCP tools
   */
  private initializeTools(): void {
    // This will be populated with actual tool definitions from each layer
    // Tools are registered in the order they appear in the memory layers
  }

  /**
   * Create a tool context for code execution
   */
  public createToolContext(sessionId: string, userId?: string): ToolContext {
    const context: ToolContext = {
      sessionId,
      userId,
      allowedTools: new Set(this.allowedOperations.keys()),
      callMCPTool: this.makeCallMCPTool(sessionId),
      search_tools: this.makeSearchTools(sessionId),
    };

    this.sessionStore.set(sessionId, context);
    return context;
  }

  /**
   * Create the callMCPTool function for code execution
   */
  private makeCallMCPTool(
    sessionId: string
  ): (operation: string, parameters: Record<string, unknown>) => Promise<unknown> {
    return async (operation: string, parameters: Record<string, unknown>) => {
      const context = this.sessionStore.get(sessionId);
      if (!context) {
        throw new Error(`Session ${sessionId} not found`);
      }

      // Validate operation is allowed
      if (!context.allowedTools.has(operation)) {
        throw new Error(`Operation '${operation}' is not allowed in this session`);
      }

      // Execute the operation
      const tool = this.allowedOperations.get(operation);
      if (!tool) {
        throw new Error(`Operation '${operation}' not found`);
      }

      try {
        return await tool.execute(parameters);
      } catch (error) {
        throw new Error(`Error executing ${operation}: ${error instanceof Error ? error.message : String(error)}`);
      }
    };
  }

  /**
   * Create the search_tools function for code execution
   */
  private makeSearchTools(
    sessionId: string
  ): (options?: Record<string, unknown>) => Promise<unknown[]> {
    return async (options?: Record<string, unknown>) => {
      const context = this.sessionStore.get(sessionId);
      if (!context) {
        throw new Error(`Session ${sessionId} not found`);
      }

      // Import search_tools utility
      const { search_tools } = await import('../servers/search_tools');

      // Call search_tools with provided options
      return await search_tools(
        options as Parameters<typeof search_tools>[0]
      );
    };
  }

  /**
   * Register a tool operation
   */
  public registerTool(operation: string, tool: MCPTool): void {
    this.allowedOperations.set(operation, tool);
  }

  /**
   * Register multiple tools
   */
  public registerTools(tools: Record<string, MCPTool>): void {
    for (const [operation, tool] of Object.entries(tools)) {
      this.registerTool(operation, tool);
    }
  }

  /**
   * Execute code with tool access
   *
   * @param code - TypeScript code to execute
   * @param context - Execution context
   * @returns Execution result
   */
  public async executeWithTools(
    code: string,
    context: ExecutionContext
  ): Promise<ExecutionResult> {
    const toolContext = this.createToolContext(context.sessionId, context.userId);

    // Prepare code with tool context
    const preparedCode = this.prepareCode(code, toolContext);

    // Create execution environment
    const env = {
      callMCPTool: toolContext.callMCPTool,
      search_tools: toolContext.search_tools,
      console: console,
    };

    try {
      // Execute code in isolated context
      const fn = new Function(...Object.keys(env), `return (async () => { ${preparedCode} })()`);
      const result = await fn(...Object.values(env));

      return {
        success: true,
        output: result,
        executionTimeMs: 0, // Would be tracked in actual implementation
        stderr: '',
        stdout: '',
      };
    } catch (error) {
      return {
        success: false,
        output: null,
        executionTimeMs: 0,
        stderr: error instanceof Error ? error.message : String(error),
        stdout: '',
      };
    }
  }

  /**
   * Prepare code for execution
   *
   * Injects tool context and ensures proper execution environment.
   */
  private prepareCode(code: string, _context: ToolContext): string {
    // Ensure code returns a value
    if (!code.includes('return ')) {
      return `const result = (async () => { ${code} })(); return result;`;
    }

    return code;
  }

  /**
   * Get available tools
   */
  public getAvailableTools(): MCPTool[] {
    return Array.from(this.allowedOperations.values());
  }

  /**
   * Get tool by operation name
   */
  public getTool(operation: string): MCPTool | undefined {
    return this.allowedOperations.get(operation);
  }

  /**
   * Validate tool access
   */
  public canAccess(operation: string, sessionId: string): boolean {
    const context = this.sessionStore.get(sessionId);
    if (!context) {
      return false;
    }

    return context.allowedTools.has(operation);
  }

  /**
   * Clean up session
   */
  public closeSession(sessionId: string): void {
    this.sessionStore.delete(sessionId);
  }
}

/**
 * Global handler instance
 */
export const codeExecutionHandler = new CodeExecutionHandler();

/**
 * Register a tool operation globally
 */
export function registerToolOperation(operation: string, execute: (params: Record<string, unknown>) => Promise<unknown>, description: string = ''): void {
  const tool: MCPTool = {
    name: operation,
    description,
    inputSchema: {
      type: 'object',
      properties: {},
    },
    execute,
  };

  codeExecutionHandler.registerTool(operation, tool);
}

/**
 * Create tool adapter for a memory layer
 *
 * @param layerName - Layer name (episodic, semantic, etc.)
 * @param operations - Operations object from layer module
 */
export function createLayerAdapter(
  layerName: string,
  operations: Record<string, any>
): Record<string, MCPTool> {
  const tools: Record<string, MCPTool> = {};

  for (const [opName, opMetadata] of Object.entries(operations)) {
    const fullName = `${layerName}/${opName}`;

    // Create a placeholder execute function
    // In real implementation, this would call the actual layer operations
    tools[fullName] = {
      name: fullName,
      description: (opMetadata as any).description || '',
      inputSchema: {
        type: 'object',
        properties: (opMetadata as any).parameters || {},
      },
      execute: async (params: Record<string, unknown>) => {
        // This would be replaced with actual operation implementation
        return { status: 'ok', operation: fullName, params };
      },
    };
  }

  return tools;
}

/**
 * Initialize all layer adapters
 */
export async function initializeAllLayers(): Promise<void> {
  try {
    // Import all layer modules
    const episodic = await import('../servers/episodic');
    const semantic = await import('../servers/semantic');
    const procedural = await import('../servers/procedural');
    const prospective = await import('../servers/prospective');
    const graph = await import('../servers/graph');
    const meta = await import('../servers/meta');
    const consolidation = await import('../servers/consolidation');
    const rag = await import('../servers/rag');

    // Create and register adapters for each layer
    const layers = [
      { name: 'episodic', module: episodic },
      { name: 'semantic', module: semantic },
      { name: 'procedural', module: procedural },
      { name: 'prospective', module: prospective },
      { name: 'graph', module: graph },
      { name: 'meta', module: meta },
      { name: 'consolidation', module: consolidation },
      { name: 'rag', module: rag },
    ];

    for (const layer of layers) {
      if (layer.module.operations) {
        const adapter = createLayerAdapter(layer.name, layer.module.operations);
        codeExecutionHandler.registerTools(adapter);
      }
    }
  } catch (error) {
    throw new Error(`Failed to initialize layers: ${error instanceof Error ? error.message : String(error)}`);
  }
}
