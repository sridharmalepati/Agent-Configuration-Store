from urllib.error import HTTPError
from unittest.mock import patch
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from repo_service.crud import _assert_github_url_reachable


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_assert_github_url_reachable_accepts_successful_response() -> None:
    with patch("repo_service.crud.urlopen", return_value=_FakeResponse()):
        _assert_github_url_reachable("https://github.com/example/acme-service")


def test_assert_github_url_rejects_http_404() -> None:
    http_error = HTTPError(
        url="https://github.com/example/acme-service_01",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    with patch("repo_service.crud.urlopen", side_effect=http_error):
        with pytest.raises(HTTPException) as exc_info:
            _assert_github_url_reachable("https://github.com/example/acme-service_01")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "github_url repo not found (HTTP 404), Please add a valid github url"


def test_assert_github_url_propagates_other_http_status_codes() -> None:
    http_error = HTTPError(
        url="https://github.com/example/acme-service",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch("repo_service.crud.urlopen", side_effect=http_error):
        with pytest.raises(HTTPException) as exc_info:
            _assert_github_url_reachable("https://github.com/example/acme-service")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "github_url is not reachable (HTTP 500)"


def test_assert_github_url_reachable_skips_when_strict_validation_disabled() -> None:
    settings = SimpleNamespace(strict_repo_url_validation=False, github_validation_token="")

    with patch("repo_service.crud.get_settings", return_value=settings):
        with patch("repo_service.crud.urlopen") as mocked_urlopen:
            _assert_github_url_reachable("https://github.com/example/acme-service")

    mocked_urlopen.assert_not_called()


def test_assert_github_url_reachable_adds_auth_header_for_private_repo_validation() -> None:
    settings = SimpleNamespace(strict_repo_url_validation=True, github_validation_token="")

    with patch("repo_service.crud.get_settings", return_value=settings):
        with patch("repo_service.crud.urlopen", return_value=_FakeResponse()) as mocked_urlopen:
            _assert_github_url_reachable("https://github.com/example/acme-service", github_token="ghp_testtoken")

    request = mocked_urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer ghp_testtoken"


def test_assert_github_url_reachable_uses_fallback_token_from_settings() -> None:
    settings = SimpleNamespace(strict_repo_url_validation=True, github_validation_token="ghp_fallback")

    with patch("repo_service.crud.get_settings", return_value=settings):
        with patch("repo_service.crud.urlopen", return_value=_FakeResponse()) as mocked_urlopen:
            _assert_github_url_reachable("https://github.com/example/acme-service")

    request = mocked_urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer ghp_fallback"
