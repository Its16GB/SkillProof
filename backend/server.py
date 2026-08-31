"""SkillProof – Job-posting-based Skills Gap Analyzer.

Backend fetches real job postings from Adzuna, then uses Claude to extract
the most common skills, grouped by category, along with salary insights,
top companies and job titles.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.cors import CORSMiddleware


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# --- Config ------------------------------------------------------------------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# Adzuna supports these country codes:
SUPPORTED_COUNTRIES: dict[str, str] = {
    "gb": "United Kingdom",
    "us": "United States",
    "at": "Austria",
    "au": "Australia",
    "be": "Belgium",
    "br": "Brazil",
    "ca": "Canada",
    "ch": "Switzerland",
    "de": "Germany",
    "es": "Spain",
    "fr": "France",
    "in": "India",
    "it": "Italy",
    "mx": "Mexico",
    "nl": "Netherlands",
    "nz": "New Zealand",
    "pl": "Poland",
    "sg": "Singapore",
    "za": "South Africa",
}

# --- App / DB ----------------------------------------------------------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="SkillProof API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("skillproof")


# --- Models ------------------------------------------------------------------
ALLOWED_CATEGORIES = {"technical", "tools", "soft", "certification"}

# --- Cache / cost-saving config ---------------------------------------------
CACHE_TTL_SECONDS = int(os.environ.get("ANALYSIS_CACHE_TTL_SECONDS", 24 * 3600))
LLM_MODEL_NAME = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
DESC_TRUNCATE_CHARS = int(os.environ.get("DESC_TRUNCATE_CHARS", 400))


class AnalyzeRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=120)
    country: str = Field(..., min_length=2, max_length=2)  # ISO 2-letter, adzuna code
    city: str | None = Field(default=None, max_length=120)
    years_experience: int = Field(..., ge=0, le=40)

    @field_validator("country")
    @classmethod
    def normalise_country(cls, v: str) -> str:
        return v.strip().lower()


class JobSample(BaseModel):
    title: str
    company: str
    location: str
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    url: str
    posted: str | None = None


class SkillFrequency(BaseModel):
    name: str
    count: int
    percentage: float
    category: str  # technical | tools | soft | certification
    source: str  # "postings" | "ai"


class AnalysisResponse(BaseModel):
    id: str
    query: AnalyzeRequest
    postings_analyzed: int
    skills: list[SkillFrequency]
    ai_suggested_skills: list[SkillFrequency]
    salary: dict[str, Any]
    top_companies: list[dict[str, Any]]
    top_titles: list[dict[str, Any]]
    samples: list[JobSample]
    created_at: str
    seniority_label: str
    cached: bool = False
    cache_age_seconds: int = 0


# --- Adzuna helpers ----------------------------------------------------------
async def fetch_adzuna_jobs(
    country: str, role: str, city: str | None, results: int = 50
) -> dict[str, Any]:
    if country not in SUPPORTED_COUNTRIES:
        raise HTTPException(400, f"Unsupported country '{country}'.")
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise HTTPException(500, "Adzuna API credentials not configured.")

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params: dict[str, Any] = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": max(10, min(50, results)),
        "what": role,
        "content-type": "application/json",
        "sort_by": "relevance",
    }
    if city:
        params["where"] = city

    async with httpx.AsyncClient(timeout=25.0) as http:
        r = await http.get(url, params=params)
        if r.status_code != 200:
            logger.error("Adzuna %s: %s", r.status_code, r.text[:300])
            raise HTTPException(
                502, f"Adzuna API error ({r.status_code}). Try a different role/location."
            )
        return r.json()


def seniority_for_years(years: int) -> str:
    if years <= 1:
        return "Entry-level / Junior"
    if years <= 3:
        return "Junior / Associate"
    if years <= 6:
        return "Mid-level"
    if years <= 10:
        return "Senior"
    return "Lead / Principal"


# --- Cache -----------------------------------------------------------------
def cache_key(role: str, country: str, city: str | None, seniority: str) -> str:
    raw = "|".join([
        role.strip().lower(),
        country.strip().lower(),
        (city or "").strip().lower(),
        seniority,
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached_analysis(key: str) -> dict[str, Any] | None:
    doc = await db.analysis_cache.find_one({"_id": key})
    if not doc:
        return None
    # Motor's TTL runs every ~60s so we double-check freshness here
    expires_at = doc.get("expires_at")
    if isinstance(expires_at, datetime):
        # Motor may return a naive datetime (MongoDB stores UTC without tz)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
    return doc.get("payload")


async def save_to_cache(key: str, payload: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    await db.analysis_cache.update_one(
        {"_id": key},
        {"$set": {
            "payload": payload,
            "cached_at": now,
            "expires_at": now + timedelta(seconds=CACHE_TTL_SECONDS),
        }},
        upsert=True,
    )


def parse_adzuna_results(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[JobSample]]:
    results = data.get("results", []) or []
    samples: list[JobSample] = []
    for j in results[:8]:
        loc = j.get("location", {}).get("display_name") or ""
        samples.append(
            JobSample(
                title=j.get("title", "Untitled"),
                company=(j.get("company") or {}).get("display_name") or "Unknown",
                location=loc,
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                currency=(j.get("salary_is_predicted") and "predicted") or None,
                url=j.get("redirect_url", "#"),
                posted=j.get("created"),
            )
        )
    return results, samples


# --- LLM extraction ----------------------------------------------------------
SKILL_SYSTEM = (
    "You are a senior technical recruiter and labor-market analyst. "
    "Extract concrete, resume-worthy skills from job descriptions. "
    "Skills must be short (1-4 words), canonical (e.g. 'Python', 'AWS', 'React', "
    "'Communication', 'Kubernetes', 'PMP'), and NEVER include generic filler like "
    "'team player', 'fast learner', 'strong background'. Respond ONLY with valid JSON."
)


def _clean_desc(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    # Strip common boilerplate lines that add tokens without info
    text = re.sub(
        r"(equal opportunity employer|about us|about the company|about the role|"
        r"we are committed to|we celebrate diversity|please note)[^.]*\.",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text[:DESC_TRUNCATE_CHARS]


async def extract_skills_with_llm(
    role: str,
    seniority: str,
    years: int,
    descriptions: list[str],
) -> dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    joined = "\n\n---\n\n".join(
        f"[Posting {i + 1}]\n{_clean_desc(d)}" for i, d in enumerate(descriptions)
    )
    total = len(descriptions)

    prompt = f"""Analyse the {total} job postings below for a "{role}" role at
{seniority} level ({years} years of experience).

