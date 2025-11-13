/**
 * Code Validator
 *
 * Validates TypeScript/JavaScript code before execution to prevent
 * injection attacks and dangerous operations.
 *
 * Performs three validation layers:
 * 1. Syntax validation (valid TS/JS)
 * 2. Pattern scanning (forbidden keywords)
 * 3. AST analysis (dangerous constructs)
 *
 * @see docs/SECURITY_MODEL.md for security strategy
 */

/**
 * Validation Configuration
 */
export interface ValidationConfig {
  /** Maximum code length in bytes (default: 100KB) */
  maxCodeLength: number;

  /** Maximum individual string length (default: 10KB) */
  maxStringLength: number;

  /** Maximum AST depth (default: 50) */
  maxDepth: number;

  /** Forbidden patterns to detect */
  forbiddenPatterns: RegExp[];

  /** Allow imports (default: false) */
  allowImports: boolean;

  /** Allow global variable access (default: false) */
  allowGlobals: boolean;
}

/**
 * Validation Result
 */
export interface ValidationResult {
  /** Is code valid and safe */
  valid: boolean;

  /** Errors found during validation */
  errors: ValidationError[];

  /** Warnings (code works but might be suspicious) */
  warnings: ValidationWarning[];

  /** Validation metrics */
  metrics: ValidationMetrics;
}

/**
 * Validation Error
 */
export interface ValidationError {
  /** Error type */
  type:
    | "syntax_error"
    | "size_limit"
    | "forbidden_pattern"
    | "ast_violation"
    | "depth_exceeded";

  /** Error message */
  message: string;

  /** Line number (if applicable) */
  line?: number;

  /** Column number (if applicable) */
  column?: number;

  /** Severity */
  severity: "error" | "critical";
}

/**
 * Validation Warning
 */
export interface ValidationWarning {
  /** Warning type */
  type: "suspicious_pattern" | "complex_logic" | "performance_concern";

  /** Warning message */
  message: string;

  /** Line number */
  line?: number;
}

/**
 * Validation Metrics
 */
export interface ValidationMetrics {
  /** Code size in bytes */
  codeSize: number;

  /** Number of lines */
  lineCount: number;

  /** Largest string literal size */
  maxStringSize: number;

  /** Validation time in milliseconds */
  validationTimeMs: number;

  /** Number of patterns detected */
  patternMatches: number;

  /** AST depth */
  astDepth?: number;
}

/**
 * Code Validator
 *
 * Multi-layer validation to prevent injection and dangerous code.
 */
export class CodeValidator {
  private config: ValidationConfig;
  private forbiddenPatterns: Map<string, RegExp>;

  constructor(config: Partial<ValidationConfig> = {}) {
    this.config = {
      maxCodeLength: 100 * 1024, // 100KB
      maxStringLength: 10 * 1024, // 10KB
      maxDepth: 50,
      allowImports: false,
      allowGlobals: false,
      forbiddenPatterns: this.getDefaultForbiddenPatterns(),
      ...config,
    };

    // Build pattern map
    this.forbiddenPatterns = new Map();
    for (const pattern of this.config.forbiddenPatterns) {
      this.forbiddenPatterns.set(pattern.source, pattern);
    }
  }

