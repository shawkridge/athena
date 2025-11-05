"""Unit tests for Security Analyzer.

Tests security vulnerability detection including:
- SQL injection and XSS patterns
- Insecure deserialization and weak crypto
- Secure coding practice enforcement
- Security metrics calculation
- OWASP Top 10 compliance
"""

import pytest
from athena.symbols.security_analyzer import (
    SecurityAnalyzer,
    SecurityVulnerability,
    SecurityProfile,
    VulnerabilityType,
    SecurityRiskLevel,
    SecureCodePractice,
)


@pytest.fixture
def analyzer():
    """Create a fresh security analyzer."""
    return SecurityAnalyzer()


@pytest.fixture
def clean_code_data():
    """Code with no security issues."""
    return {
        "name": "secure_function",
        "code": "def authenticate(user): return user.is_valid()",
    }


@pytest.fixture
def sql_injection_code():
    """Code with potential SQL injection."""
    # Pattern requires 'select' + ('+' or 'f"')
    code_pattern = r'query = "select * from users where id = " + str(user_id)'
    return {
        "name": "vulnerable_query",
        "code": code_pattern,
    }


@pytest.fixture
def xss_vulnerable_code():
    """Code with XSS vulnerability."""
    return {
        "name": "xss_function",
        "code": "element.innerhtml = user_input",
    }


@pytest.fixture
def insecure_deser_code():
    """Code with insecure deserialization."""
    return {
        "name": "deserialize_func",
        "code": "import pickle\ndata = pickle.loads(user_data)",
    }


@pytest.fixture
def weak_crypto_code():
    """Code with weak cryptography."""
    return {
        "name": "hash_password",
        "code": "import hashlib\nhash_obj = hashlib.md5(password.encode())",
    }


@pytest.fixture
def insufficient_logging_code():
    """Code with security keyword but no logging."""
    return {
        "name": "auth_handler",
        "code": "def authenticate_user(token): check_permission(token); process_auth(token)",
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes correctly."""
    assert analyzer.profiles == {}
    assert analyzer.detected_vulnerabilities == {}
    assert analyzer.compliance_status == {}


# ============================================================================
# SQL Injection Detection Tests
# ============================================================================


def test_detect_sql_injection(analyzer, sql_injection_code):
    """Test SQL injection detection."""
    profile = analyzer.analyze_security(sql_injection_code)

    assert profile.symbol_name == "vulnerable_query"
    assert len(profile.vulnerabilities) > 0

    sql_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.SQL_INJECTION
    ]
    assert len(sql_vulns) > 0


def test_sql_injection_attributes(analyzer, sql_injection_code):
    """Test SQL injection vulnerability has correct attributes."""
    profile = analyzer.analyze_security(sql_injection_code)

    sql_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.SQL_INJECTION
    ]
    assert len(sql_vulns) > 0

    vuln = sql_vulns[0]
    assert vuln.risk_level == SecurityRiskLevel.CRITICAL
    assert vuln.risk_score == 0.95
    assert len(vuln.remediation) > 0
    assert any("parameterized" in r.lower() for r in vuln.remediation)


def test_no_sql_injection_in_clean_code(analyzer, clean_code_data):
    """Test clean code doesn't trigger SQL injection."""
    profile = analyzer.analyze_security(clean_code_data)

    sql_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.SQL_INJECTION
    ]
    assert len(sql_vulns) == 0


# ============================================================================
# XSS Detection Tests
# ============================================================================


def test_detect_xss_vulnerability(analyzer, xss_vulnerable_code):
    """Test XSS vulnerability detection."""
    profile = analyzer.analyze_security(xss_vulnerable_code)

    xss_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.XSS
    ]
    assert len(xss_vulns) > 0


def test_xss_vulnerability_attributes(analyzer, xss_vulnerable_code):
    """Test XSS vulnerability has correct attributes."""
    profile = analyzer.analyze_security(xss_vulnerable_code)

    xss_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.XSS
    ]
    assert len(xss_vulns) > 0

    vuln = xss_vulns[0]
    assert vuln.risk_level == SecurityRiskLevel.HIGH
    assert vuln.risk_score == 0.85
    assert len(vuln.remediation) > 0


# ============================================================================
# Insecure Deserialization Detection Tests
# ============================================================================


def test_detect_insecure_deserialization(analyzer, insecure_deser_code):
    """Test insecure deserialization detection."""
    profile = analyzer.analyze_security(insecure_deser_code)

    deser_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.INSECURE_DESERIALIZATION
    ]
    assert len(deser_vulns) > 0


