import os
import shutil
from datetime import date
from fastapi import FastAPI, Depends, HTTPException
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
    saved_file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(saved_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save report metadata to DB
    new_report = models.SiteReport(
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



