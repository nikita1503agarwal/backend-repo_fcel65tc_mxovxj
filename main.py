import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import db, create_document, get_documents
from schemas import Dog, Exercise, Task, ProgressLog, LiveSession

app = FastAPI(title="training-pets API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Basic helpers

def collection_name(model_cls):
    return model_cls.__name__.lower()

# Tasks
@app.post("/tasks")
def create_task(task: Task):
    inserted_id = create_document(collection_name(Task), task)
    return {"id": inserted_id}

@app.get("/tasks")
def list_tasks(dog_id: Optional[str] = None, limit: int = 50):
    filt: Dict[str, Any] = {}
    if dog_id:
        filt["dog_id"] = dog_id
    docs = get_documents(collection_name(Task), filt, limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}

# Progress
@app.post("/progress")
def log_progress(progress: ProgressLog):
    inserted_id = create_document(collection_name(ProgressLog), progress)
    return {"id": inserted_id}

# Analytics summary (very simple aggregate stub)
@app.get("/analytics/summary")
def analytics_summary(dog_id: Optional[str] = None):
    tasks = get_documents(collection_name(Task), {"dog_id": dog_id} if dog_id else {})
    logs = get_documents(collection_name(ProgressLog), {"dog_id": dog_id} if dog_id else {})

    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    success_rate = None
    if logs:
        successes = sum(1 for l in logs if l.get("success"))
        success_rate = successes / len(logs)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed,
        "success_rate": success_rate,
    }

# WebSocket stub for live coaching
@app.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        await ws.send_json({"type": "welcome", "message": "Connected to training-pets live coach"})
        while True:
            data = await ws.receive_text()
            # Echo with stub processing
            await ws.send_json({"type": "echo", "text": data})
    except WebSocketDisconnect:
        pass

# Keep previous root routes for compatibility
@app.get("/")
def read_root():
    return {"message": "training-pets backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected & Working",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Connected" if db is not None else "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["collections"] = db.list_collection_names()[:10]
    except Exception as e:
        response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