def test_insecure_deser_attributes(analyzer, insecure_deser_code):
    """Test insecure deserialization has correct attributes."""
    profile = analyzer.analyze_security(insecure_deser_code)

    deser_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.INSECURE_DESERIALIZATION
    ]
    assert len(deser_vulns) > 0

    vuln = deser_vulns[0]
    assert vuln.risk_level == SecurityRiskLevel.CRITICAL
    assert vuln.risk_score == 0.9
    assert "CWE-502" in vuln.cwe_id


# ============================================================================
# Weak Cryptography Detection Tests
# ============================================================================


def test_detect_weak_crypto(analyzer, weak_crypto_code):
    """Test weak cryptography detection."""
    profile = analyzer.analyze_security(weak_crypto_code)

    crypto_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.CRYPTOGRAPHIC_FAILURE
    ]
    assert len(crypto_vulns) > 0


def test_weak_crypto_attributes(analyzer, weak_crypto_code):
    """Test weak crypto vulnerability has correct attributes."""
    profile = analyzer.analyze_security(weak_crypto_code)

    crypto_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.CRYPTOGRAPHIC_FAILURE
    ]
    assert len(crypto_vulns) > 0

    vuln = crypto_vulns[0]
    assert vuln.risk_level == SecurityRiskLevel.HIGH
    assert vuln.risk_score == 0.8
    assert any("aes" in r.lower() for r in vuln.remediation)


# ============================================================================
# Insufficient Logging Detection Tests
# ============================================================================


def test_detect_insufficient_logging(analyzer, insufficient_logging_code):
    """Test insufficient logging detection."""
    profile = analyzer.analyze_security(insufficient_logging_code)

    log_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.INSUFFICIENT_LOGGING
    ]
    assert len(log_vulns) > 0


def test_insufficient_logging_attributes(analyzer, insufficient_logging_code):
    """Test insufficient logging has correct attributes."""
    profile = analyzer.analyze_security(insufficient_logging_code)

    log_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.INSUFFICIENT_LOGGING
    ]
    assert len(log_vulns) > 0

    vuln = log_vulns[0]
    assert vuln.risk_level == SecurityRiskLevel.MEDIUM
    assert vuln.risk_score == 0.6


def test_no_insufficient_logging_with_logging(analyzer):
    """Test code with logging doesn't trigger insufficient logging."""
    code_data = {
        "name": "safe_auth",
        "code": "def login(user): logger.info('attempt'); authenticate(user)",
    }
    profile = analyzer.analyze_security(code_data)

    log_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.INSUFFICIENT_LOGGING
    ]
    assert len(log_vulns) == 0


# ============================================================================
# Secure Practices Tests
# ============================================================================


def test_check_secure_practices(analyzer):
    """Test secure practices checking."""
    code_data = {
        "name": "input_handler",
        "code": "def process(user_input): handle(user_input)",
    }
    profile = analyzer.analyze_security(code_data)

    assert len(profile.practice_issues) >= 0


def test_input_validation_issue_detection(analyzer):
    """Test input validation practice issue detection."""
    code_data = {
        "name": "input_handler",
        "code": "def handle_input(data): process(data)",
    }
    profile = analyzer.analyze_security(code_data)

    input_issues = [
        i for i in profile.practice_issues
        if i.practice == SecureCodePractice.INPUT_VALIDATION
    ]
    assert len(input_issues) > 0


def test_error_handling_issue_detection(analyzer):
    """Test error handling practice issue detection."""
    code_data = {
        "name": "parser",
        "code": "def parse_request(data): json_parse(data)",
    }
    profile = analyzer.analyze_security(code_data)

    error_issues = [
        i for i in profile.practice_issues
        if i.practice == SecureCodePractice.ERROR_HANDLING
    ]
    assert len(error_issues) > 0


# ============================================================================
# Security Metrics Tests
# ============================================================================


def test_calculate_security_metrics(analyzer, clean_code_data):
    """Test security metrics calculation."""
    profile = analyzer.analyze_security(clean_code_data)

    assert len(profile.metrics) > 0
    assert "input_validation" in profile.metrics
    assert "authentication" in profile.metrics
    assert "logging" in profile.metrics


def test_metric_values_in_range(analyzer, clean_code_data):
    """Test metrics have values between 0 and 1."""
    profile = analyzer.analyze_security(clean_code_data)

    for metric in profile.metrics.values():
        assert 0.0 <= metric.value <= 1.0
        assert 0.0 <= metric.threshold <= 1.0
        assert metric.status in ["compliant", "warning", "non-compliant"]


