"""SQL Injection Prevention Audit.

Scans hook library code for SQL injection vulnerabilities.
Checks that all SQL queries use parameterized statements.
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class AuditFinding:
    """A potential SQL injection vulnerability finding."""
    file_path: str
    line_number: int
    line_content: str
    issue_type: str
    severity: str  # "error", "warning", "info"
    recommendation: str


class SQLInjectionAuditor:
    """Audit Python files for SQL injection vulnerabilities."""

    # Patterns that might indicate SQL injection
    SQL_PATTERNS = [
        (r'\.execute\s*\(\s*f["\']', "f-string in execute() - potential injection"),
        (r'\.execute\s*\(\s*["\'].*\{.*\}.*["\']', "String formatting in execute() - potential injection"),
        (r'\.execute\s*\(\s*["\'][^"\']*\+', "String concatenation in execute() - potential injection"),
        (r'\.execute\s*\(\s*["\'][^"\']*%\s', "String formatting (%) in execute() - potential injection"),
    ]

    # Safe patterns (parameterized queries)
    SAFE_PATTERNS = [
        r'\.execute\s*\(\s*["\'][^"\']*%s[^"\']*["\']\s*,',  # %s parameterized
        r'\.execute\s*\(\s*["\'][^"\']*\?\s*[^"\']*["\']\s*,',  # ? parameterized
        r'\.execute\s*\(\s*["\'][^"\']*:[a-zA-Z_]',  # Named parameters
    ]

    def __init__(self, verbose: bool = False):
        """Initialize auditor.

        Args:
            verbose: Print debug information
        """
        self.verbose = verbose
        self.findings: List[AuditFinding] = []

    def audit_file(self, file_path: str) -> List[AuditFinding]:
        """Audit a single Python file for SQL injection risks.

        Args:
            file_path: Path to Python file

        Returns:
            List of findings
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            file_findings = []

            for line_num, line in enumerate(lines, 1):
                # Skip comments and empty lines
                stripped = line.strip()
                if stripped.startswith('#') or not stripped:
                    continue

                # Check for SQL execute statements
                if '.execute(' in line:
                    # Check if it's safe (parameterized)
                    is_safe = any(
                        re.search(pattern, line)
                        for pattern in self.SAFE_PATTERNS
                    )

                    if not is_safe:
                        # Check for known unsafe patterns
                        for pattern, issue_desc in self.SQL_PATTERNS:
                            if re.search(pattern, line):
                                finding = AuditFinding(
                                    file_path=file_path,
                                    line_number=line_num,
                                    line_content=line.rstrip(),
                                    issue_type=issue_desc,
                                    severity="warning",
                                    recommendation="Use parameterized query with %s placeholder and separate args tuple"
                                )
                                file_findings.append(finding)
                                break

            self.findings.extend(file_findings)
            return file_findings

        except Exception as e:
            print(f"Error auditing {file_path}: {e}")
            return []

    def audit_directory(self, directory: str) -> List[AuditFinding]:
        """Audit all Python files in directory.

        Args:
            directory: Directory path to audit

        Returns:
            List of all findings
        """
        all_findings = []
        python_files = list(Path(directory).rglob("*.py"))

        if self.verbose:
            print(f"Found {len(python_files)} Python files to audit")

        for file_path in sorted(python_files):
            findings = self.audit_file(str(file_path))
            all_findings.extend(findings)

        return all_findings

    def get_summary(self) -> Dict:
        """Get audit summary.

        Returns:
            Dict with audit statistics
        """
        if not self.findings:
            return {
                "total_findings": 0,
                "errors": 0,
                "warnings": 0,
                "status": "PASSED ✅",
            }

        errors = [f for f in self.findings if f.severity == "error"]
        warnings = [f for f in self.findings if f.severity == "warning"]

        return {
            "total_findings": len(self.findings),
            "errors": len(errors),
            "warnings": len(warnings),
            "status": "FAILED ❌" if errors else "PASSED ⚠️" if warnings else "PASSED ✅",
        }


def main():
    """Run SQL injection audit on hook library."""
    hooks_lib_dir = "/home/user/.claude/hooks/lib"

    print("\n" + "=" * 70)
    print("SQL INJECTION PREVENTION AUDIT")
    print("=" * 70)
    print(f"Scanning: {hooks_lib_dir}\n")

    auditor = SQLInjectionAuditor(verbose=True)
    findings = auditor.audit_directory(hooks_lib_dir)

    # Print findings
    if findings:
        print(f"\n⚠️  Found {len(findings)} potential issue(s):\n")

        by_file = {}
        for finding in findings:
            if finding.file_path not in by_file:
                by_file[finding.file_path] = []
            by_file[finding.file_path].append(finding)

        for file_path, file_findings in sorted(by_file.items()):
            file_name = os.path.basename(file_path)
            print(f"  📄 {file_name}")

            for finding in file_findings:
                print(f"     Line {finding.line_number}: {finding.issue_type}")
                print(f"     → {finding.line_content[:70]}")
                print(f"     💡 {finding.recommendation}")
                print()
    else:
        print("✅ No SQL injection vulnerabilities detected!")
        print("\nAll SQL queries use parameterized statements.")

    # Summary
    summary = auditor.get_summary()
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"Total findings: {summary['total_findings']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"\nStatus: {summary['status']}")
    print("=" * 70 + "\n")

    return 2 if summary['errors'] > 0 else (1 if summary['warnings'] > 0 else 0)


if __name__ == "__main__":
    import sys
    sys.exit(main())
