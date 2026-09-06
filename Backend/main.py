from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine

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