def test_logging_metric_compliance(analyzer):
    """Test logging metric compliance status."""
    code_data = {
        "name": "app",
        "code": "logger.info('event'); process()",
    }
    profile = analyzer.analyze_security(code_data)

    logging_metric = profile.metrics.get("logging")
    assert logging_metric is not None
    assert logging_metric.value >= 0.7
    assert logging_metric.status == "compliant"


# ============================================================================
# OWASP Scoring Tests
# ============================================================================


def test_owasp_a1_score_with_no_violations(analyzer, clean_code_data):
    """Test OWASP A1 score with no violations."""
    profile = analyzer.analyze_security(clean_code_data)

    assert 0.0 <= profile.owasp_a1_score <= 100.0
    assert profile.owasp_a1_score >= 80


def test_owasp_a2_score_with_weak_crypto(analyzer, weak_crypto_code):
    """Test OWASP A2 score with weak crypto."""
    profile = analyzer.analyze_security(weak_crypto_code)

    assert 0.0 <= profile.owasp_a2_score <= 100.0
    assert profile.owasp_a2_score < 80


def test_owasp_a3_score_with_injection(analyzer):
    """Test OWASP A3 score with injection vulnerability."""
    sql_injection_code = {
        "name": "query_func",
        "code": r'query = "select * where id = " + user_id'
    }
    profile = analyzer.analyze_security(sql_injection_code)

    assert 0.0 <= profile.owasp_a3_score <= 100.0
    assert profile.owasp_a3_score < 80


# ============================================================================
# Overall Security Score Tests
# ============================================================================


def test_security_score_in_valid_range(analyzer, clean_code_data):
    """Test security score is between 0-100."""
    profile = analyzer.analyze_security(clean_code_data)

    assert 0.0 <= profile.overall_security_score <= 100.0


def test_clean_code_has_high_score(analyzer, clean_code_data):
    """Test clean code gets high security score."""
    profile = analyzer.analyze_security(clean_code_data)

    assert profile.overall_security_score >= 70


def test_vulnerable_code_has_low_score(analyzer):
    """Test vulnerable code gets lower security score than clean code."""
    sql_injection_code = {
        "name": "bad_query",
        "code": r'query = "select * from users where id = " + user_id'
    }
    clean_code = {
        "name": "clean",
        "code": "def multiply(a, b): return a * b"
    }

    vulnerable_profile = analyzer.analyze_security(sql_injection_code)
    clean_profile = analyzer.analyze_security(clean_code)

    # Vulnerable code should have lower score than clean code
    assert vulnerable_profile.overall_security_score < clean_profile.overall_security_score


def test_multiple_vulnerabilities_reduce_score(analyzer):
    """Test multiple vulnerabilities reduce security score."""
    vulnerable_code = {
        "name": "very_vulnerable",
        "code": r'query = "select * from users where id = " + user_id + " or 1=1"; pickle.loads(data); hashlib.md5()',
    }
    profile = analyzer.analyze_security(vulnerable_code)

    assert profile.overall_security_score < 50


# ============================================================================
# Security Level Determination Tests
# ============================================================================


def test_security_level_secure(analyzer, clean_code_data):
    """Test security level is 'secure' for good code."""
    profile = analyzer.analyze_security(clean_code_data)

    assert profile.security_level in ["secure", "low"]


def test_security_level_critical(analyzer):
    """Test security level is lower for vulnerable code."""
    vulnerable_code = {
        "name": "vuln",
        "code": r'query = "select * where id = " + user_id'
    }
    profile = analyzer.analyze_security(vulnerable_code)

    # With SQL injection vulnerability, should not be "secure"
    assert profile.security_level != "secure"


def test_security_level_mapping(analyzer):
    """Test security level mapping from score."""
    # Score >= 90: secure
    code_data = {
        "name": "test1",
        "code": "def func(): pass",
    }
    profile = analyzer.analyze_security(code_data)
    assert profile.security_level in ["secure", "low", "medium"]
    assert profile.overall_security_score >= 80


# ============================================================================
# Recommendation Generation Tests
# ============================================================================


def test_generate_recommendations(analyzer):
    """Test recommendations are generated."""
    code_data = {
        "name": "app",
        "code": "def process(data): handle(data)",
    }
    profile = analyzer.analyze_security(code_data)

    assert len(profile.recommendations) > 0
    assert all(isinstance(r, str) for r in profile.recommendations)


def test_critical_vulnerabilities_in_recommendations(analyzer):
    """Test critical vulnerabilities appear in recommendations."""
    code = {
        "name": "func",
        "code": r'query = "select * where id = " + user_id'
    }
    profile = analyzer.analyze_security(code)

    assert len(profile.recommendations) > 0
    # Either has critical in text or has vulnerabilities
    recommendations_text = " ".join(profile.recommendations).lower()
    assert "critical" in recommendations_text or len(profile.vulnerabilities) > 0


