"""
Training-Pets Database Schemas

Each Pydantic model corresponds to a MongoDB collection whose name is the lowercased class name.
Dog -> "dog"
Exercise -> "exercise"
Task -> "task"
ProgressLog -> "progresslog"
LiveSession -> "livesession"
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Dog(BaseModel):
    name: str = Field(..., description="Dog name")
    breed: Optional[str] = Field(None, description="Breed")
    age_months: Optional[int] = Field(None, ge=0, description="Age in months")
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight in kg")
    owner_name: Optional[str] = Field(None, description="Owner name")
    tags: List[str] = Field(default_factory=list, description="Tags e.g., puppy, reactive, agility")

class Exercise(BaseModel):
    title: str = Field(..., description="Exercise title")
    description: Optional[str] = Field(None, description="Short description")
    difficulty: Optional[str] = Field("beginner", description="beginner | intermediate | advanced")
    duration_min: Optional[int] = Field(5, ge=1, description="Estimated duration in minutes")
    cues: List[str] = Field(default_factory=list, description="Cues used in this exercise")
    goals: List[str] = Field(default_factory=list, description="Learning goals")

class Task(BaseModel):
    dog_id: Optional[str] = Field(None, description="Reference to dog _id as string")
    exercise_id: Optional[str] = Field(None, description="Reference to exercise _id as string")
    title: str = Field(..., description="Task title")
    steps: List[str] = Field(default_factory=list, description="Step-by-step instructions")
    scheduled_for: Optional[datetime] = Field(None, description="Planned session time")
    status: str = Field("pending", description="pending | in_progress | completed")
    language: str = Field("en", description="Language code for UI copy: en/he")

class ProgressLog(BaseModel):
    task_id: str = Field(..., description="Task id")
    dog_id: Optional[str] = Field(None, description="Dog id")
    success: bool = Field(..., description="Whether the step/session succeeded")
    notes: Optional[str] = Field(None, description="Trainer notes")
    score: Optional[float] = Field(None, ge=0, le=1, description="Normalized score 0..1")
    step_index: Optional[int] = Field(None, ge=0, description="Which step was attempted")

class LiveSession(BaseModel):
    dog_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None)
    status: str = Field("idle", description="idle | active | ended")
    peer_id: Optional[str] = Field(None, description="Client identifier for WS room")
