# =============================================================================
# schemas.py
# Pydantic request and response schemas for all AI microservice routes.
# Enforces strict type, length, and content validation.
# =============================================================================

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError


def format_validation_error(e: ValidationError) -> dict:
    """Format Pydantic ValidationError into a clean, JSON-serializable dictionary."""
    clean_errors = []
    for err in e.errors():
        clean_errors.append({
            "type": str(err.get("type", "")),
            "loc": [str(loc_item) for loc_item in err.get("loc", [])],
            "msg": str(err.get("msg", ""))
        })
    first_msg = clean_errors[0]["msg"] if clean_errors else "Invalid request body"
    return {
        "error": f"Validation Error: {first_msg}",
        "details": clean_errors
    }



# ── Shared Models ────────────────────────────────────────────────────────────

class CitationItem(BaseModel):
    """Represents an authoritative source chunk retrieved from ChromaDB."""
    model_config = ConfigDict(extra="ignore")

    doc_id: str
    chunk_id: str
    source: str
    section: Optional[str] = "N/A"
    page: Optional[int] = None
    file_sha256: Optional[str] = None
    text_hash: Optional[str] = None


# ── POST /describe ───────────────────────────────────────────────────────────

class DescribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_text: str = Field(..., description="Raw text to describe")

    @field_validator("input_text")
    @classmethod
    def validate_input_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("'input_text' cannot be empty or whitespace only")
        if len(stripped) > 5000:
            raise ValueError(f"'input_text' exceeds maximum length of 5000 characters (got {len(stripped)})")
        return stripped


class DescribeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    professional_description: str
    generated_at: str
    grounded: bool = False
    citations: List[CitationItem] = []
    disclaimer: Optional[str] = None


# ── POST /categorise ─────────────────────────────────────────────────────────

DPDP_CATEGORIES = [
    "Data Collection",
    "Data Storage",
    "Data Processing",
    "Consent Management",
    "Data Breach",
    "Third-Party Sharing",
    "Data Retention",
    "User Rights"
]


class CategoriseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="Text of the compliance item to categorise")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("'text' cannot be empty or whitespace only")
        if len(stripped) > 5000:
            raise ValueError(f"'text' exceeds maximum length of 5000 characters (got {len(stripped)})")
        return stripped


class CategoriseMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_used: str = "llama-3.3-70b-versatile"
    tokens_used: int = 0
    response_time_ms: int = 0
    cached: bool = False
    is_fallback: bool = False


class CategoriseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    meta: CategoriseMeta
    grounded: bool = False
    citations: List[CitationItem] = []
    disclaimer: Optional[str] = None


# ── POST /recommend ──────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_text: str = Field(..., description="Raw description of the business process or incident")

    @field_validator("input_text")
    @classmethod
    def validate_input_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("'input_text' cannot be empty or whitespace only")
        if len(stripped) > 5000:
            raise ValueError(f"'input_text' exceeds maximum length of 5000 characters (got {len(stripped)})")
        return stripped


class RecommendationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_type: str
    description: str
    priority: str = "Medium"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        normalized = v.capitalize()
        if normalized not in {"High", "Medium", "Low"}:
            return "Medium"
        return normalized


class RecommendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommendations: List[RecommendationItem]
    grounded: bool = False
    citations: List[CitationItem] = []
    disclaimer: Optional[str] = None


# ── POST /generate-report ────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_text: str = Field(..., description="Raw description to analyze for executive report")

    @field_validator("input_text")
    @classmethod
    def validate_input_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("'input_text' cannot be empty or whitespace only")
        if len(stripped) > 5000:
            raise ValueError(f"'input_text' exceeds maximum length of 5000 characters (got {len(stripped)})")
        return stripped


class GenerateReportResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    executive_summary: str
    overview: str
    top_items: List[str]
    recommendations: List[str]
    grounded: bool = False
    citations: List[CitationItem] = []
    disclaimer: Optional[str] = None
