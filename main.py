import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import db, create_document, get_documents
from schemas import Dog, Exercise, Task, ProgressLog, LiveSession

from datetime import datetime, timezone
from bson import ObjectId

app = FastAPI(title="training-pets API", version="0.2.0")

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

# Utilities

def collection_name(model_cls):
    return model_cls.__name__.lower()


def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")


# Dogs
@app.post("/dogs")
def create_dog(dog: Dog):
    inserted_id = create_document(collection_name(Dog), dog)
    return {"id": inserted_id}


@app.get("/dogs")
def list_dogs(limit: int = Query(100, ge=1, le=500)):
    docs = get_documents(collection_name(Dog), {}, limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}


# Exercises
@app.post("/exercises")
def create_exercise(ex: Exercise):
    inserted_id = create_document(collection_name(Exercise), ex)
    return {"id": inserted_id}


@app.get("/exercises")
def list_exercises(limit: int = Query(200, ge=1, le=1000)):
    docs = get_documents(collection_name(Exercise), {}, limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}


# Tasks
@app.post("/tasks")
def create_task(task: Task):
    inserted_id = create_document(collection_name(Task), task)
    return {"id": inserted_id}


@app.get("/tasks")
def list_tasks(dog_id: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    filt: Dict[str, Any] = {}
    if dog_id:
        filt["dog_id"] = dog_id
    if status:
        filt["status"] = status
    docs = get_documents(collection_name(Task), filt, limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    steps: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    language: Optional[str] = None


@app.patch("/tasks/{task_id}")
def update_task(task_id: str = Path(...), payload: TaskUpdate = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    oid = to_object_id(task_id)
    update_doc = {k: v for k, v in (payload.model_dump() if payload else {}).items() if v is not None}
    update_doc["updated_at"] = datetime.now(timezone.utc)
    res = db[collection_name(Task)].update_one({"_id": oid}, {"$set": update_doc})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"updated": True}


@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: str = Path(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    oid = to_object_id(task_id)
    res = db[collection_name(Task)].update_one({"_id": oid}, {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"completed": True}


# Progress
@app.post("/progress")
def log_progress(progress: ProgressLog):
    inserted_id = create_document(collection_name(ProgressLog), progress)
    return {"id": inserted_id}


@app.get("/progress")
def list_progress(dog_id: Optional[str] = None, task_id: Optional[str] = None, limit: int = Query(200, ge=1, le=1000)):
    filt: Dict[str, Any] = {}
    if dog_id:
        filt["dog_id"] = dog_id
    if task_id:
        filt["task_id"] = task_id
    docs = get_documents(collection_name(ProgressLog), filt, limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}


# Analytics summary (simple aggregate)
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
            await ws.send_json({"type": "echo", "text": data})
    except WebSocketDisconnect:
        pass


# Root & diagnostics
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
