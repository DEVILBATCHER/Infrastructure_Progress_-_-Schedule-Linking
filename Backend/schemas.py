from pydantic import BaseModel
from datetime import date
from uuid import UUID
from typing import Optional

class ScheduleActivityCreate(BaseModel):
    wbs_code: str
    activity_name: str
    planned_start_date: date
    planned_end_date: date

class ScheduleActivityResponse(BaseModel):
    id: UUID
    wbs_code: str
    activity_name: str
    planned_start_date: date
    planned_end_date: date

    class Config:
        from_attributes = True
# --- Append to schemas.py ---

class SiteReportResponse(BaseModel):
    id: UUID
    file_name: str
    file_url: str
    file_type: str
    report_date: date
    processing_status: str

    class Config:
        from_attributes = True        
# --- Append to schemas.py ---

class ActivityMatchResponse(BaseModel):
    id: UUID
    extracted_text: str
    matched_schedule_name: str
    confidence_score: float
    status: str

    class Config:
        from_attributes = True

class MatchReviewAction(BaseModel):
    action: str # "APPROVE" or "REJECT"
