"""Security Analysis for code symbols.

Provides:
- Security vulnerability detection
- Secure coding practice enforcement
- Security anti-pattern identification
- Cryptography and authentication checks
- Input validation analysis
- OWASP top 10 compliance checks
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class VulnerabilityType(str, Enum):
    """Types of security vulnerabilities."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    BROKEN_AUTHENTICATION = "broken_authentication"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    XXE = "xxe"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    USING_COMPONENTS_WITH_KNOWN_VULNERABILITIES = "known_vulnerabilities"
    INSUFFICIENT_LOGGING = "insufficient_logging"
    CRYPTOGRAPHIC_FAILURE = "cryptographic_failure"


class SecurityRiskLevel(str, Enum):
    """Security risk severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecureCodePractice(str, Enum):
    """Secure coding practices."""

    INPUT_VALIDATION = "input_validation"
    OUTPUT_ENCODING = "output_encoding"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    DEPENDENCY_MANAGEMENT = "dependency_management"


@dataclass
class SecurityVulnerability:
    """Identified security vulnerability."""

    symbol_name: str
    vulnerability_type: VulnerabilityType
    risk_level: SecurityRiskLevel
    risk_score: float  # 0-1
    description: str
    affected_code_pattern: str
    remediation: List[str]
    references: List[str]  # OWASP, CVE links, etc.
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID


@dataclass
class SecureCodeIssue:
    """Issue with secure coding practices."""

    symbol_name: str
    practice: SecureCodePractice
    severity: str  # low, medium, high, critical
    severity_score: float  # 0-1
    message: str
    recommendation: List[str]


@dataclass
class SecurityMetric:
    """Security metric for a symbol."""

    metric_name: str
    value: float  # 0-1
    threshold: float  # 0-1
    status: str  # compliant, warning, non-compliant


@dataclass
class SecurityProfile:
    """Complete security profile for a symbol."""

    symbol_name: str
    overall_security_score: float  # 0-100
    security_level: str  # critical, high, medium, low, secure
    vulnerabilities: List[SecurityVulnerability]
    practice_issues: List[SecureCodeIssue]
    metrics: Dict[str, SecurityMetric]
    owasp_a1_score: float  # Broken Access Control
    owasp_a2_score: float  # Cryptographic Failures
    owasp_a3_score: float  # Injection
    recommendations: List[str]


class SecurityAnalyzer:
    """Analyzes code for security vulnerabilities and practices."""

    def __init__(self):
        """Initialize security analyzer."""
        self.profiles: Dict[str, SecurityProfile] = {}
        self.detected_vulnerabilities: Dict[str, List[SecurityVulnerability]] = {}
        self.compliance_status: Dict[str, Dict[str, bool]] = {}

    def analyze_security(self, symbol_data: Dict) -> SecurityProfile:
        """Analyze security of a symbol.

        Args:
            symbol_data: Symbol data with code and metrics

        Returns:
            SecurityProfile with vulnerabilities and recommendations
        """
        symbol_name = symbol_data.get("name", "unknown")

        # Detect vulnerabilities
        vulnerabilities = self._detect_vulnerabilities(symbol_name, symbol_data)

        # Check secure coding practices
        practice_issues = self._check_secure_practices(symbol_name, symbol_data)

        # Calculate security metrics
        metrics = self._calculate_security_metrics(symbol_data)

        # Calculate OWASP scores
        owasp_a1 = self._calculate_owasp_a1(vulnerabilities, symbol_data)
        owasp_a2 = self._calculate_owasp_a2(vulnerabilities, symbol_data)
        owasp_a3 = self._calculate_owasp_a3(vulnerabilities, symbol_data)

        # Calculate overall security score
        overall_score = self._calculate_security_score(vulnerabilities, practice_issues, metrics)

        # Determine security level
        security_level = self._determine_security_level(overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(vulnerabilities, practice_issues)

        profile = SecurityProfile(
            symbol_name=symbol_name,
            overall_security_score=overall_score,
            security_level=security_level,
            vulnerabilities=vulnerabilities,
            practice_issues=practice_issues,
            metrics=metrics,
            owasp_a1_score=owasp_a1,
            owasp_a2_score=owasp_a2,
            owasp_a3_score=owasp_a3,
            recommendations=recommendations,
        )

        self.profiles[symbol_name] = profile
        if vulnerabilities:
            self.detected_vulnerabilities[symbol_name] = vulnerabilities

        return profile

    def _detect_vulnerabilities(
        self, symbol_name: str, symbol_data: Dict
    ) -> List[SecurityVulnerability]:
        """Detect security vulnerabilities."""
        vulnerabilities = []
        code = symbol_data.get("code", "").lower()

        # SQL Injection detection
        if self._check_sql_injection(code):
            vulnerabilities.append(
                SecurityVulnerability(
                    symbol_name=symbol_name,
                    vulnerability_type=VulnerabilityType.SQL_INJECTION,
                    risk_level=SecurityRiskLevel.CRITICAL,
                    risk_score=0.95,
                    description="Potential SQL injection vulnerability detected",
                    affected_code_pattern="String concatenation in SQL queries",
                    remediation=[
                        "Use parameterized queries",
                        "Use ORM frameworks",
                        "Validate and sanitize input",
                        "Apply principle of least privilege to DB accounts",
                    ],
                    references=["OWASP A03:2021 - Injection", "CWE-89"],
                    cwe_id="CWE-89",
                )
            )

        # XSS detection
        if self._check_xss_vulnerability(code):
            vulnerabilities.append(
                SecurityVulnerability(
                    symbol_name=symbol_name,
                    vulnerability_type=VulnerabilityType.XSS,
                    risk_level=SecurityRiskLevel.HIGH,
                    risk_score=0.85,
                    description="Potential XSS vulnerability detected",
                    affected_code_pattern="Unsafe HTML rendering or DOM manipulation",
                    remediation=[
                        "Use templating engines with auto-escaping",
                        "Sanitize user input",
                        "Use Content Security Policy (CSP)",
                        "Validate output encoding",
                    ],
                    references=["OWASP A03:2021 - Injection", "CWE-79"],
                    cwe_id="CWE-79",
                )
            )

        # Insecure deserialization
        if self._check_insecure_deserialization(code):
            vulnerabilities.append(
                SecurityVulnerability(
                    symbol_name=symbol_name,
                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                    risk_level=SecurityRiskLevel.CRITICAL,
                    risk_score=0.9,
                    description="Insecure deserialization detected",
                    affected_code_pattern="Deserialization of untrusted data",
                    remediation=[
                        "Use safe deserialization methods",
                        "Implement strict input validation",
                        "Use allowlists for deserialization",
                        "Keep libraries updated",
                    ],
                    references=["OWASP A08:2021 - Deserialization", "CWE-502"],
                    cwe_id="CWE-502",
                )
            )

        # Cryptographic failure
        if self._check_weak_crypto(code):
            vulnerabilities.append(
                SecurityVulnerability(
                    symbol_name=symbol_name,
                    vulnerability_type=VulnerabilityType.CRYPTOGRAPHIC_FAILURE,
                    risk_level=SecurityRiskLevel.HIGH,
                    risk_score=0.8,
                    description="Weak cryptographic implementation detected",
                    affected_code_pattern="Use of deprecated or weak encryption",
                    remediation=[
                        "Use modern encryption algorithms (AES-256)",
                        "Use secure hashing (SHA-256+)",
                        "Implement proper key management",
                        "Use established cryptographic libraries",
                    ],
                    references=["OWASP A02:2021 - Cryptographic Failures", "CWE-327"],
                    cwe_id="CWE-327",
                )
            )

        # Insufficient logging
        if self._check_insufficient_logging(code, symbol_data):
            vulnerabilities.append(
                SecurityVulnerability(
                    symbol_name=symbol_name,
                    vulnerability_type=VulnerabilityType.INSUFFICIENT_LOGGING,
                    risk_level=SecurityRiskLevel.MEDIUM,
                    risk_score=0.6,
                    description="Insufficient logging and monitoring",
                    affected_code_pattern="Missing security event logging",
                    remediation=[
                        "Log all security-relevant events",
                        "Include timestamps and user information",
                        "Protect log files from tampering",
                        "Monitor logs for suspicious activity",
                    ],
                    references=["OWASP A09:2021 - Logging Failures", "CWE-778"],
                    cwe_id="CWE-778",
                )
            )

        return vulnerabilities

    def _check_sql_injection(self, code: str) -> bool:
        """Check for SQL injection vulnerability patterns."""
        injection_patterns = [
            "select" in code and ("+" in code or 'f"' in code),
            "insert" in code and ("+" in code or 'f"' in code),
            "update" in code and ("+" in code or 'f"' in code),
            "delete" in code and ("+" in code or 'f"' in code),
            "query(" in code and ("+" in code or "format(" in code),
        ]
        return any(injection_patterns)

    def _check_xss_vulnerability(self, code: str) -> bool:
        """Check for XSS vulnerability patterns."""
        xss_patterns = [
            "innerhtml" in code,
            "eval(" in code,
            "execute(" in code,
            "html(" in code and "escape" not in code,
            "render" in code and "unsafe" in code,
        ]
        return any(xss_patterns)

    def _check_insecure_deserialization(self, code: str) -> bool:
        """Check for insecure deserialization patterns."""
        deser_patterns = [
            "pickle.loads" in code,
            "eval(" in code,
            "exec(" in code,
            "deserialize" in code and "validate" not in code,
        ]
        return any(deser_patterns)

    def _check_weak_crypto(self, code: str) -> bool:
        """Check for weak cryptographic patterns."""
        weak_patterns = [
            "md5" in code,
            "sha1" in code,
            "des" in code,
            "rc4" in code,
            "random()" in code and "password" in code,
        ]
        return any(weak_patterns)

    def _check_insufficient_logging(self, code: str, symbol_data: Dict) -> bool:
        """Check for insufficient logging."""
        security_keywords = ["auth", "login", "password", "token", "permission"]
        has_security_keyword = any(kw in code for kw in security_keywords)

        if has_security_keyword:
            log_keywords = ["log", "logger", "audit", "track"]
            has_logging = any(kw in code for kw in log_keywords)
            return not has_logging

        return False

    def _check_secure_practices(self, symbol_name: str, symbol_data: Dict) -> List[SecureCodeIssue]:
        """Check secure coding practices."""
        issues = []
        code = symbol_data.get("code", "").lower()

        # Input validation check
        if "input" in code and "validate" not in code:
            issues.append(
                SecureCodeIssue(
                    symbol_name=symbol_name,
                    practice=SecureCodePractice.INPUT_VALIDATION,
                    severity="high",
                    severity_score=0.8,
                    message="Input validation not detected",
                    recommendation=[
                        "Validate all user inputs",
                        "Use allowlists for validation",
                        "Reject invalid input",
                    ],
                )
            )

        # Error handling check
        if "try" not in code and ("parse" in code or "request" in code):
            issues.append(
                SecureCodeIssue(
                    symbol_name=symbol_name,
                    practice=SecureCodePractice.ERROR_HANDLING,
                    severity="medium",
                    severity_score=0.6,
                    message="Weak error handling detected",
                    recommendation=[
                        "Implement try-catch blocks",
                        "Avoid exposing error details",
                        "Log errors securely",
                    ],
                )
            )

        return issues

    def _calculate_security_metrics(self, symbol_data: Dict) -> Dict[str, SecurityMetric]:
        """Calculate security metrics."""
        metrics = {}
        code = symbol_data.get("code", "").lower()

        # Input validation metric
        input_validation_score = 1.0 if "validate" in code else 0.0
        metrics["input_validation"] = SecurityMetric(
            metric_name="Input Validation",
            value=input_validation_score,
            threshold=0.8,
            status="compliant" if input_validation_score >= 0.8 else "non-compliant",
        )

        # Authentication check
        auth_check = 1.0 if "auth" in code else 0.5
        metrics["authentication"] = SecurityMetric(
            metric_name="Authentication",
            value=auth_check,
            threshold=0.7,
            status="compliant" if auth_check >= 0.7 else "warning",
        )

        # Logging check
        logging_check = 1.0 if "log" in code else 0.3
        metrics["logging"] = SecurityMetric(
            metric_name="Logging & Monitoring",
            value=logging_check,
            threshold=0.7,
            status="compliant" if logging_check >= 0.7 else "non-compliant",
        )

        return metrics

    def _calculate_owasp_a1(
        self, vulnerabilities: List[SecurityVulnerability], symbol_data: Dict
    ) -> float:
        """Calculate OWASP A01 score."""
        score = 100.0

        access_control_vulns = [
            v
            for v in vulnerabilities
            if v.vulnerability_type == VulnerabilityType.BROKEN_ACCESS_CONTROL
        ]

        for vuln in access_control_vulns:
            score -= vuln.risk_score * 50

        code = symbol_data.get("code", "").lower()
        if "auth" not in code or "permission" not in code:
            score -= 10

        return max(0.0, score)

    def _calculate_owasp_a2(
        self, vulnerabilities: List[SecurityVulnerability], symbol_data: Dict
    ) -> float:
        """Calculate OWASP A02 score."""
        score = 100.0

        crypto_vulns = [
            v
            for v in vulnerabilities
            if v.vulnerability_type == VulnerabilityType.CRYPTOGRAPHIC_FAILURE
        ]

        for vuln in crypto_vulns:
            score -= vuln.risk_score * 50

        code = symbol_data.get("code", "").lower()
        weak_crypto_keywords = ["md5", "sha1", "des", "rc4"]
        if any(kw in code for kw in weak_crypto_keywords):
            score -= 30

        return max(0.0, score)

    def _calculate_owasp_a3(
        self, vulnerabilities: List[SecurityVulnerability], symbol_data: Dict
    ) -> float:
        """Calculate OWASP A03 score."""
        score = 100.0

        injection_vulns = [
            v
            for v in vulnerabilities
            if v.vulnerability_type in [VulnerabilityType.SQL_INJECTION, VulnerabilityType.XSS]
        ]

        for vuln in injection_vulns:
            score -= vuln.risk_score * 50

        return max(0.0, score)

    def _calculate_security_score(
        self,
        vulnerabilities: List[SecurityVulnerability],
        practice_issues: List[SecureCodeIssue],
        metrics: Dict[str, SecurityMetric],
    ) -> float:
        """Calculate overall security score."""
        base_score = 100.0

        severity_weights = {
            SecurityRiskLevel.CRITICAL: 25,
            SecurityRiskLevel.HIGH: 15,
            SecurityRiskLevel.MEDIUM: 8,
            SecurityRiskLevel.LOW: 3,
            SecurityRiskLevel.INFO: 1,
        }

        for vuln in vulnerabilities:
            weight = severity_weights.get(vuln.risk_level, 5)
            base_score -= weight

        for issue in practice_issues:
            severity_weight = {
                "critical": 10,
                "high": 8,
                "medium": 5,
                "low": 2,
            }
            base_score -= severity_weight.get(issue.severity, 3)

        for metric in metrics.values():
            if metric.status == "compliant":
                base_score += 2

        return max(0.0, min(100.0, base_score))

    def _determine_security_level(self, score: float) -> str:
        """Determine security level from score."""
        if score >= 90:
            return "secure"
        elif score >= 75:
            return "low"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "high"
        else:
            return "critical"

    def _generate_recommendations(
        self,
        vulnerabilities: List[SecurityVulnerability],
        practice_issues: List[SecureCodeIssue],
    ) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        critical = [v for v in vulnerabilities if v.risk_level == SecurityRiskLevel.CRITICAL]
        if critical:
            recommendations.append(f"CRITICAL: Fix {len(critical)} critical vulnerability(ies)")
            for vuln in critical[:2]:
                recommendations.extend(vuln.remediation[:2])

        high = [v for v in vulnerabilities if v.risk_level == SecurityRiskLevel.HIGH]
        if high:
            recommendations.append(f"HIGH PRIORITY: Address {len(high)} high-risk issue(s)")

        for issue in practice_issues[:3]:
            recommendations.append(f"Improve {issue.practice.value}: {issue.message}")

        if not recommendations:
            recommendations.append("Code passes security analysis.")

        return recommendations

    def check_owasp_compliance(self, symbol_name: str) -> Dict[str, bool]:
        """Check OWASP Top 10 compliance for a symbol."""
        profile = self.profiles.get(symbol_name)

        if not profile:
            return {"error": f"No profile for {symbol_name}"}

        compliance = {
            "A01_Broken_Access_Control": profile.owasp_a1_score >= 80,
            "A02_Cryptographic_Failures": profile.owasp_a2_score >= 80,
            "A03_Injection": profile.owasp_a3_score >= 80,
            "Input_Validation": profile.metrics.get("input_validation", None)
            and profile.metrics["input_validation"].status == "compliant",
            "Error_Handling": len(
                [
                    i
                    for i in profile.practice_issues
                    if i.practice == SecureCodePractice.ERROR_HANDLING
                ]
            )
            == 0,
            "Logging": profile.metrics.get("logging", None)
            and profile.metrics["logging"].status == "compliant",
        }

        self.compliance_status[symbol_name] = compliance
        return compliance

    def get_security_summary(self) -> Dict:
        """Get summary of all security profiles."""
        if not self.profiles:
            return {
                "total_symbols": 0,
                "average_score": 0.0,
                "critical_count": 0,
                "vulnerable_count": 0,
            }

        scores = [p.overall_security_score for p in self.profiles.values()]
        critical_count = len([p for p in self.profiles.values() if p.security_level == "critical"])
        vulnerable_count = len(self.detected_vulnerabilities)

        return {
            "total_symbols": len(self.profiles),
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 100.0,
            "security_levels": {
                level: len([p for p in self.profiles.values() if p.security_level == level])
                for level in ["secure", "low", "medium", "high", "critical"]
            },
            "critical_count": critical_count,
            "vulnerable_count": vulnerable_count,
            "total_vulnerabilities": sum(len(v) for v in self.detected_vulnerabilities.values()),
        }
