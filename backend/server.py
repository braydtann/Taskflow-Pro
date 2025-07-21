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
    
    # Timer functionality fields
    timer_start_time: Optional[datetime] = None  # When current timer session started
    timer_elapsed_seconds: int = 0  # Total accumulated time in seconds
    is_timer_running: bool = False  # Whether timer is currently running
    timer_sessions: List[Dict[str, Any]] = []  # Detailed timer session history

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

# Team Management Models
class Team(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_by: str  # Admin user ID who created the team
    team_lead_id: Optional[str] = None  # User ID of team lead
    members: List[str] = []  # List of user IDs in the team
    projects: List[str] = []  # List of project IDs assigned to this team
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    team_settings: Dict[str, Any] = {}

class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    team_lead_id: Optional[str] = None
    members: List[str] = []

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_lead_id: Optional[str] = None
    members: Optional[List[str]] = None
    is_active: Optional[bool] = None

# Admin User Management Models
class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    role: UserRole = UserRole.USER
    password: str
    team_ids: List[str] = []

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    team_ids: Optional[List[str]] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_active: bool
    avatar_url: Optional[str] = None
    team_ids: List[str] = []  # Teams this user belongs to
    last_login: Optional[datetime] = None

# Update existing UserInDB model to include team information
class UserInDB(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = {}
    team_ids: List[str] = []  # Teams this user belongs to
    last_login: Optional[datetime] = None
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

# Helper functions (updated for user filtering)
async def calculate_productivity_metrics(user_id: str, date: datetime = None):
    """Calculate productivity metrics for a user"""
    if date is None:
        date = datetime.utcnow().date()
    
    start_date = datetime.combine(date, datetime.min.time())
    end_date = start_date + timedelta(days=1)
    
    # Get user's tasks for the day
    tasks = await db.tasks.find({
        "$or": [
            {"owner_id": user_id},
            {"assigned_users": user_id},
            {"collaborators": user_id}
        ],
        "updated_at": {"$gte": start_date, "$lt": end_date}
    }).to_list(1000)
    
    completed_tasks = [t for t in tasks if t.get("status") == "completed"]
    created_tasks = [t for t in tasks if t.get("created_at", datetime.min) >= start_date and t.get("owner_id") == user_id]
    
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

async def get_project_analytics(project_id: str, user_id: str):
    """Get analytics for a specific project (user must have access)"""
    # Verify user has access to this project
    project = await db.projects.find_one({
        "id": project_id,
        "$or": [
            {"owner_id": user_id},
            {"collaborators": user_id}
        ]
    })
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
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

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user_dict = user_data.dict()
    del user_dict["password"]
    
    user = UserInDB(**user_dict, hashed_password=hashed_password)
    await db.users.insert_one(user.dict())
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"user_id": user.id, "email": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(**user.dict())
    )

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user["id"], "email": user["email"]}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"user_id": user["id"], "email": user["email"]})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(**user)
    )

@api_router.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise credentials_exception
    
    # Create new tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user["id"], "email": user["email"]}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"user_id": user["id"], "email": user["email"]})
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse(**user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_active_user)):
    return UserResponse(**current_user.dict())