STEP 1 - Extract every meaningful skill appearing in the postings and count
how many DISTINCT postings it appears in. Categorise each skill into exactly
one of: technical | tools | soft | certification.

STEP 2 - Add up to 8 AI_SUGGESTED skills a strong {seniority} {role} should
have that are UNDER-REPRESENTED in the postings but valuable given
{years} yrs experience.

Return STRICT JSON in this exact shape:
{{
  "skills": [
    {{"name": "Python", "count": 34, "category": "technical"}},
    {{"name": "AWS", "count": 22, "category": "tools"}}
  ],
  "ai_suggested_skills": [
    {{"name": "System Design", "category": "technical",
      "reason": "Expected at senior level for scaling teams"}}
  ]
}}

Rules: max 30 items in skills, sorted by count DESC; counts must not exceed {total};
skill names capitalised properly (e.g. "TypeScript" not "typescript"). No prose,
no markdown, only JSON.

POSTINGS:
{joined}
"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": LLM_MODEL_NAME,
        "max_tokens": 6000,
        "system": SKILL_SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "skills": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "count": {"type": "integer"},
                                    "category": {
                                        "type": "string",
                                        "enum": [
                                            "technical",
                                            "tools",
                                            "soft",
                                            "certification",
                                        ],
                                    },
                                },
                                "required": ["name", "count", "category"],
                                "additionalProperties": False,
                            },
                        },
                        "ai_suggested_skills": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "category": {
                                        "type": "string",
                                        "enum": [
                                            "technical",
                                            "tools",
                                            "soft",
                                            "certification",
                                        ],
                                    },
                                    "reason": {"type": "string"},
                                },
                                "required": ["name", "category", "reason"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["skills", "ai_suggested_skills"],
                    "additionalProperties": False,
                },
            }
        },
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as http:
            response = await http.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
        if response.status_code >= 400:
            logger.error("Anthropic %s: %s", response.status_code, response.text[:500])
            raise HTTPException(502, f"AI extraction failed ({response.status_code})")
        body = response.json()
        if body.get("stop_reason") == "max_tokens":
            logger.error(
                "Claude output truncated at max_tokens; usage=%s",
                body.get("usage"),
            )
            raise HTTPException(502, "AI response exceeded the output token limit")
        text = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("LLM error")
        raise HTTPException(502, f"AI extraction failed: {e}") from e
    # Parse Claude JSON response safely
    cleaned_text = text.strip()

    # Remove Markdown code fences if Claude included them
    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        ).strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError:
        # Fallback: extract the outermost JSON object
        start = cleaned_text.find("{")
        end = cleaned_text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            logger.error("Claude returned non-JSON output: %s", cleaned_text[:1000])
            raise HTTPException(502, "AI returned unparseable output")

        candidate = cleaned_text[start:end + 1]

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as e:
            logger.error(
                "Claude returned invalid JSON: %s",
                candidate[:1000],
            )
            raise HTTPException(
                502,
                f"AI JSON parse error: {e}",
            ) from e

    return parsed


