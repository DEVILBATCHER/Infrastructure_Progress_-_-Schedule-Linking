import uuid
from sqlalchemy import Column, String, Date, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from database import Base

# 1. Master Planned Schedule (Baseline from MS Project / Primavera)
class ScheduleActivity(Base):
    __tablename__ = "schedule_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wbs_code = Column(String(50), nullable=False)
    activity_name = Column(Text, nullable=False)
    planned_start_date = Column(Date, nullable=False)
    planned_end_date = Column(Date, nullable=False)
   # embedding = Column(Vector(384), nullable=True) # 384 dimensions for all-MiniLM-L6-v2


# 2. Uploaded Daily Reports / Spreadsheets
class SiteReport(Base):
    __tablename__ = "site_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(20), nullable=False) # 'pdf', 'xlsx', 'image'
    report_date = Column(Date, nullable=False)
    processing_status = Column(String(30), default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 3. Extracted Unstructured Entries from Reports
class ExtractedActivity(Base):
    __tablename__ = "extracted_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("site_reports.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    extracted_date = Column(Date, nullable=True)
    embedding = Column(Vector(384), nullable=True)


# 4. Matches and Planner Review Queue
class ActivityMatch(Base):
    __tablename__ = "activity_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracted_activity_id = Column(UUID(as_uuid=True), ForeignKey("extracted_activities.id"), nullable=False)
    schedule_activity_id = Column(UUID(as_uuid=True), ForeignKey("schedule_activities.id"), nullable=False)
    confidence_score = Column(Numeric(4, 3), nullable=False)
    status = Column(String(50), default="PENDING") # AUTO_APPROVED, PENDING, MANUALLY_APPROVED, REJECTED
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String, nullable=True, default="Site Planner")
    review_remarks = Column(String, nullable=True)
    

