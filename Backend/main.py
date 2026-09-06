import os
import shutil
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer

from datetime import datetime, date
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List 

import models
import schemas
from database import engine, get_db

# This tells SQLAlchemy to create all tables defined in models.py if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Infrastructure Progress Tracker")
# Load local sentence embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

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
def process_and_match_report(report_id: str, daily_notes: List[str], db: Session = Depends(get_db)):
    schedule_items = db.query(models.ScheduleActivity).all()
    if not schedule_items:
        raise HTTPException(status_code=400, detail="No schedule activities available to match against.")

    # Compute schedule embeddings
    schedule_embeddings = [(item, model.encode(item.activity_name).tolist()) for item in schedule_items]

    results = []
    for note in daily_notes:
        extracted = models.ExtractedActivity(id=uuid.uuid4(),report_id=uuid.UUID(report_id), raw_text=note)
        db.add(extracted)
        db.commit()
        db.refresh(extracted)

        note_emb = model.encode(note).tolist()
        best_score = -1.0
        best_item = None

        for item, s_emb in schedule_embeddings:
            score = compute_similarity(note_emb, s_emb)
            if score > best_score:
                best_score = score
                best_item = item

        # Auto-approve matches >= 0.80, route lower scores to review queue
        status = "AUTO_APPROVED" if best_score >= 0.80 else "PENDING"

        match = models.ActivityMatch(
            id=uuid.uuid4(),
            extracted_activity_id=extracted.id,
            schedule_activity_id=best_item.id,
            confidence_score=round(best_score, 3),
            status=status
        )
        db.add(match)
        db.commit()

        results.append({
            "site_note": note,
            "matched_activity": best_item.activity_name,
            "confidence_score": round(best_score, 3),
            "status": status
        })

    return {"matches": results}


# 6. Planner Review Queue: Retrieve uncertain matches (< 0.80)
@app.get("/api/v1/matches/review-queue")
def get_review_queue(db: Session = Depends(get_db)):
    pending = db.query(models.ActivityMatch).filter(models.ActivityMatch.status == "PENDING").all()
    queue = []
    for m in pending:
        extracted = db.query(models.ExtractedActivity).filter(models.ExtractedActivity.id == m.extracted_activity_id).first()
        sched = db.query(models.ScheduleActivity).filter(models.ScheduleActivity.id == m.schedule_activity_id).first()
        queue.append({
            "match_id": m.id,
            "site_note": extracted.raw_text if extracted else "Unknown",
            "suggested_schedule_task": sched.activity_name if sched else "Unknown",
            "confidence_score": float(m.confidence_score),
            "status": m.status
        })
    return queue


# 7. Planner Decision: Approve or Reject a match
@app.patch("/api/v1/matches/{match_id}/review")
def review_match(
    match_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    try:
        # Try both UUID object and raw string to guarantee SQLite match
        target_uuid = None
        try:
            target_uuid = uuid.UUID(match_id)
        except Exception:
            pass

        match = None
        if target_uuid:
            match = db.query(models.ActivityMatch).filter(models.ActivityMatch.id == target_uuid).first()
        if not match:
            match = db.query(models.ActivityMatch).filter(models.ActivityMatch.id == match_id).first()

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        action = str(payload.get("action", "")).strip().upper()
        if action == "APPROVE":
            match.status = "MANUALLY_APPROVED"
        elif action == "REJECT":
            match.status = "REJECTED"
        else:
            raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT")

        db.commit()
        db.refresh(match)
        return {"message": f"Match status updated to {match.status}"}

    except HTTPException:
        raise
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Review error: {str(err)}")






