from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum
import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Security configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="TaskFlow Pro API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Enums
class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

# Authentication Models
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    role: UserRole = UserRole.USER

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDB(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = {}

class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_active: bool
    avatar_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

# Task/Project Models (Updated with user ownership)
class TodoItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    completed: bool = False
    completed_at: Optional[datetime] = None

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    todos: List[TodoItem] = []
    estimated_duration: Optional[int] = None  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    due_date: Optional[datetime] = None
    owner_id: str  # User who owns this task
    assigned_users: List[str] = []  # User IDs assigned to this task
    collaborators: List[str] = []  # User IDs collaborating on this task
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    time_logs: List[Dict[str, Any]] = []  # Track time spent

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner_id: str  # User who owns this project
    collaborators: List[str] = []  # User IDs with access to this project
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    task_count: int = 0
    completed_task_count: int = 0

class PerformanceMetrics(BaseModel):
    user_id: str
    date: datetime
    tasks_completed: int = 0
    tasks_created: int = 0
    total_time_spent: int = 0  # in minutes
    productivity_score: float = 0.0
    accuracy_score: float = 0.0  # estimated vs actual time accuracy

# Create/Update Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    assigned_users: List[str] = []
    collaborators: List[str] = []
    tags: List[str] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    assigned_users: Optional[List[str]] = None
    collaborators: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    collaborators: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# Authentication Utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": token_data.user_id})
    if user is None:
        raise credentials_exception
    return UserInDB(**user)

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    todos: List[TodoItem] = []
    estimated_duration: Optional[int] = None  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    due_date: Optional[datetime] = None
    owners: List[str] = []  # user IDs
    collaborators: List[str] = []  # user IDs
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    time_logs: List[Dict[str, Any]] = []  # Track time spent

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner_id: str
    collaborators: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    task_count: int = 0
    completed_task_count: int = 0

class PerformanceMetrics(BaseModel):
    user_id: str
    date: datetime
    tasks_completed: int = 0
    tasks_created: int = 0
    total_time_spent: int = 0  # in minutes
    productivity_score: float = 0.0
    accuracy_score: float = 0.0  # estimated vs actual time accuracy

# Create Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    owners: List[str] = []
    collaborators: List[str] = []
    tags: List[str] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    owners: Optional[List[str]] = None
    collaborators: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: str
    collaborators: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# Helper functions
async def calculate_productivity_metrics(user_id: str, date: datetime = None):
    """Calculate productivity metrics for a user"""
    if date is None:
        date = datetime.utcnow().date()
    
    start_date = datetime.combine(date, datetime.min.time())
    end_date = start_date + timedelta(days=1)
    
    # Get tasks for the day
    tasks = await db.tasks.find({
        "$or": [
            {"owners": user_id},
            {"collaborators": user_id}
        ],
        "updated_at": {"$gte": start_date, "$lt": end_date}
    }).to_list(1000)
    
    completed_tasks = [t for t in tasks if t.get("status") == "completed"]
    created_tasks = [t for t in tasks if t.get("created_at", datetime.min) >= start_date]
    
    # Calculate accuracy score (estimated vs actual duration)
    accuracy_scores = []
    total_time = 0
    
    for task in completed_tasks:
        if task.get("actual_duration") and task.get("estimated_duration"):
            estimated = task["estimated_duration"]
            actual = task["actual_duration"]
            accuracy = 1 - abs(estimated - actual) / max(estimated, actual)
            accuracy_scores.append(accuracy)
            total_time += actual
    
    accuracy_score = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
    productivity_score = len(completed_tasks) * 0.6 + accuracy_score * 0.4
    
    return {
        "tasks_completed": len(completed_tasks),
        "tasks_created": len(created_tasks),
        "total_time_spent": total_time,
        "productivity_score": round(productivity_score, 2),
        "accuracy_score": round(accuracy_score, 2)
    }

async def get_project_analytics(project_id: str):
    """Get analytics for a specific project"""
    tasks = await db.tasks.find({"project_id": project_id}).to_list(1000)
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
    in_progress_tasks = len([t for t in tasks if t.get("status") == "in_progress"])
    
    # Calculate total estimated vs actual time
    total_estimated = sum(t.get("estimated_duration", 0) for t in tasks)
    total_actual = sum(t.get("actual_duration", 0) for t in tasks if t.get("actual_duration"))
    
    progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "todo_tasks": total_tasks - completed_tasks - in_progress_tasks,
        "progress_percentage": round(progress_percentage, 2),
        "total_estimated_time": total_estimated,
        "total_actual_time": total_actual,
        "time_accuracy": round((1 - abs(total_estimated - total_actual) / max(total_estimated, total_actual, 1)) * 100, 2)
    }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Task Management API v1.0.0"}