# --- Aggregations ------------------------------------------------------------
def aggregate_salary(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    mins = [j.get("salary_min") for j in jobs if j.get("salary_min")]
    maxs = [j.get("salary_max") for j in jobs if j.get("salary_max")]
    if not mins and not maxs:
        return {"available": False}
    all_vals = mins + maxs
    return {
        "available": True,
        "count": len(all_vals),
        "min": min(all_vals),
        "max": max(all_vals),
        "avg": round(sum(all_vals) / len(all_vals), 2),
        "avg_min": round(sum(mins) / len(mins), 2) if mins else None,
        "avg_max": round(sum(maxs) / len(maxs), 2) if maxs else None,
    }


def aggregate_field(jobs: list[dict[str, Any]], path: list[str], top: int = 8):
    tally: dict[str, int] = {}
    for j in jobs:
        v: Any = j
        for k in path:
            v = (v or {}).get(k) if isinstance(v, dict) else None
        if v:
            tally[str(v)] = tally.get(str(v), 0) + 1
    ranked = sorted(tally.items(), key=lambda x: x[1], reverse=True)[:top]
    return [{"name": n, "count": c} for n, c in ranked]


# --- Routes ------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"service": "SkillProof", "status": "ok"}


@api_router.get("/countries")
async def get_countries():
    return [{"code": k, "name": v} for k, v in SUPPORTED_COUNTRIES.items()]


@api_router.post("/analyze", response_model=AnalysisResponse)
async def analyze(req: AnalyzeRequest):
    logger.info(
        "Analyze role=%s country=%s city=%s years=%s",
        req.role, req.country, req.city, req.years_experience,
    )

    seniority = seniority_for_years(req.years_experience)
    ck = cache_key(req.role, req.country, req.city, seniority)

    # Cache hit → return instantly, no Adzuna / LLM call
    cached = await get_cached_analysis(ck)
    if cached:
        try:
            cached_at = datetime.fromisoformat(cached.get("created_at"))
            age = int((datetime.now(timezone.utc) - cached_at).total_seconds())
        except Exception:  # noqa: BLE001
            age = 0
        cached["cached"] = True
        cached["cache_age_seconds"] = age
        # Reissue a fresh id so the frontend can key React lists
        cached["id"] = str(uuid.uuid4())
        # Overwrite the query with the current one (same bucket, may differ in city case)
        cached["query"] = req.model_dump()
        logger.info("cache HIT key=%s age=%ss", ck[:8], age)
        return cached

    data = await fetch_adzuna_jobs(req.country, req.role, req.city, 50)
    results, samples = parse_adzuna_results(data)

    if not results:
        raise HTTPException(
            404,
            "No postings found. Try a broader role, remove the city, or pick another country.",
        )

    descriptions = [r.get("description", "") for r in results if r.get("description")]
    llm_result = await extract_skills_with_llm(
        req.role, seniority, req.years_experience, descriptions
    )

    total = len(descriptions)
    raw_skills = llm_result.get("skills", [])
    skills: list[SkillFrequency] = []
    for s in raw_skills:
        try:
            count = int(s.get("count", 0))
            count = min(count, total)
            if count <= 0:
                continue
            category = str(s.get("category", "technical")).lower().strip()
            if category not in ALLOWED_CATEGORIES:
                category = "technical"
            skills.append(
                SkillFrequency(
                    name=str(s.get("name", "")).strip(),
                    count=count,
                    percentage=round(count * 100 / total, 1),
                    category=category,
                    source="postings",
                )
            )
        except (ValueError, TypeError):
            continue
    skills.sort(key=lambda x: x.count, reverse=True)
    skills = skills[:30]

    ai_skills: list[SkillFrequency] = []
    for s in llm_result.get("ai_suggested_skills", []) or []:
        cat = str(s.get("category", "technical")).lower().strip()
        if cat not in ALLOWED_CATEGORIES:
            cat = "technical"
        ai_skills.append(
            SkillFrequency(
                name=str(s.get("name", "")).strip(),
                count=0,
                percentage=0.0,
                category=cat,
                source="ai",
            )
        )

    salary = aggregate_salary(results)
    top_companies = aggregate_field(results, ["company", "display_name"], 8)
    top_titles = aggregate_field(results, ["title"], 8)

    resp = AnalysisResponse(
        id=str(uuid.uuid4()),
        query=req,
        postings_analyzed=total,
        skills=skills,
        ai_suggested_skills=ai_skills,
        salary=salary,
        top_companies=top_companies,
        top_titles=top_titles,
        samples=samples,
        created_at=datetime.now(timezone.utc).isoformat(),
        seniority_label=seniority,
    )

    # Persist audit trail + populate cache
    doc = json.loads(resp.model_dump_json())
    try:
        await db.analyses.insert_one({**doc, "_id": doc["id"]})
    except Exception:  # noqa: BLE001
        logger.exception("failed to persist analysis")
    try:
        await save_to_cache(ck, doc)
    except Exception:  # noqa: BLE001
        logger.exception("failed to write cache")

    return resp


@api_router.get("/recent")
async def recent_analyses(limit: int = Query(8, ge=1, le=50)):
    cursor = db.analyses.find(
        {},
        {"_id": 0, "id": 1, "query": 1, "postings_analyzed": 1, "created_at": 1, "seniority_label": 1},
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _ensure_indexes():
    try:
        await db.analysis_cache.create_index("expires_at", expireAfterSeconds=0)
        await db.analyses.create_index([("created_at", -1)])
        logger.info("indexes ensured (TTL on analysis_cache.expires_at)")
    except Exception:  # noqa: BLE001
        logger.exception("failed to ensure indexes")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
