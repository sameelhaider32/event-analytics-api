"""
schemas.py — Pydantic models for request/response validation.

These models define the shape of data going in and out of the API.
FastAPI uses them automatically for validation and documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------

class AssetCreate(BaseModel):
    """What the client sends when creating a new asset."""
    id: Optional[str] = None          # optional — server generates uuid4 if missing
    name: str = Field(..., min_length=1, description="Asset name (required)")
    type: str = Field(..., min_length=1, description="Asset type, e.g. 'server', 'device'")


class Asset(BaseModel):
    """What the API returns for an asset."""
    id: str
    name: str
    type: str
    created_at: str


# ---------------------------------------------------------------------------
# Operator schemas
# ---------------------------------------------------------------------------

class OperatorCreate(BaseModel):
    """What the client sends when creating a new operator."""
    id: Optional[str] = None          # optional — server generates uuid4 if missing
    name: str = Field(..., min_length=1, description="Operator name (required)")


class Operator(BaseModel):
    """What the API returns for an operator."""
    id: str
    name: str
    created_at: str


# ---------------------------------------------------------------------------
# Event schemas (Phase 2)
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    """What the client sends when creating a new event."""
    timestamp: str = Field(..., description="ISO 8601 timestamp string")
    asset_id: str = Field(..., min_length=1, description="ID of the asset this event belongs to")
    operator_id: Optional[str] = None
    type: str = Field(..., min_length=1, description="Event type, e.g. 'cpu_spike', 'login'")
    severity: int = Field(..., ge=1, le=5, description="Severity level 1 (low) to 5 (critical)")
    metadata: Optional[dict] = Field(default_factory=dict)


class Event(BaseModel):
    """What the API returns for an event."""
    id: int
    timestamp: str
    asset_id: str
    operator_id: Optional[str] = None
    type: str
    severity: int
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analytics schemas (Phase 3)
# ---------------------------------------------------------------------------

class AnalyticsSummary(BaseModel):
    """What the API returns for the /analytics/summary endpoint."""
    filters: dict
    total_events: int
    avg_severity: Optional[float]
    counts_by_type: dict
    counts_by_severity: dict
    top_assets: list
    top_operators: list


# ---------------------------------------------------------------------------
# Health Score schemas (Phase 4)
# ---------------------------------------------------------------------------

class HealthScoreBreakdown(BaseModel):
    """Detailed deductions breakdown for a health score."""
    severity_sum: int
    high_sev_count: int
    error_count: int
    deduction_severity: int
    deduction_high: int
    deduction_error: int


class HealthScoreResponse(BaseModel):
    """What the API returns for the /score/health endpoint."""
    filters: dict
    window_hours: int
    total_events: int
    score: int
    status: str
    breakdown: HealthScoreBreakdown


# ---------------------------------------------------------------------------
# Alerts schemas (Phase 5)
# ---------------------------------------------------------------------------

class AlertEvidence(BaseModel):
    """Details explaining why the alert fired."""
    count: int
    event_ids: Optional[list[int]] = None
    window_minutes: Optional[int] = None

class AlertResponse(BaseModel):
    """What the API returns for the /alerts endpoint."""
    alert_type: str
    asset_id: str
    operator_id: Optional[str] = None
    triggered_at: str
    severity: Optional[int] = None
    evidence: AlertEvidence
