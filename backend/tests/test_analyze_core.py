"""Module: POST /api/analyze happy path (Software Engineer / GB / London / 3 yrs)."""
import pytest
from conftest import ANALYZE_TIMEOUT, BASE_URL, assert_skill_shape


@pytest.fixture(scope="module")
def analysis(api_client):
    r = api_client.post(
        f"{BASE_URL}/api/analyze",
        json={"role": "Software Engineer", "country": "gb", "city": "London",
              "years_experience": 3},
        timeout=ANALYZE_TIMEOUT,
    )
    if r.status_code != 200:
        pytest.fail(f"analyze failed {r.status_code}: {r.text[:500]}")
    return r.json()


class TestAnalyzeHappyPath:
    def test_core_fields(self, analysis):
        assert isinstance(analysis["id"], str) and analysis["id"]
        assert analysis["postings_analyzed"] >= 10
        assert analysis["seniority_label"] == "Junior / Associate"
        assert analysis["query"]["role"] == "Software Engineer"
        assert analysis["query"]["country"] == "gb"
        assert analysis["query"]["city"] == "London"
        assert "_id" not in analysis

    def test_created_at_is_iso(self, analysis):
        from datetime import datetime
        datetime.fromisoformat(analysis["created_at"])

    def test_skills(self, analysis):
        skills = analysis["skills"]
        assert isinstance(skills, list) and len(skills) > 0
        assert len(skills) <= 30
        total = analysis["postings_analyzed"]
        for s in skills:
            assert_skill_shape(s, total, "postings")
        counts = [s["count"] for s in skills]
        assert counts == sorted(counts, reverse=True), "skills not sorted by count desc"

    def test_ai_suggested_skills(self, analysis):
        ai = analysis["ai_suggested_skills"]
        assert isinstance(ai, list) and len(ai) > 0
        for s in ai:
            assert_skill_shape(s, analysis["postings_analyzed"], "ai")

    def test_salary_block(self, analysis):
        salary = analysis["salary"]
        assert isinstance(salary, dict) and "available" in salary
        if salary["available"]:
            assert salary["min"] <= salary["avg"] <= salary["max"]
            assert salary["count"] > 0

    def test_companies_and_titles(self, analysis):
        for key in ("top_companies", "top_titles"):
            items = analysis[key]
            assert isinstance(items, list) and len(items) > 0, f"{key} empty"
            assert len(items) <= 8
            for it in items:
                assert it["name"] and isinstance(it["count"], int) and it["count"] >= 1
            counts = [i["count"] for i in items]
            assert counts == sorted(counts, reverse=True)

    def test_samples_are_real_postings(self, analysis):
        samples = analysis["samples"]
        assert isinstance(samples, list) and len(samples) > 0
        assert len(samples) <= 8
        for s in samples:
            assert s["title"]
            assert s["company"]
            assert s["url"].startswith("http"), f"bad url {s['url']}"

    def test_analysis_persisted_in_recent(self, api_client, analysis):
        r = api_client.get(f"{BASE_URL}/api/recent?limit=20", timeout=30)
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()]
        assert analysis["id"] in ids, "analysis not persisted / not returned by /api/recent"
