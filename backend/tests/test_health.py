"""Module: root + countries metadata endpoints."""
from conftest import BASE_URL

EXPECTED_COUNTRY_COUNT = 19


class TestHealthAndMeta:
    def test_root_status_ok(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "SkillProof"

    def test_countries_list(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/countries", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == EXPECTED_COUNTRY_COUNT, f"expected 19 got {len(data)}"
        codes = {c["code"] for c in data}
        for c in data:
            assert set(c.keys()) == {"code", "name"}
            assert len(c["code"]) == 2
            assert c["name"]
        for expected in ("gb", "us", "in"):
            assert expected in codes

    def test_recent_analyses(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/recent", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list)
        for item in data:
            assert "_id" not in item, "Mongo _id leaked into /api/recent response"
            assert "id" in item and "created_at" in item
            assert "query" in item and "seniority_label" in item
        created = [i["created_at"] for i in data]
        assert created == sorted(created, reverse=True), "recent not sorted desc"


class TestRecentEdgeCases:
    """Known bugs documented as regression tests."""

    def test_negative_limit_should_not_500(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/recent?limit=-1", timeout=30)
        assert r.status_code != 500, (
            "BUG: motor to_list(length=-1) raises ValueError -> 500. "
            "Use Query(8, ge=1, le=50)."
        )
        assert r.status_code in (200, 422)

    def test_non_integer_limit_returns_422(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/recent?limit=abc", timeout=30)
        assert r.status_code == 422


class TestCountryCodeCasing:
    def test_uppercase_country_code(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "Software Engineer", "country": "GB", "years_experience": 3},
            timeout=60,
        )
        assert r.status_code != 400, (
            "BUG: uppercase ISO code rejected; backend should normalise country to lowercase"
        )
