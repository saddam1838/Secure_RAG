from services.security_service import SecurityService


def test_filter_output():
    sec = SecurityService()
    text = "This is a terrorist attack plan."
    filtered = sec.filter_output(text)
    assert "terrorist" not in filtered or "[REDACTED]" in filtered
