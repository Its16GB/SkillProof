"""Module: seniority_label mapping boundaries for POST /api/analyze."""
import pytest
from conftest import ANALYZE_TIMEOUT, BASE_URL


class TestSeniorityMapping:
    @pytest.mark.parametrize(
        "years,expected",
        [
            (1, "Entry-level / Junior"),
            (8, "Senior"),
            (11, "Lead / Principal"),
        ],
    )
    def test_seniority_boundaries(self, api_client, years, expected):
        r = api_client.post(
            f"{BASE_URL}/api/analyze",
            json={"role": "Project Manager", "country": "gb",
                  "years_experience": years},
            timeout=ANALYZE_TIMEOUT,
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        data = r.json()
        assert data["seniority_label"] == expected
        assert data["postings_analyzed"] >= 10
        total = data["postings_analyzed"]
        assert all(s["count"] <= total for s in data["skills"])