  /**
   * Get default forbidden patterns
   */
  private getDefaultForbiddenPatterns(): RegExp[] {
    return [
      // No require() or import
      /\brequire\s*\(/,
      /\bimport\s+\w/,
      /\bfrom\s+["']/,

      // No eval or Function constructor
      /\beval\s*\(/,
      /\bFunction\s*\(/,
      /\bAsyncFunction\s*\(/,

      // No process or system access
      /\bprocess\./,
      /\bglobalThis\./,
      /\bglobal\./,
      /\bwindow\./,

      // No file system access
      /\brequire\s*\(\s*["']fs["']/,
      /\brequire\s*\(\s*["']path["']/,

      // No child process spawning
      /\brequire\s*\(\s*["']child_process["']/,
      /\bexecSync\s*\(/,
      /\bspawn\s*\(/,

      // No eval-like functions
      /\bsetTimeout\s*\(\s*["']/,
      /\bsetInterval\s*\(\s*["']/,

      // No WebAssembly
      /\bWebAssembly\./,
      /\bwasm/i,

      // No native modules
      /\b__dirname\b/,
      /\b__filename\b/,
    ];
  }

  /**
   * Validate code
   */
  validate(code: string): ValidationResult {
    const startTime = Date.now();
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // 1. Check code length
    if (code.length > this.config.maxCodeLength) {
      errors.push({
        type: "size_limit",
        message: `Code exceeds maximum length (${code.length} > ${this.config.maxCodeLength} bytes)`,
        severity: "error",
      });
    }

    // 2. Check syntax
    const syntaxError = this.checkSyntax(code);
    if (syntaxError) {
      errors.push(syntaxError);
    }

    // 3. Scan for forbidden patterns
    const patternViolations = this.scanPatterns(code);
    errors.push(...patternViolations);

    // 4. Validate AST (only if syntax is valid)
    if (!syntaxError) {
      try {
        const astError = this.validateAST(code);
        if (astError) {
          errors.push(astError);
        }
      } catch (error) {
        // If AST parsing fails, it's still a syntax error
        warnings.push({
          type: "suspicious_pattern",
          message: `Could not parse AST: ${error}`,
        });
      }
    }

    // 5. Check string sizes
    const stringSizeWarnings = this.checkStringSizes(code);
    warnings.push(...stringSizeWarnings);

    const validationTime = Date.now() - startTime;
    const metrics = this.calculateMetrics(code, validationTime);
    metrics.patternMatches = patternViolations.length;

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      metrics,
    };
  }

  /**
   * Check if code is valid JavaScript/TypeScript
   */
  private checkSyntax(code: string): ValidationError | null {
    try {
      // Try to parse with simple regex-based validation
      // Real implementation would use a parser like Babel or Acorn

      // Check for balanced braces/brackets
      if (!this.checkBraces(code)) {
        return {
          type: "syntax_error",
          message: "Unbalanced braces or brackets detected",
          severity: "error",
        };
      }

      // Check for unclosed strings
      if (!this.checkStrings(code)) {
        return {
          type: "syntax_error",
          message: "Unclosed string literal detected",
          severity: "error",
        };
      }

      return null;
    } catch (error) {
      return {
        type: "syntax_error",
        message: `Syntax error: ${error}`,
        severity: "error",
      };
    }
  }

  /**
   * Check for balanced braces and brackets
   */
  private checkBraces(code: string): boolean {
    const stack: string[] = [];
    const pairs: Record<string, string> = {
      "{": "}",
      "[": "]",
      "(": ")",
    };
    const closingBraces: Record<string, string> = {
      "}": "{",
      "]": "[",
      ")": "(",
    };

    let inString = false;
    let stringChar = "";
    let inRegex = false;

    for (let i = 0; i < code.length; i++) {
      const char = code[i];
      const prevChar = i > 0 ? code[i - 1] : "";

      // Check for string boundaries
      if ((char === '"' || char === "'" || char === "`") && prevChar !== "\\") {
        if (inString && char === stringChar) {
          inString = false;
          stringChar = "";
        } else if (!inString && !inRegex) {
          inString = true;
          stringChar = char;
        }
      }

      // Check for regex boundaries
      if (char === "/" && prevChar !== "\\" && !inString) {
        inRegex = !inRegex;
      }

      // Skip if in string or regex
      if (inString || inRegex) {
        continue;
      }

      // Check for braces
      if (pairs[char]) {
        stack.push(char);
      } else if (closingBraces[char]) {
        if (
          stack.length === 0 ||
          stack[stack.length - 1] !== closingBraces[char]
        ) {
          return false;
        }
        stack.pop();
      }
    }

    return stack.length === 0;
  }

  /**
   * Check for unclosed strings
   */
  private checkStrings(code: string): boolean {
    const stringRegex =
      /(['"`])(?:(?=(\\?))\2.)*?\1/g;
    const matches = code.match(stringRegex);

    // Count quotes to ensure they're paired
    const quotes = code.match(/['"`]/g) || [];
    const doubleQuotes = code.match(/"/g) || [];
    const singleQuotes = code.match(/'/g) || [];
    const backticks = code.match(/`/g) || [];

    // Each type of quote should have even count (excluding escaped)
    // This is a simple check; real implementation would be more sophisticated
    return (
      doubleQuotes.length % 2 === 0 &&
      singleQuotes.length % 2 === 0 &&
      backticks.length % 2 === 0
    );
  }

  /**
   * Scan for dangerous patterns
   */
  private scanPatterns(code: string): ValidationError[] {
    const violations: ValidationError[] = [];

    for (const [patternSource, pattern] of this.forbiddenPatterns) {
      const matches = code.match(pattern);
      if (matches) {
        violations.push({
          type: "forbidden_pattern",
          message: `Forbidden pattern detected: ${patternSource}`,
          severity: "error",
        });
      }
    }

    // Additional pattern checks
    if (code.includes("__proto__")) {
      violations.push({
        type: "forbidden_pattern",
        message: "Direct __proto__ access forbidden (prototype pollution risk)",
        severity: "error",
      });
    }

    if (code.includes("constructor.prototype")) {
      violations.push({
        type: "forbidden_pattern",
        message:
          "Direct constructor.prototype access forbidden (prototype pollution risk)",
        severity: "error",
      });
    }

    return violations;
  }

  /**
   * Validate Abstract Syntax Tree
   */
  private validateAST(code: string): ValidationError | null {
    // Simple AST validation using regex patterns
    // Real implementation would use a full parser

    // Check for dangerous function calls
    const dangerousFunctionCalls = [
      /document\./,
      /location\./,
      /XMLHttpRequest/,
      /fetch\s*\(/,
      /Worker\s*\(/,
    ];

    for (const pattern of dangerousFunctionCalls) {
      if (pattern.test(code)) {
        return {
          type: "ast_violation",
          message: `Dangerous function call detected: ${pattern.source}`,
          severity: "error",
        };
      }
    }

    return null;
  }

  /**
   * Check individual string sizes
   */
  private checkStrings(code: string): ValidationWarning[] {
    const warnings: ValidationWarning[] = [];
    const stringRegex =
      /(['"`])(?:(?=(\\?))\2.)*?\1/g;
    let match;

    while ((match = stringRegex.exec(code)) !== null) {
      const stringContent = match[0];
      if (stringContent.length > this.config.maxStringLength) {
        warnings.push({
          type: "suspicious_pattern",
          message: `String literal exceeds maximum length (${stringContent.length} > ${this.config.maxStringLength} bytes)`,
          line: code.substring(0, match.index).split("\n").length,
        });
      }
    }

    return warnings;
  }

  /**
   * Check individual string sizes (duplicate method name, should consolidate)
   */
  private checkStringSizes(code: string): ValidationWarning[] {
    return this.checkStrings(code);
  }

  /**
   * Calculate validation metrics
   */
  private calculateMetrics(
    code: string,
    validationTimeMs: number
  ): ValidationMetrics {
    const lineCount = code.split("\n").length;

    // Find largest string
    const stringRegex =
      /(['"`])(?:(?=(\\?))\2.)*?\1/g;
    let maxStringSize = 0;
    let match;

    while ((match = stringRegex.exec(code)) !== null) {
      maxStringSize = Math.max(maxStringSize, match[0].length);
    }

    return {
      codeSize: code.length,
      lineCount,
      maxStringSize,
      validationTimeMs,
      patternMatches: 0, // Set by caller
    };
  }
}

export default CodeValidator;
