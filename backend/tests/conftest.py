import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = _base.rstrip("/")

ANALYZE_TIMEOUT = 180
VALID_CATEGORIES = {"technical", "tools", "soft", "certification"}


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


def assert_skill_shape(skill, postings_analyzed, expected_source):
    assert isinstance(skill["name"], str) and skill["name"].strip()
    assert isinstance(skill["count"], int)
    assert skill["count"] <= postings_analyzed, (
        f"skill {skill['name']} count {skill['count']} > postings {postings_analyzed}"
    )
    assert skill["category"] in VALID_CATEGORIES, f"bad category {skill['category']}"
    assert skill["source"] == expected_source
    assert 0 <= skill["percentage"] <= 100
