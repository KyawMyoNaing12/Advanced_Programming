import json
import uuid
import urllib.error
import urllib.request

import pytest

from Sale_Data_Validation import FilePanel


@pytest.fixture
def app():
    """
    Create a FilePanel object without running the GUI __init__().
    """

    application = FilePanel.__new__(FilePanel)

    class MockApp:
        """
        Mock application object used by FilePanel.
        """

        def log_message(self, level, message):
            """
            Mock the log_message() method used by FilePanel.
            """
            pass

    application.app = MockApp()

    return application


def test_get_api_uuid_success(app, monkeypatch):
    """
    Test _get_api_uuid() when the external API succeeds.
    """

    expected_uuid = "123e4567-e89b-12d3-a456-426614174000"

    class MockResponse:
        """
        Mock HTTP response from the UUID API.
        """

        def read(self):
            # The real method expects a JSON list.
            return json.dumps([expected_uuid]).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

    def mock_urlopen(request, timeout=5):
        """
        Mock urllib.request.urlopen().
        """
        return MockResponse()

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        mock_urlopen
    )

    result = app._get_api_uuid()

    assert result == expected_uuid


def test_get_api_uuid_api_failure(app, monkeypatch):
    """
    Test _get_api_uuid() when the external API fails.

    The method should fall back to local UUID generation.
    """

    def mock_urlopen(request, timeout=5):
        """
        Simulate an API connection failure.
        """
        raise urllib.error.URLError("API connection failed")

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        mock_urlopen
    )

    result = app._get_api_uuid()

    assert isinstance(result, str)


def test_get_api_uuid_returns_string(app):
    """
    Test that _get_api_uuid() returns a string.
    """

    result = app._get_api_uuid()

    assert isinstance(result, str)
    assert len(result) > 0


def test_get_api_uuid_fallback_is_valid_uuid(app, monkeypatch):
    """
    Test that the fallback result is a valid UUID.
    """

    def mock_urlopen(request, timeout=5):
        """
        Simulate API failure.
        """
        raise urllib.error.URLError("API unavailable")

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        mock_urlopen
    )

    result = app._get_api_uuid()

    # Check that the returned value is a valid UUID.
    parsed_uuid = uuid.UUID(result)

    assert isinstance(parsed_uuid, uuid.UUID)

