"""Specialized agents for modern code analysis tools.

These agents handle complex multi-step tasks using ripgrep, ast-grep, tree-sitter, and semgrep.
"""

import logging
from typing import Any, List, Dict, Optional
from pathlib import Path

from mcp.types import TextContent

from athena.code.modern_tools import (
    RipgrepSearcher,
    AstGrepSearcher,
    ModernCodeAnalyzer,
)
from athena.code.enhanced_parser import EnhancedCodeParser

logger = logging.getLogger(__name__)


class CodeDiscoveryAgent:
    """Agent for discovering code patterns and structure across repositories."""

    def __init__(self):
        """Initialize code discovery agent."""
        self.analyzer = ModernCodeAnalyzer()
        self.parser = EnhancedCodeParser()

    async def discover_code_structure(self, directory: str) -> Dict[str, Any]:
        """Discover code structure using modern tools.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary with code structure information
        """
        results = {
            "directory": directory,
            "imports": 0,
            "functions": 0,
            "classes": 0,
            "status": "analyzing",
        }

        try:
            if self.analyzer.ripgrep.rg_available:
                # Find imports
                imports = self.analyzer.ripgrep.find_imports(directory, file_type="ts")
                results["imports"] = len(imports)

                # Find functions
                functions = self.analyzer.ripgrep.find_functions(directory, file_type="ts")
                results["functions"] = len(functions)

                results["status"] = "success"
        except Exception as e:
            logger.error(f"Error discovering code structure: {e}")
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def find_patterns(self, pattern: str, directory: str, language: str = "typescript") -> Dict[str, Any]:
        """Find specific patterns in code using ast-grep.

        Args:
            pattern: AST pattern to search for
            directory: Directory to search
            language: Programming language

        Returns:
            Dictionary with pattern matching results
        """
        results = {
            "pattern": pattern,
            "directory": directory,
            "language": language,
            "matches": 0,
            "status": "analyzing",
        }

        try:
            if self.analyzer.astgrep.available:
                matches = self.analyzer.astgrep.search(pattern, language, directory)
                results["matches"] = len(matches)
                results["sample_matches"] = matches[:5] if matches else []
                results["status"] = "success"
            else:
                results["status"] = "ast-grep not available"
        except Exception as e:
            logger.error(f"Error finding patterns: {e}")
            results["status"] = "error"
            results["error"] = str(e)

        return results


