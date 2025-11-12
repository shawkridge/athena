"""Tests for PII detector.

Tests:
- Email detection
- Path detection
- Credential detection
- SSN, credit card, phone detection
- Custom patterns
- Event scanning
"""

import pytest
from athena.pii.detector import PIIDetector, PIIDetection


class TestPIIDetector:
    """Test PII detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return PIIDetector()

    def test_detect_emails(self, detector):
        """Test email detection."""
        text = "Contact alice@example.com or bob.smith@company.co.uk"
        detections = detector.detect(text, field_name='content')

        assert len(detections) == 2
        assert detections[0].type == 'email'
        assert detections[0].value == 'alice@example.com'
        assert detections[1].value == 'bob.smith@company.co.uk'

    def test_detect_absolute_paths(self, detector):
        """Test absolute path detection."""
        text = "Error in /home/alice/projects/app/main.py and /Users/bob/code/test.py"
        detections = detector.detect(text, field_name='stack_trace')

        assert len(detections) == 2
        assert all(d.type == 'absolute_path' for d in detections)
        assert '/home/alice' in detections[0].value
        assert '/Users/bob' in detections[1].value

    def test_detect_api_keys(self, detector):
        """Test API key detection."""
        text = "Generated key sk-1234567890abcdefghij"
        detections = detector.detect(text, field_name='content')

        assert len(detections) >= 1
        assert any(d.type == 'api_key' for d in detections)

    def test_detect_aws_keys(self, detector):
        """Test AWS key detection."""
        text = "AWS key: AKIA1234567890ABCDEF"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'aws_key' for d in detections)

    def test_detect_private_keys(self, detector):
        """Test private key detection."""
        text = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA1234567890...
        -----END RSA PRIVATE KEY-----
        """
        detections = detector.detect(text, field_name='diff')

        assert any(d.type == 'private_key' for d in detections)

    def test_detect_ssn(self, detector):
        """Test Social Security Number detection."""
        text = "SSN: 123-45-6789"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'ssn' for d in detections)

    def test_detect_credit_card(self, detector):
        """Test credit card detection."""
        text = "Card: 4532-1234-5678-9010"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'credit_card' for d in detections)

    def test_detect_phone_numbers(self, detector):
        """Test phone number detection."""
        text = "Call (555) 123-4567 or +1-555-123-4567"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'phone' for d in detections)

    def test_no_pii_in_clean_text(self, detector):
        """Test that clean text returns no detections."""
        text = "This is a clean message with no sensitive data"
        detections = detector.detect(text, field_name='content')

        assert len(detections) == 0

    def test_empty_text(self, detector):
        """Test empty text handling."""
        detections = detector.detect("", field_name='content')
        assert len(detections) == 0

    def test_none_input(self, detector):
        """Test None input handling."""
        detections = detector.detect(None, field_name='content')
        assert len(detections) == 0

    def test_confidence_threshold(self, detector):
        """Test confidence threshold filtering."""
        text = "Email: alice@example.com"

        # Low threshold (should include all)
        detections_loose = detector.detect(text, field_name='content', confidence_threshold=0.5)

        # Emails have high confidence (0.95), so loose threshold should detect them
        assert len(detections_loose) >= 1

        # High threshold above email confidence (0.95) should filter them out
        detections_strict = detector.detect(text, field_name='content', confidence_threshold=0.99)
        assert len(detections_strict) == 0

    def test_custom_patterns(self):
        """Test custom pattern detection."""
        custom_patterns = {
            'slack_token': r'xox[baprs]-[0-9a-zA-Z]{10,48}'
        }
        detector = PIIDetector(custom_patterns=custom_patterns)

        text = "Token: xoxb-123456789012-1234567890ab"
        detections = detector.detect(text, field_name='content')

        # Should detect custom pattern
        assert any(d.type == 'slack_token' for d in detections)

    def test_github_token_detection(self, detector):
        """Test GitHub token detection."""
        text = "ghp_1234567890abcdefghij1234567890abcdef"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'github_token' for d in detections)

    def test_jwt_detection(self, detector):
        """Test JWT detection."""
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        detections = detector.detect(text, field_name='content')

        assert any(d.type == 'jwt' for d in detections)

    def test_detection_has_required_fields(self, detector):
        """Test that detections have all required fields."""
        text = "Email: alice@example.com"
        detections = detector.detect(text, field_name='test_field')

        assert len(detections) > 0
        detection = detections[0]
        assert detection.type is not None
        assert detection.value is not None
        assert detection.start_pos is not None
        assert detection.end_pos is not None
        assert detection.confidence is not None
        assert detection.field_name == 'test_field'

    def test_has_pii_simple(self, detector):
        """Test has_pii check."""
        # Note: This would require an EpisodicEvent fixture
        # For now, test detection directly
        text_with_pii = "Email: alice@example.com"
        text_clean = "No PII here"

        assert detector.detect(text_with_pii) != []
        assert detector.detect(text_clean) == []

    def test_summary_generation(self, detector):
        """Test summary generation."""
        text = "Email: alice@example.com, Path: /home/alice/file.txt"
        detections = detector.detect(text, field_name='content')
        detections_by_field = {'content': detections}

        summary = detector.summary(detections_by_field)

        assert 'PII' in summary
        assert 'content' in summary

    def test_multiple_detections_same_type(self, detector):
        """Test multiple detections of same type."""
        text = "Emails: alice@example.com, bob@example.com, charlie@example.com"
        detections = detector.detect(text, field_name='content')

        email_detections = [d for d in detections if d.type == 'email']
        assert len(email_detections) == 3

    def test_detection_position_accuracy(self, detector):
        """Test that detection positions are accurate."""
        text = "The email is alice@example.com in the middle"
        detections = detector.detect(text, field_name='content')

        email_detections = [d for d in detections if d.type == 'email']
        assert len(email_detections) > 0

        for d in email_detections:
            # Verify position
            extracted = text[d.start_pos:d.end_pos]
            assert extracted == d.value
