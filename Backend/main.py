from fastapi import FastAPI
app = FastAPI(title="Infrastructure Progress Backend")

@app.get("/")
def home():
    return {
        "message": "backend is running successfully"
    }