# Task endpoints
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate):
    task_dict = task_data.dict()
    
    # Get project name if project_id is provided
    if task_dict.get("project_id"):
        project = await db.projects.find_one({"id": task_dict["project_id"]})
        if project:
            task_dict["project_name"] = project["name"]
            # Update project task count
            await db.projects.update_one(
                {"id": task_dict["project_id"]},
                {"$inc": {"task_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
    
    task = Task(**task_dict)
    await db.tasks.insert_one(task.dict())
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    project_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    owner_id: Optional[str] = None
):
    filter_dict = {}
    if project_id:
        filter_dict["project_id"] = project_id
    if status:
        filter_dict["status"] = status
    if priority:
        filter_dict["priority"] = priority
    if owner_id:
        filter_dict["$or"] = [{"owners": owner_id}, {"collaborators": owner_id}]
    
    tasks = await db.tasks.find(filter_dict).sort("created_at", -1).to_list(1000)
    return [Task(**task) for task in tasks]

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**task)

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_dict = {k: v for k, v in task_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    # Handle status change to completed
    if update_dict.get("status") == "completed" and task.get("status") != "completed":
        update_dict["completed_at"] = datetime.utcnow()
        # Update project completed task count
        if task.get("project_id"):
            await db.projects.update_one(
                {"id": task["project_id"]},
                {"$inc": {"completed_task_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update project task count
    if task.get("project_id"):
        await db.projects.update_one(
            {"id": task["project_id"]},
            {"$inc": {"task_count": -1}, "$set": {"updated_at": datetime.utcnow()}}
        )
    
    await db.tasks.delete_one({"id": task_id})
    return {"message": "Task deleted successfully"}

# Project endpoints
@api_router.post("/projects", response_model=Project)
async def create_project(project_data: ProjectCreate):
    project = Project(**project_data.dict())
    await db.projects.insert_one(project.dict())
    return project

@api_router.get("/projects", response_model=List[Project])
async def get_projects(owner_id: Optional[str] = None):
    filter_dict = {}
    if owner_id:
        filter_dict["$or"] = [{"owner_id": owner_id}, {"collaborators": owner_id}]
    
    projects = await db.projects.find(filter_dict).sort("created_at", -1).to_list(1000)
    return [Project(**project) for project in projects]

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return Project(**project)

@api_router.get("/projects/{project_id}/analytics")
async def get_project_analytics_endpoint(project_id: str):
    analytics = await get_project_analytics(project_id)
    return analytics

# Analytics endpoints
@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(user_id: Optional[str] = None):
    """Get comprehensive dashboard analytics"""
    
    # Get overall task statistics
    total_tasks = await db.tasks.count_documents({})
    completed_tasks = await db.tasks.count_documents({"status": "completed"})
    in_progress_tasks = await db.tasks.count_documents({"status": "in_progress"})
    overdue_tasks = await db.tasks.count_documents({
        "due_date": {"$lt": datetime.utcnow()},
        "status": {"$ne": "completed"}
    })
    
    # Get project statistics
    total_projects = await db.projects.count_documents({})
    active_projects = await db.projects.count_documents({"status": "active"})
    
    # Get recent productivity metrics
    today = datetime.utcnow().date()
    recent_metrics = []
    
    for days_back in range(7):
        date = today - timedelta(days=days_back)
        if user_id:
            metrics = await calculate_productivity_metrics(user_id, date)
        else:
            # Get overall metrics for all users
            metrics = {
                "tasks_completed": await db.tasks.count_documents({
                    "status": "completed",
                    "completed_at": {
                        "$gte": datetime.combine(date, datetime.min.time()),
                        "$lt": datetime.combine(date, datetime.min.time()) + timedelta(days=1)
                    }
                }),
                "tasks_created": await db.tasks.count_documents({
                    "created_at": {
                        "$gte": datetime.combine(date, datetime.min.time()),
                        "$lt": datetime.combine(date, datetime.min.time()) + timedelta(days=1)
                    }
                }),
                "total_time_spent": 0,
                "productivity_score": 0,
                "accuracy_score": 0
            }
        
        recent_metrics.append({
            "date": date.isoformat(),
            **metrics
        })
    
    return {
        "overview": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "overdue_tasks": overdue_tasks,
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2),
            "total_projects": total_projects,
            "active_projects": active_projects
        },
        "productivity_trends": recent_metrics,
        "generated_at": datetime.utcnow().isoformat()
    }

@api_router.get("/analytics/performance/{user_id}")
async def get_user_performance(user_id: str, days: int = 30):
    """Get user performance analytics for specified days"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    performance_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        metrics = await calculate_productivity_metrics(user_id, date)
        performance_data.append({
            "date": date.isoformat(),
            **metrics
        })
    
    return {
        "user_id": user_id,
        "period_days": days,
        "performance_data": performance_data
    }

@api_router.get("/analytics/time-tracking")
async def get_time_tracking_analytics(user_id: Optional[str] = None, project_id: Optional[str] = None):
    """Get time tracking analytics"""
    filter_dict = {"actual_duration": {"$exists": True, "$ne": None}}
    
    if user_id:
        filter_dict["$or"] = [{"owners": user_id}, {"collaborators": user_id}]
    if project_id:
        filter_dict["project_id"] = project_id
    
    tasks = await db.tasks.find(filter_dict).to_list(1000)
    
    # Calculate time distribution by project
    time_by_project = {}
    time_by_priority = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
    total_estimated = 0
    total_actual = 0
    
    for task in tasks:
        actual_duration = task.get("actual_duration", 0)
        estimated_duration = task.get("estimated_duration", 0)
        project_name = task.get("project_name", "No Project")
        priority = task.get("priority", "medium")
        
        # Time by project
        time_by_project[project_name] = time_by_project.get(project_name, 0) + actual_duration
        
        # Time by priority
        time_by_priority[priority] += actual_duration
        
        # Totals
        total_actual += actual_duration
        total_estimated += estimated_duration
    
    accuracy_percentage = (1 - abs(total_estimated - total_actual) / max(total_estimated, total_actual, 1)) * 100
    
    return {
        "time_by_project": time_by_project,
        "time_by_priority": time_by_priority,
        "total_estimated_hours": round(total_estimated / 60, 2),
        "total_actual_hours": round(total_actual / 60, 2),
        "accuracy_percentage": round(accuracy_percentage, 2),
        "tasks_analyzed": len(tasks)
    }

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()