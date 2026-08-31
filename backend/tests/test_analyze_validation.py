"""Module: POST /api/analyze input validation and error paths."""
import pytest
from conftest import ANALYZE_TIMEOUT, BASE_URL


class TestAnalyzeValidation:
    @pytest.mark.parametrize("years", [-5, 99, 41])
    def test_invalid_years_returns_422(self, api_client, years):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "Software Engineer", "country": "gb", "city": None,
                  "years_experience": years},
            timeout=60,
        )
        assert r.status_code == 422, f"years={years} -> {r.status_code} {r.text[:200]}"

    def test_short_role_returns_422(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "a", "country": "gb", "years_experience": 3},
            timeout=60,
        )
        assert r.status_code == 422, r.text[:200]

    def test_invalid_country_returns_400(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "Software Engineer", "country": "zz", "years_experience": 3},
            timeout=60,
        )
        assert r.status_code == 400, f"got {r.status_code}: {r.text[:300]}"
        assert "zz" in r.json().get("detail", "").lower()

    def test_nonsense_role_returns_404(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "asdkjahsdgjahsdlkjh", "country": "gb",
                  "years_experience": 3},
            timeout=ANALYZE_TIMEOUT,
        )
        assert r.status_code == 404, f"got {r.status_code}: {r.text[:300]}"
        detail = r.json().get("detail", "")
        assert "No postings found" in detail