# Task endpoints (updated with user filtering)
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: UserInDB = Depends(get_current_active_user)):
    task_dict = task_data.dict()
    task_dict["owner_id"] = current_user.id
    
    # Get project name if project_id is provided and user has access
    if task_dict.get("project_id"):
        project = await db.projects.find_one({
            "id": task_dict["project_id"],
            "$or": [
                {"owner_id": current_user.id},
                {"collaborators": current_user.id}
            ]
        })
        if project:
            task_dict["project_name"] = project["name"]
            # Update project task count
            await db.projects.update_one(
                {"id": task_dict["project_id"]},
                {"$inc": {"task_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
        else:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    task = Task(**task_dict)
    await db.tasks.insert_one(task.dict())
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    current_user: UserInDB = Depends(get_current_active_user),
    project_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None
):
    # Base filter - user can only see tasks they own, are assigned to, or collaborate on
    filter_dict = {
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    }
    
    if project_id:
        # Verify user has access to this project
        project = await db.projects.find_one({
            "id": project_id,
            "$or": [
                {"owner_id": current_user.id},
                {"collaborators": current_user.id}
            ]
        })
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        filter_dict["project_id"] = project_id
    
    if status:
        filter_dict["status"] = status
    if priority:
        filter_dict["priority"] = priority
    
    tasks = await db.tasks.find(filter_dict).sort("created_at", -1).to_list(1000)
    return [Task(**task) for task in tasks]

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    return Task(**task)

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: UserInDB = Depends(get_current_active_user)):
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
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
async def delete_task(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    task = await db.tasks.find_one({
        "id": task_id,
        "owner_id": current_user.id  # Only owner can delete
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or you don't have permission to delete it")
    
    # Update project task count
    if task.get("project_id"):
        await db.projects.update_one(
            {"id": task["project_id"]},
            {"$inc": {"task_count": -1}, "$set": {"updated_at": datetime.utcnow()}}
        )
    
    await db.tasks.delete_one({"id": task_id})
    return {"message": "Task deleted successfully"}

# Project endpoints (updated with user filtering)
@api_router.post("/projects", response_model=Project)
async def create_project(project_data: ProjectCreate, current_user: UserInDB = Depends(get_current_active_user)):
    project_dict = project_data.dict()
    project_dict["owner_id"] = current_user.id
    
    project = Project(**project_dict)
    await db.projects.insert_one(project.dict())
    return project

@api_router.get("/projects", response_model=List[Project])
async def get_projects(current_user: UserInDB = Depends(get_current_active_user)):
    filter_dict = {
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    }
    
    projects = await db.projects.find(filter_dict).sort("created_at", -1).to_list(1000)
    return [Project(**project) for project in projects]

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    project = await db.projects.find_one({
        "id": project_id,
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return Project(**project)

@api_router.get("/projects/{project_id}/analytics")
async def get_project_analytics_endpoint(project_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    analytics = await get_project_analytics(project_id, current_user.id)
    return analytics

# Analytics endpoints (user-specific)
@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(current_user: UserInDB = Depends(get_current_active_user)):
    """Get comprehensive dashboard analytics for current user"""
    
    # Get user's task statistics
    user_filter = {
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    }
    
    total_tasks = await db.tasks.count_documents(user_filter)
    completed_tasks = await db.tasks.count_documents({**user_filter, "status": "completed"})
    in_progress_tasks = await db.tasks.count_documents({**user_filter, "status": "in_progress"})
    overdue_tasks = await db.tasks.count_documents({
        **user_filter,
        "due_date": {"$lt": datetime.utcnow()},
        "status": {"$ne": "completed"}
    })
    
    # Get user's project statistics
    project_filter = {
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    }
    total_projects = await db.projects.count_documents(project_filter)
    active_projects = await db.projects.count_documents({**project_filter, "status": "active"})
    
    # Get recent productivity metrics
    today = datetime.utcnow().date()
    recent_metrics = []
    
    for days_back in range(7):
        date = today - timedelta(days=days_back)
        metrics = await calculate_productivity_metrics(current_user.id, date)
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
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@api_router.get("/analytics/performance")
async def get_user_performance(days: int = 30, current_user: UserInDB = Depends(get_current_active_user)):
    """Get user performance analytics for specified days"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    performance_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        metrics = await calculate_productivity_metrics(current_user.id, date)
        performance_data.append({
            "date": date.isoformat(),
            **metrics
        })
    
    return {
        "user_id": current_user.id,
        "period_days": days,
        "performance_data": performance_data
    }

@api_router.get("/analytics/time-tracking")
async def get_time_tracking_analytics(project_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_active_user)):
    """Get time tracking analytics for current user"""
    filter_dict = {
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ],
        "actual_duration": {"$exists": True, "$ne": None}
    }
    
    if project_id:
        # Verify user has access to this project
        project = await db.projects.find_one({
            "id": project_id,
            "$or": [
                {"owner_id": current_user.id},
                {"collaborators": current_user.id}
            ]
        })
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
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

# Timer endpoints
@api_router.post("/tasks/{task_id}/timer/start")
async def start_task_timer(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Start timer for a task and set status to in_progress"""
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Check if timer is already running
    if task.get("is_timer_running", False):
        raise HTTPException(status_code=400, detail="Timer is already running for this task")
    
    # Start timer
    now = datetime.utcnow()
    update_dict = {
        "timer_start_time": now,
        "is_timer_running": True,
        "status": "in_progress",
        "updated_at": now
    }
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    
    return {
        "message": "Timer started successfully",
        "task": Task(**updated_task),
        "timer_started_at": now.isoformat()
    }

@api_router.post("/tasks/{task_id}/timer/pause")
async def pause_task_timer(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Pause timer for a task (keeps status as in_progress)"""
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Check if timer is running
    if not task.get("is_timer_running", False):
        raise HTTPException(status_code=400, detail="Timer is not currently running for this task")
    
    # Calculate elapsed time for this session
    timer_start = task.get("timer_start_time")
    if not timer_start:
        raise HTTPException(status_code=400, detail="Timer start time not found")
    
    now = datetime.utcnow()
    if isinstance(timer_start, str):
        timer_start = datetime.fromisoformat(timer_start.replace('Z', '+00:00'))
    
    session_seconds = int((now - timer_start).total_seconds())
    current_elapsed = task.get("timer_elapsed_seconds", 0)
    new_elapsed = current_elapsed + session_seconds
    
    # Add this session to timer_sessions
    timer_sessions = task.get("timer_sessions", [])
    timer_sessions.append({
        "start_time": timer_start.isoformat(),
        "end_time": now.isoformat(),
        "duration_seconds": session_seconds,
        "session_type": "work"
    })
    
    # Update task
    update_dict = {
        "timer_start_time": None,
        "is_timer_running": False,
        "timer_elapsed_seconds": new_elapsed,
        "timer_sessions": timer_sessions,
        "updated_at": now
    }
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    
    return {
        "message": "Timer paused successfully",
        "task": Task(**updated_task),
        "session_duration_seconds": session_seconds,
        "total_elapsed_seconds": new_elapsed
    }

@api_router.post("/tasks/{task_id}/timer/resume")
async def resume_task_timer(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Resume paused timer for a task"""
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Check if timer is already running
    if task.get("is_timer_running", False):
        raise HTTPException(status_code=400, detail="Timer is already running for this task")
    
    # Resume timer
    now = datetime.utcnow()
    update_dict = {
        "timer_start_time": now,
        "is_timer_running": True,
        "status": "in_progress",  # Ensure status is in_progress
        "updated_at": now
    }
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    
    return {
        "message": "Timer resumed successfully",
        "task": Task(**updated_task),
        "timer_resumed_at": now.isoformat()
    }

@api_router.post("/tasks/{task_id}/timer/stop")
async def stop_task_timer(task_id: str, complete_task: bool = False, current_user: UserInDB = Depends(get_current_active_user)):
    """Stop timer for a task and optionally complete the task"""
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Check if timer is running
    if not task.get("is_timer_running", False):
        raise HTTPException(status_code=400, detail="Timer is not currently running for this task")
    
    # Calculate elapsed time for this session
    timer_start = task.get("timer_start_time")
    if not timer_start:
        raise HTTPException(status_code=400, detail="Timer start time not found")
    
    now = datetime.utcnow()
    if isinstance(timer_start, str):
        timer_start = datetime.fromisoformat(timer_start.replace('Z', '+00:00'))
    
    session_seconds = int((now - timer_start).total_seconds())
    current_elapsed = task.get("timer_elapsed_seconds", 0)
    new_elapsed = current_elapsed + session_seconds
    
    # Add this session to timer_sessions
    timer_sessions = task.get("timer_sessions", [])
    timer_sessions.append({
        "start_time": timer_start.isoformat(),
        "end_time": now.isoformat(),
        "duration_seconds": session_seconds,
        "session_type": "work"
    })
    
    # Update task
    update_dict = {
        "timer_start_time": None,
        "is_timer_running": False,
        "timer_elapsed_seconds": new_elapsed,
        "timer_sessions": timer_sessions,
        "actual_duration": round(new_elapsed / 60),  # Convert to minutes
        "updated_at": now
    }
    
    # Complete task if requested
    if complete_task:
        update_dict["status"] = "completed"
        update_dict["completed_at"] = now
        
        # Update project completed task count
        if task.get("project_id"):
            await db.projects.update_one(
                {"id": task["project_id"]},
                {"$inc": {"completed_task_count": 1}, "$set": {"updated_at": now}}
            )
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    
    return {
        "message": f"Timer stopped successfully{' and task completed' if complete_task else ''}",
        "task": Task(**updated_task),
        "session_duration_seconds": session_seconds,
        "total_elapsed_seconds": new_elapsed,
        "total_elapsed_minutes": round(new_elapsed / 60, 2)
    }

@api_router.get("/tasks/{task_id}/timer/status")
async def get_task_timer_status(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Get current timer status for a task"""
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    is_running = task.get("is_timer_running", False)
    elapsed_seconds = task.get("timer_elapsed_seconds", 0)
    
    # Calculate current session time if timer is running
    current_session_seconds = 0
    if is_running and task.get("timer_start_time"):
        timer_start = task["timer_start_time"]
        if isinstance(timer_start, str):
            timer_start = datetime.fromisoformat(timer_start.replace('Z', '+00:00'))
        current_session_seconds = int((datetime.utcnow() - timer_start).total_seconds())
    
    total_current_seconds = elapsed_seconds + current_session_seconds
    
    return {
        "task_id": task_id,
        "is_timer_running": is_running,
        "timer_start_time": task.get("timer_start_time"),
        "elapsed_seconds": elapsed_seconds,
        "current_session_seconds": current_session_seconds,
        "total_current_seconds": total_current_seconds,
        "total_current_minutes": round(total_current_seconds / 60, 2),
        "timer_sessions_count": len(task.get("timer_sessions", []))
    }

# User Management
@api_router.get("/users/search")
async def search_users(query: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Search users by username or email for task assignment"""
    users = await db.users.find({
        "$or": [
            {"username": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}},
            {"full_name": {"$regex": query, "$options": "i"}}
        ],
        "is_active": True
    }).limit(10).to_list(10)
    
    return [{"id": user["id"], "username": user["username"], "full_name": user["full_name"], "email": user["email"]} for user in users]

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