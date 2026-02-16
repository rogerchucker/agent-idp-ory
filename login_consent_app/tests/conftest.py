import os
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Must be set before importing main.
os.environ["SKIP_STARTUP_HYDRA_CHECK"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def _cookie_header(name: str, value: str) -> dict[str, str]:
    return {"Cookie": f"{name}={value}"}


@pytest.fixture
def user_cookie_header() -> dict[str, str]:
    return _cookie_header(main.COOKIE_NAME, main.build_session_cookie("user:raj@example.com"))


@pytest.fixture
def admin_cookie_header() -> dict[str, str]:
    return _cookie_header(main.ADMIN_COOKIE_NAME, main.build_admin_cookie(main.ADMIN_USERNAME))


@pytest.fixture
def hydra_state() -> dict[str, Any]:
    return {
        "login_challenge": "lc-1",
        "consent_challenge": "cc-1",
        "login_accepted": False,
        "consent_accepted": False,
    }