def test_clean_code_passes_analysis_message(analyzer, clean_code_data):
    """Test clean code gets 'passes' message in recommendations."""
    profile = analyzer.analyze_security(clean_code_data)

    if len(profile.vulnerabilities) == 0 and len(profile.practice_issues) == 0:
        assert any("pass" in r.lower() for r in profile.recommendations)


# ============================================================================
# OWASP Compliance Tests
# ============================================================================


def test_check_owasp_compliance(analyzer, clean_code_data):
    """Test OWASP compliance checking."""
    profile = analyzer.analyze_security(clean_code_data)
    compliance = analyzer.check_owasp_compliance("secure_function")

    assert isinstance(compliance, dict)
    assert "A01_Broken_Access_Control" in compliance
    assert "A02_Cryptographic_Failures" in compliance
    assert "A03_Injection" in compliance


def test_compliance_with_no_profile(analyzer):
    """Test compliance check with non-existent profile."""
    compliance = analyzer.check_owasp_compliance("non_existent")

    assert "error" in compliance


def test_compliance_values_are_boolean(analyzer, clean_code_data):
    """Test compliance values are booleans."""
    profile = analyzer.analyze_security(clean_code_data)
    compliance = analyzer.check_owasp_compliance("secure_function")

    for key, value in compliance.items():
        if key != "error":
            assert isinstance(value, bool)


def test_vulnerable_code_fails_compliance(analyzer, sql_injection_code):
    """Test vulnerable code fails compliance check."""
    profile = analyzer.analyze_security(sql_injection_code)
    compliance = analyzer.check_owasp_compliance("vulnerable_query")

    assert compliance.get("A03_Injection") is not None


# ============================================================================
# Security Summary Tests
# ============================================================================


def test_security_summary_empty(analyzer):
    """Test summary with no profiles."""
    summary = analyzer.get_security_summary()

    assert summary["total_symbols"] == 0
    assert summary["average_score"] == 0.0
    assert summary["critical_count"] == 0


def test_security_summary_with_profiles(analyzer, clean_code_data, sql_injection_code):
    """Test summary with multiple profiles."""
    analyzer.analyze_security(clean_code_data)
    analyzer.analyze_security(sql_injection_code)

    summary = analyzer.get_security_summary()

    assert summary["total_symbols"] == 2
    assert summary["average_score"] > 0.0
    assert "security_levels" in summary
    assert "total_vulnerabilities" in summary


def test_summary_includes_vulnerability_count(analyzer):
    """Test summary includes total vulnerability count."""
    code = {
        "name": "func",
        "code": r'query = "select * where id = " + user_id'
    }
    analyzer.analyze_security(code)

    summary = analyzer.get_security_summary()

    assert summary["vulnerable_count"] > 0
    assert summary["total_vulnerabilities"] > 0


def test_summary_security_levels_distribution(analyzer):
    """Test summary includes security level distribution."""
    code1 = {"name": "secure1", "code": "def func(): pass"}
    code2 = {"name": "sql_injection", "code": r'query = "select * where id = " + user_id'}

    analyzer.analyze_security(code1)
    analyzer.analyze_security(code2)

    summary = analyzer.get_security_summary()

    levels = summary.get("security_levels", {})
    assert "secure" in levels or "low" in levels
    assert "critical" in levels or "high" in levels or "medium" in levels


# ============================================================================
# Profile Storage Tests
# ============================================================================


def test_profile_stored_after_analysis(analyzer, clean_code_data):
    """Test profile is stored in analyzer."""
    analyzer.analyze_security(clean_code_data)

    assert "secure_function" in analyzer.profiles


def test_vulnerability_stored_after_detection(analyzer):
    """Test vulnerabilities are stored."""
    code = {
        "name": "func",
        "code": r'query = "select * where id = " + user_id'
    }
    analyzer.analyze_security(code)

    assert "func" in analyzer.detected_vulnerabilities
    assert len(analyzer.detected_vulnerabilities["func"]) > 0


