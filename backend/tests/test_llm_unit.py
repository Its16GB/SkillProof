"""Offline extraction regression checks; run with unittest (no live services)."""
import unittest
import os
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "skillproof_unit"}):
    import server


class ExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def extract(self, response):
        http = AsyncMock()
        http.post.return_value = response
        http.__aenter__.return_value = http
        with patch.object(server, "GROQ_API_KEY", "test-key"), patch.object(
            server.httpx, "AsyncClient", return_value=http
        ):
            result = await server.extract_skills_with_llm(
                "Software Engineer", "Mid-level", 4, ["Python and SQL"]
            )
        self.assertEqual(http.post.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(http.post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        return result, http.post.call_args.kwargs["json"]

    async def test_structured_response(self):
        result, payload = await self.extract(httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content":
                '{"skills": [], "ai_suggested_skills": []}'}}],
        }))
        self.assertEqual(result, {"skills": [], "ai_suggested_skills": []})
        self.assertEqual(payload["response_format"]["type"], "json_schema")

    async def test_rejection_has_configuration_guidance(self):
        with self.assertRaises(HTTPException) as raised:
            await self.extract(httpx.Response(400, json={"error": {
                "message": "unsupported output format"
            }}))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("LLM_MODEL", raised.exception.detail)

    async def test_truncated_response_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            await self.extract(httpx.Response(200, json={
                "choices": [{"finish_reason": "length", "message": {"content": "{"}}]
            }))
        self.assertIn("token limit", raised.exception.detail)

    async def test_rate_limit_guidance(self):
        with self.assertRaises(HTTPException) as raised:
            await self.extract(httpx.Response(429, json={"error": {}}))
        self.assertIn("usage limit", raised.exception.detail)

    async def test_missing_key(self):
        with patch.object(server, "GROQ_API_KEY", ""), self.assertRaises(HTTPException) as raised:
            await server.extract_skills_with_llm("Engineer", "Mid-level", 4, ["Python"])
        self.assertEqual(raised.exception.status_code, 500)
        self.assertIn("GROQ_API_KEY", raised.exception.detail)

    async def test_empty_and_refused_responses(self):
        for body in [
            {"choices": []},
            {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
            {"choices": [{"finish_reason": "stop", "message": {"refusal": "Refused"}}]},
            {"choices": [{"finish_reason": "stop", "message": {"content": "invalid json"}}]},
        ]:
            with self.subTest(body=body), self.assertRaises(HTTPException) as raised:
                await self.extract(httpx.Response(200, json=body))
            self.assertEqual(raised.exception.status_code, 502)

    async def test_analysis_caps_postings_and_requests_ten(self):
        jobs = [{"description": "Python", "title": "Engineer"} for _ in range(50)]
        database = AsyncMock()
        with patch.object(server, "get_cached_analysis", AsyncMock(return_value=None)), patch.object(
            server, "fetch_adzuna_jobs", AsyncMock(return_value={"results": jobs})
        ) as fetch, patch.object(server, "extract_skills_with_llm", AsyncMock(return_value={
            "skills": [], "ai_suggested_skills": []
        })) as extract, patch.object(server, "db", database), patch.object(
            server, "save_to_cache", AsyncMock()
        ):
            result = await server.analyze(server.AnalyzeRequest(
                role="Engineer", country="us", years_experience=4
            ))
        self.assertEqual(fetch.call_args.args[-1], 10)
        self.assertEqual(len(extract.call_args.args[-1]), 10)
        self.assertEqual(result.postings_analyzed, 10)

    async def test_oversized_request_guidance(self):
        with self.assertRaises(HTTPException) as raised:
            await self.extract(httpx.Response(413, json={"error": {}}))
        self.assertIn("token limit", raised.exception.detail)
        self.assertNotIn("try again later", raised.exception.detail)
