import os
import shutil
import uuid
import numpy as np
import re 
import csv
import io
from sentence_transformers import SentenceTransformer

from datetime import datetime, date
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Response, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List 

import models
import schemas
from database import engine, get_db

# This tells SQLAlchemy to create all tables defined in models.py if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Infrastructure Progress Tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load local sentence embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def is_valid_site_note(text: str) -> bool:
    cleaned = text.strip()

    # Skip strings that are too short to be actual construction tasks
    if len(cleaned) < 8:
        return False

    # Skip date-only lines (e.g., "Date: 07/09/2026", "12/09/2026")
    date_pattern = r"^(date\s*[:\-\/]?\s*)?\d{1,4}[\.\-\/]\d{1,2}[\.\-\/]\d{2,4}$"
    if re.match(date_pattern, cleaned, re.IGNORECASE):
        return False

    # Skip report headers, page numbering, and standard metadata labels
    metadata_patterns = [
        r"^page\s+\d+(\s+of\s+\d+)?$",
        r"^(site\s+report|daily\s+log|daily\s+progress\s+report)$",
        r"^(weather|temperature|location)\s*[:\-].*",
        r"^(prepared\s+by|approved\s+by|signature)\s*[:\-].*"
    ]
    for pattern in metadata_patterns:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return False

    return True



def compute_similarity(emb1, emb2):
    vec1 = np.array(emb1)
    vec2 = np.array(emb2)
    norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return float(np.dot(vec1, vec2) / norm) if norm != 0 else 0.0


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "backend is running successfully"}

# 1. Add a single schedule activity
@app.post("/api/v1/schedule/activities", response_model=schemas.ScheduleActivityResponse)
def create_activity(activity: schemas.ScheduleActivityCreate, db: Session = Depends(get_db)):
    db_activity = models.ScheduleActivity(
        wbs_code=activity.wbs_code,
        activity_name=activity.activity_name,
        planned_start_date=activity.planned_start_date,
        planned_end_date=activity.planned_end_date
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

# 2. Get all schedule activities
@app.get("/api/v1/schedule/activities", response_model=List[schemas.ScheduleActivityResponse])
def get_activities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    activities = db.query(models.ScheduleActivity).offset(skip).limit(limit).all()
    return activities
# Create local folder for storing uploaded reports
UPLOAD_DIR = "./uploaded_reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from pypdf import PdfReader

def extract_notes_from_pdf(file_path: str) -> list[str]:
    """Reads lines from a PDF and filters out empty lines."""
    notes = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                cleaned = line.strip()
                # Ignore empty strings or very short artifacts
                if len(cleaned) > 5:
                    notes.append(cleaned)
    except Exception as e:
        print(f"PDF extraction error: {e}")
    return notes


# 3. Upload a site report (PDF, Excel, or Image)
@app.post("/api/v1/reports/upload", response_model=schemas.SiteReportResponse)
def upload_report(
    report_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):    
    # Determine file extension
    file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"
    
    # Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved_file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(saved_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save report metadata to DB
    new_report = models.SiteReport(
        id=uuid.uuid4(),
        file_name=file.filename,
        file_url=saved_file_path,
        file_type=file_extension,
        report_date=report_date,
        processing_status="PENDING"
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report

# 4. Get list of all uploaded reports and their statuses
@app.get("/api/v1/reports", response_model=List[schemas.SiteReportResponse])
def get_reports(db: Session = Depends(get_db)):
    return db.query(models.SiteReport).order_by(models.SiteReport.created_at.desc()).all()
# 5. Semantic Matcher: Match unstructured daily site logs to schedule items
@app.post("/api/v1/reports/{report_id}/process")
def process_and_match_report(
    report_id: str,
    manual_notes: list[str] = None,
    db: Session = Depends(get_db)
):
    try:
        # 1. Convert report_id string cleanly to a UUID object
        clean_uuid = uuid.UUID(str(report_id).strip())
        
        # query using the UUID object
        report = db.query(models.SiteReport).filter(models.SiteReport.id == clean_uuid).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found in database")

        # 2. Fetch report supporting both UUID and string types
        clean_uuid = uuid.UUID(str(report_id).strip())
        report = db.query(models.SiteReport).filter(models.SiteReport.id == clean_uuid).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found in database")

         # 3. Retrieve site notes
        raw_notes = manual_notes or []
        if not raw_notes:
            # Resolve absolute path regardless of current working directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.normpath(report.file_url)

            # Check direct path first, then check relative to main.py location
            if not os.path.exists(file_path):
                file_path = os.path.normpath(os.path.join(base_dir, report.file_url))

            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found on disk at {file_path}"
                )

            raw_notes = extract_notes_from_pdf(file_path)

        # Apply noise filtering
        site_notes = [note.strip() for note in raw_notes if is_valid_site_note(note)]

        if not site_notes:
            return {"message": "No actionable construction activities found in the report.", "matches": []}


        # 4. Fetch schedule activities
        # Change models.ScheduleTask -> models.ScheduleActivity
        schedule_items = db.query(models.ScheduleActivity).all()
        if not schedule_items:
            raise HTTPException(status_code=400, detail="No schedule tasks found in database")

        # Change t.description -> t.activity_name
        task_descriptions = [t.activity_name for t in schedule_items]
        task_embeddings = model.encode(task_descriptions, normalize_embeddings=True)
        note_embeddings = model.encode(site_notes, normalize_embeddings=True)

        results = []
        for idx, note in enumerate(site_notes):
            similarities = np.dot(task_embeddings, note_embeddings[idx])
            best_match_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_match_idx])
            best_task = schedule_items[best_match_idx]

            status = "AUTO_APPROVED" if best_score >= 0.80 else "PENDING"

             # 1. Create the Extracted Activity entry
            extracted_record = models.ExtractedActivity(
                id=uuid.uuid4(),
                report_id=report.id,
                raw_text=note
            )
            db.add(extracted_record)
            db.flush()

            # 2. Link extracted activity to schedule activity
            match_record = models.ActivityMatch(
                id=uuid.uuid4(),
                extracted_activity_id=extracted_record.id,
                schedule_activity_id=best_task.id,
                confidence_score=round(best_score, 3),
                status=status
            )
            db.add(match_record)
            
            results.append({
                "site_note": note,
                "matched_activity": best_task.activity_name,
                "confidence_score": round(best_score, 3),
                "status": status
            })
            report.processing_status = "COMPLETED"
            db.commit()

        return {"extracted_count": len(results), "matches": results}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# 6. Planner Review Queue: Retrieve uncertain matches (< 0.80)