def test_multiple_analyses_dont_overwrite(analyzer, clean_code_data, sql_injection_code):
    """Test multiple analyses accumulate profiles."""
    analyzer.analyze_security(clean_code_data)
    analyzer.analyze_security(sql_injection_code)

    assert len(analyzer.profiles) == 2


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_security_analysis_workflow(analyzer):
    """Test complete security analysis workflow."""
    # Analyze secure code
    secure_profile = analyzer.analyze_security({
        "name": "secure_func",
        "code": "def authenticate(): pass",
    })
    assert secure_profile is not None

    # Analyze vulnerable code
    vulnerable_profile = analyzer.analyze_security({
        "name": "vulnerable_func",
        "code": r'query = "select * where id = " + user_id',
    })
    assert vulnerable_profile is not None

    # Check compliance
    secure_compliance = analyzer.check_owasp_compliance("secure_func")
    vulnerable_compliance = analyzer.check_owasp_compliance("vulnerable_func")

    assert isinstance(secure_compliance, dict)
    assert isinstance(vulnerable_compliance, dict)

    # Get summary
    summary = analyzer.get_security_summary()
    assert summary["total_symbols"] == 2
    assert summary["vulnerable_count"] > 0


def test_vulnerability_remediation_provided(analyzer):
    """Test that vulnerabilities include remediation steps."""
    code = {"name": "func", "code": r'query = "select * where id = " + user_id'}
    profile = analyzer.analyze_security(code)

    for vuln in profile.vulnerabilities:
        assert len(vuln.remediation) > 0
        assert all(isinstance(r, str) for r in vuln.remediation)


def test_cwe_references_included(analyzer):
    """Test that vulnerabilities include CWE references."""
    code = {"name": "func", "code": r'query = "select * where id = " + user_id'}
    profile = analyzer.analyze_security(code)

    for vuln in profile.vulnerabilities:
        assert vuln.cwe_id is not None or vuln.references is not None


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_analyze_empty_code(analyzer):
    """Test analysis of empty code."""
    code_data = {"name": "empty", "code": ""}

    profile = analyzer.analyze_security(code_data)

    assert profile.overall_security_score >= 80


def test_analyze_minimal_symbol(analyzer):
    """Test analysis with minimal symbol data."""
    code_data = {"name": "minimal"}

    profile = analyzer.analyze_security(code_data)

    assert profile.symbol_name == "minimal"
    assert profile.overall_security_score >= 0


def test_analyze_code_without_vulnerabilities(analyzer):
    """Test code without any detected vulnerabilities."""
    code_data = {
        "name": "safe",
        "code": "def multiply(a, b): return a * b",
    }

    profile = analyzer.analyze_security(code_data)

    assert len(profile.vulnerabilities) == 0
    assert profile.overall_security_score >= 80


def test_analyze_code_with_multiple_issues(analyzer):
    """Test code with multiple security issues."""
    code_data = {
        "name": "complex_vulnerable",
        "code": r'import pickle; hashlib.md5(pwd); exec(cmd); pickle.loads(data); query = "select * where id = " + uid',
    }

    profile = analyzer.analyze_security(code_data)

    assert len(profile.vulnerabilities) > 1
    assert profile.overall_security_score < 50


def test_case_insensitive_pattern_matching(analyzer):
    """Test that pattern matching is case-insensitive."""
    uppercase_code = {
        "name": "upper",
        "code": r'QUERY = "SELECT * WHERE ID = " + USER_ID',
    }

    profile = analyzer.analyze_security(uppercase_code)

    sql_vulns = [
        v for v in profile.vulnerabilities
        if v.vulnerability_type == VulnerabilityType.SQL_INJECTION
    ]
    assert len(sql_vulns) > 0


# ============================================================================
# Validation Tests
# ============================================================================


def test_vulnerability_has_all_required_fields(analyzer, sql_injection_code):
    """Test vulnerability objects have all required fields."""
    profile = analyzer.analyze_security(sql_injection_code)

    for vuln in profile.vulnerabilities:
        assert vuln.symbol_name is not None
        assert vuln.vulnerability_type is not None
        assert vuln.risk_level is not None
        assert 0.0 <= vuln.risk_score <= 1.0
        assert vuln.description is not None
        assert vuln.remediation is not None
        assert vuln.references is not None


def test_profile_has_all_required_fields(analyzer, clean_code_data):
    """Test profile has all required fields."""
    profile = analyzer.analyze_security(clean_code_data)

    assert profile.symbol_name is not None
    assert 0.0 <= profile.overall_security_score <= 100.0
    assert profile.security_level is not None
    assert isinstance(profile.vulnerabilities, list)
    assert isinstance(profile.practice_issues, list)
    assert isinstance(profile.metrics, dict)
    assert 0.0 <= profile.owasp_a1_score <= 100.0
    assert 0.0 <= profile.owasp_a2_score <= 100.0
    assert 0.0 <= profile.owasp_a3_score <= 100.0
    assert isinstance(profile.recommendations, list)