class SecurityScanAgent:
    """Agent for security scanning and vulnerability detection."""

    def __init__(self):
        """Initialize security scan agent."""
        self.analyzer = ModernCodeAnalyzer()

    async def scan_for_vulnerabilities(self, directory: str, rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scan for security vulnerabilities using semgrep.

        Args:
            directory: Directory to scan
            rules: Optional list of specific rules to run

        Returns:
            Dictionary with security scan results
        """
        results = {
            "directory": directory,
            "vulnerabilities": 0,
            "status": "analyzing",
        }

        try:
            if self.analyzer.semgrep.available:
                scan_results = self.analyzer.semgrep.scan(directory, rules=rules)
                if "results" in scan_results:
                    vulnerabilities = scan_results.get("results", [])
                    results["vulnerabilities"] = len(vulnerabilities)
                    results["findings"] = vulnerabilities[:5]
                    results["status"] = "success"
                else:
                    results["status"] = "scan completed"
            else:
                results["status"] = "semgrep not installed"
                results["install_command"] = "pip install semgrep"
        except Exception as e:
            logger.error(f"Error scanning for vulnerabilities: {e}")
            results["status"] = "error"
            results["error"] = str(e)

        return results


class CodeRefactoringAgent:
    """Agent for identifying refactoring opportunities."""

    def __init__(self):
        """Initialize code refactoring agent."""
        self.analyzer = ModernCodeAnalyzer()

    async def identify_refactoring_opportunities(self, directory: str) -> Dict[str, Any]:
        """Identify code that could be refactored.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary with refactoring suggestions
        """
        results = {
            "directory": directory,
            "opportunities": [],
            "status": "analyzing",
        }

        try:
            # Look for common refactoring patterns
            patterns = {
                "duplicate_imports": r"^import.*\n.*\1",
                "unused_variables": r"const \w+ = .*;",
                "long_functions": r"function \w+.*{[\s\S]{2000,}}",
                "deeply_nested": r"{.*{.*{.*{.*{",
            }

            opportunities = []

            if self.analyzer.ripgrep.rg_available:
                # Check for duplicate imports (simplified)
                matches = self.analyzer.ripgrep.search(
                    r"^import", directory, file_type="ts"
                )
                if len(matches) > 20:
                    opportunities.append({
                        "type": "excessive_imports",
                        "count": len(matches),
                        "suggestion": "Consider consolidating imports",
                    })

            results["opportunities"] = opportunities
            results["status"] = "success"

        except Exception as e:
            logger.error(f"Error identifying refactoring opportunities: {e}")
            results["status"] = "error"
            results["error"] = str(e)

        return results


class CodeQualityAgent:
    """Agent for comprehensive code quality analysis."""

    def __init__(self):
        """Initialize code quality agent."""
        self.discovery_agent = CodeDiscoveryAgent()
        self.security_agent = SecurityScanAgent()
        self.refactoring_agent = CodeRefactoringAgent()

    async def analyze_code_quality(self, directory: str) -> Dict[str, Any]:
        """Comprehensive code quality analysis.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary with comprehensive quality report
        """
        report = {
            "directory": directory,
            "analysis_complete": False,
            "structure": {},
            "security": {},
            "refactoring": {},
            "overall_score": 0,
        }

        try:
            # Structure analysis
            structure = await self.discovery_agent.discover_code_structure(directory)
            report["structure"] = structure

            # Security scan
            security = await self.security_agent.scan_for_vulnerabilities(directory)
            report["security"] = security

            # Refactoring opportunities
            refactoring = await self.refactoring_agent.identify_refactoring_opportunities(directory)
            report["refactoring"] = refactoring

            # Calculate overall score
            score = 100
            if security["vulnerabilities"] > 0:
                score -= min(50, security["vulnerabilities"] * 5)
            if refactoring["opportunities"]:
                score -= len(refactoring["opportunities"]) * 10

            report["overall_score"] = max(0, score)
            report["analysis_complete"] = True

        except Exception as e:
            logger.error(f"Error in code quality analysis: {e}")
            report["error"] = str(e)

        return report


# Agent factory
def create_code_discovery_agent() -> CodeDiscoveryAgent:
    """Create a code discovery agent."""
    return CodeDiscoveryAgent()


def create_security_scan_agent() -> SecurityScanAgent:
    """Create a security scan agent."""
    return SecurityScanAgent()


def create_code_refactoring_agent() -> CodeRefactoringAgent:
    """Create a code refactoring agent."""
    return CodeRefactoringAgent()


def create_code_quality_agent() -> CodeQualityAgent:
    """Create a comprehensive code quality agent."""
    return CodeQualityAgent()


# Async wrapper functions for MCP handlers
async def handle_discover_code_structure(directory: str) -> Dict[str, Any]:
    """Handle code structure discovery."""
    agent = create_code_discovery_agent()
    return await agent.discover_code_structure(directory)


async def handle_find_code_patterns(
    pattern: str, directory: str, language: str = "typescript"
) -> Dict[str, Any]:
    """Handle pattern finding."""
    agent = create_code_discovery_agent()
    return await agent.find_patterns(pattern, directory, language)


async def handle_scan_security(directory: str, rules: Optional[List[str]] = None) -> Dict[str, Any]:
    """Handle security scanning."""
    agent = create_security_scan_agent()
    return await agent.scan_for_vulnerabilities(directory, rules)


async def handle_analyze_quality(directory: str) -> Dict[str, Any]:
    """Handle code quality analysis."""
    agent = create_code_quality_agent()
    return await agent.analyze_code_quality(directory)