@app.get("/api/v1/matches/review-queue")
def get_review_queue(db: Session = Depends(get_db)):
    try:
        matches = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.status == "PENDING")
            .all()
        )
        queue = []
        for m in matches:
            extracted_text = "N/A"
            if getattr(m, "extracted_activity_id", None):
                extracted = db.query(models.ExtractedActivity).filter(
                    models.ExtractedActivity.id == m.extracted_activity_id
                ).first()
                if extracted and getattr(extracted, "raw_text", None):
                    extracted_text = extracted.raw_text

            task_name = "N/A"
            if getattr(m, "schedule_activity_id", None):
                schedule = db.query(models.ScheduleActivity).filter(
                    models.ScheduleActivity.id == m.schedule_activity_id
                ).first()
                if schedule and getattr(schedule, "activity_name", None):
                    task_name = schedule.activity_name

            score = float(m.confidence_score) if m.confidence_score is not None else 0.0

            queue.append({
                "match_id": str(m.id),
                "site_note": extracted_text,
                "suggested_schedule_task": task_name,
                "confidence_score": round(score, 3),
                "status": m.status
            })
        return queue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review queue failed: {str(e)}")



# 7. Planner Decision: Approve or Reject a match
@app.patch("/api/v1/matches/{match_id}/review")
def review_match(
    match_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    try:
        # Resolve UUID or raw string
        clean_id = str(match_id).strip()
        match = None
        try:
            target_uuid = uuid.UUID(clean_id)
            match = db.query(models.ActivityMatch).filter(models.ActivityMatch.id == target_uuid).first()
        except Exception:
            pass

        if not match:
            match = db.query(models.ActivityMatch).filter(models.ActivityMatch.id == clean_id).first()

        if not match:
            raise HTTPException(status_code=404, detail="Activity match not found")

        action = str(payload.get("action", "")).strip().upper()
        if not action:
            raise HTTPException(status_code=400, detail="'action' field is required")

        # Save audit fields
        match.reviewed_at = datetime.utcnow()
        match.reviewed_by = payload.get("reviewer_name", "Site Planner")
        match.review_remarks = payload.get("remarks")

        if action == "APPROVE":
            match.status = "MANUALLY_APPROVED"
        elif action == "REJECT":
            match.status = "REJECTED"
        elif action == "REASSIGN":
            new_sched_id = payload.get("corrected_schedule_activity_id")
            if not new_sched_id:
                raise HTTPException(status_code=400, detail="corrected_schedule_activity_id required for reassignment")
            match.schedule_activity_id = uuid.UUID(str(new_sched_id).strip())
            match.status = "MANUALLY_APPROVED"
            match.confidence_score = 1.0
        else:
            raise HTTPException(status_code=400, detail="Action must be APPROVE, REJECT, or REASSIGN")

        db.commit()
        db.refresh(match)

        return {
            "message": f"Match status updated to {match.status}",
            "match_id": str(match.id),
            "reviewed_by": match.reviewed_by,
            "reviewed_at": str(match.reviewed_at),
            "remarks": match.review_remarks
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Review update failed: {str(e)}")


# 8. Analytics and Progress of the report :
@app.get("/api/v1/analytics/progress")
def get_progress_summary(db: Session = Depends(get_db)):
    try:
        # 1. Fetch all planned baseline schedule tasks
        total_activities = db.query(models.ScheduleActivity).all()
        total_tasks_count = len(total_activities)

        if total_tasks_count == 0:
            return {
                "overall_progress_percentage": 0.0,
                "total_scheduled_activities": 0,
                "verified_activities_count": 0,
                "pending_review_count": 0,
                "activities": []
            }

        # 2. Query matches grouped by schedule_activity_id
        approved_statuses = ["AUTO_APPROVED", "MANUALLY_APPROVED"]

        # Fetch all approved matches
        approved_matches = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.status.in_(approved_statuses))
            .all()
        )
        approved_task_ids = {m.schedule_activity_id for m in approved_matches if m.schedule_activity_id}

        # Fetch pending matches count
        pending_count = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.status == "PENDING")
            .count()
        )

        # 3. Build task-by-task breakdown
        breakdown = []
        for task in total_activities:
            # Count how many approved reports back this activity
            matches_for_task = [m for m in approved_matches if m.schedule_activity_id == task.id]
            is_active = len(matches_for_task) > 0

            breakdown.append({
                "activity_id": str(task.id),
                "wbs_code": getattr(task, "wbs_code", "N/A"),
                "activity_name": task.activity_name,
                "status": "IN_PROGRESS / VERIFIED" if is_active else "NOT_STARTED",
                "verified_matches_count": len(matches_for_task),
                "planned_start_date": str(task.planned_start_date) if getattr(task, "planned_start_date", None) else None,
                "planned_end_date": str(task.planned_end_date) if getattr(task, "planned_end_date", None) else None
            })

        # 4. Calculate overall progress metric
        verified_count = len(approved_task_ids)
        coverage_percentage = round((verified_count / total_tasks_count) * 100, 2)

        return {
            "overall_progress_percentage": coverage_percentage,
            "total_scheduled_activities": total_tasks_count,
            "verified_activities_count": verified_count,
            "pending_review_count": pending_count,
            "activities": breakdown
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate progress summary: {str(e)}")

# 9--- Seed Baseline Schedule Tasks ---
@app.post("/api/v1/schedule/seed-baseline")
def seed_baseline_schedule(db: Session = Depends(get_db)):
    baseline_activities = [
        {
            "wbs_code": "1.1",
            "activity_name": "Excavation and foundation groundwork",
            "planned_start_date": date(2026, 9, 1),
            "planned_end_date": date(2026, 9, 15)
        },
        {
            "wbs_code": "1.2",
            "activity_name": "Reinforced concrete pillar and slab casting",
            "planned_start_date": date(2026, 9, 16),
            "planned_end_date": date(2026, 10, 5)
        },
        {
            "wbs_code": "2.1",
            "activity_name": "Brickwork and masonry construction",
            "planned_start_date": date(2026, 10, 6),
            "planned_end_date": date(2026, 10, 25)
        },
        {
            "wbs_code": "2.2",
            "activity_name": "Electrical wiring and conduit rough-in",
            "planned_start_date": date(2026, 10, 26),
            "planned_end_date": date(2026, 11, 10)
        },
        {
            "wbs_code": "3.1",
            "activity_name": "Interior and exterior surface painting",
            "planned_start_date": date(2026, 11, 11),
            "planned_end_date": date(2026, 11, 30)
        }
    ]

    created = []
    for item in baseline_activities:
        existing = db.query(models.ScheduleActivity).filter(
            models.ScheduleActivity.activity_name == item["activity_name"]
        ).first()

        if not existing:
            new_activity = models.ScheduleActivity(
                id=uuid.uuid4(),
                wbs_code=item["wbs_code"],
                activity_name=item["activity_name"],
                planned_start_date=item["planned_start_date"],
                planned_end_date=item["planned_end_date"]
            )
            db.add(new_activity)
            created.append(item["activity_name"])

    db.commit()
    return {
        "message": f"Successfully seeded {len(created)} baseline tasks.",
        "added_activities": created
    }
#---10 export file
@app.get("/api/v1/analytics/progress/export")
def export_progress_summary_csv(db: Session = Depends(get_db)):
    try:
        activities = db.query(models.ScheduleActivity).all()
        approved_statuses = ["AUTO_APPROVED", "MANUALLY_APPROVED"]
        
        approved_matches = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.status.in_(approved_statuses))
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "WBS Code",
            "Activity Name",
            "Status",
            "Verified Matches Count",
            "Planned Start Date",
            "Planned End Date"
        ])

        for task in activities:
            task_matches = [m for m in approved_matches if m.schedule_activity_id == task.id]
            is_active = len(task_matches) > 0
            
            writer.writerow([
                getattr(task, "wbs_code", "N/A"),
                task.activity_name,
                "IN_PROGRESS / VERIFIED" if is_active else "NOT_STARTED",
                len(task_matches),
                str(task.planned_start_date) if getattr(task, "planned_start_date", None) else "",
                str(task.planned_end_date) if getattr(task, "planned_end_date", None) else ""
            ])

        csv_content = output.getvalue()
        output.close()

        headers = {
            "Content-Disposition": "attachment; filename=project_progress_summary.csv"
        }
        return Response(content=csv_content, media_type="text/csv", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# 11__ Analytics delay:
@app.get("/api/v1/analytics/delays")
def detect_project_delays(db: Session = Depends(get_db)):
    try:
        today = date.today()
        activities = db.query(models.ScheduleActivity).all()
        approved_statuses = ["AUTO_APPROVED", "MANUALLY_APPROVED"]

        # Fetch verified matches
        approved_matches = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.status.in_(approved_statuses))
            .all()
        )

        delayed_activities = []
        on_track_activities = []

        for task in activities:
            task_matches = [m for m in approved_matches if m.schedule_activity_id == task.id]
            is_active = len(task_matches) > 0

            # Safe date conversions
            start = task.planned_start_date
            end = task.planned_end_date

            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()

            delay_reason = None
            severity = "LOW"
            days_overdue = 0

            # 1. Condition: Activity should have started, but zero verified reports
            if start and today > start and not is_active:
                days_overdue = (today - start).days
                delay_reason = "Activity not started despite passing planned start date."
                severity = "HIGH" if days_overdue > 7 else "MEDIUM"

            # 2. Condition: Activity passed its completion date without sustained progress
            elif end and today > end:
                days_overdue = (today - end).days
                delay_reason = "Activity passed planned finish date."
                severity = "CRITICAL"

            item = {
                "activity_id": str(task.id),
                "wbs_code": getattr(task, "wbs_code", "N/A"),
                "activity_name": task.activity_name,
                "verified_matches": len(task_matches),
                "planned_start": str(start) if start else None,
                "planned_end": str(end) if end else None,
                "days_overdue": days_overdue,
                "delay_reason": delay_reason,
                "severity": severity if delay_reason else "NONE"
            }

            if delay_reason:
                delayed_activities.append(item)
            else:
                on_track_activities.append(item)

        return {
            "evaluation_date": str(today),
            "total_activities": len(activities),
            "delayed_activities_count": len(delayed_activities),
            "on_track_activities_count": len(on_track_activities),
            "delays": delayed_activities,
            "on_track": on_track_activities
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delay analysis failed: {str(e)}")
# 12___Audit logs
@app.get("/api/v1/matches/audit-log")
def get_audit_trail(db: Session = Depends(get_db)):
    try:
        reviewed_records = (
            db.query(models.ActivityMatch)
            .filter(models.ActivityMatch.reviewed_at.isnot(None))
            .order_by(models.ActivityMatch.reviewed_at.desc())
            .all()
        )

        log = []
        for r in reviewed_records:
            extracted_obj = (
                db.query(models.ExtractedActivity)
                .filter(models.ExtractedActivity.id == r.extracted_activity_id)
                .first()
            )

            site_note = extracted_obj.raw_text if extracted_obj else "Verified Construction Note"

            log.append({
                "match_id": str(r.id),
                "site_note": site_note,
                "status": r.status,
                "reviewed_by": getattr(r, "reviewed_by", "Site Planner"),
                "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
                "remarks": getattr(r, "review_remarks", None),
                "confidence_score": float(r.confidence_score) if r.confidence_score is not None else None
            })

        return log

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit log: {str(e)}")

