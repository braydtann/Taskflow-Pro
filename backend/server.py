from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timedelta
from enum import Enum
import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext
import json

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

# WebSocket Connection Manager for Real-time Updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # user_id -> [websockets]
        self.user_teams: Dict[str, List[str]] = {}  # user_id -> [team_ids]
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Load user's teams for targeted broadcasts
        user = await db.users.find_one({"id": user_id})
        if user:
            self.user_teams[user_id] = user.get("team_ids", [])
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_teams:
                    del self.user_teams[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    pass
    
    async def send_team_message(self, message: dict, team_ids: List[str], exclude_user: str = None):
        """Send message to all users in specified teams"""
        for user_id, user_teams in self.user_teams.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            # Check if user is in any of the target teams
            if any(team_id in user_teams for team_id in team_ids):
                await self.send_personal_message(message, user_id)
    
    async def send_project_message(self, message: dict, project_id: str, exclude_user: str = None):
        """Send message to all collaborators of a project"""
        project = await db.projects.find_one({"id": project_id})
        if project:
            collaborators = project.get("collaborators", []) + [project.get("owner_id")]
            for user_id in collaborators:
                if exclude_user and user_id == exclude_user:
                    continue
                await self.send_personal_message(message, user_id)
    
    async def broadcast_task_update(self, task: dict, action: str, user_id: str):
        """Broadcast task updates to relevant users"""
        message = {
            "type": "task_update",
            "action": action,  # "created", "updated", "deleted"
            "task": task,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to task collaborators and assigned users
        recipients = set(task.get("collaborators", []) + task.get("assigned_users", []))
        if task.get("owner_id"):
            recipients.add(task["owner_id"])
        
        for recipient_id in recipients:
            if recipient_id != user_id:  # Don't send back to the creator
                await self.send_personal_message(message, recipient_id)
        
        # Send to project collaborators if task belongs to a project
        if task.get("project_id"):
            await self.send_project_message(message, task["project_id"], exclude_user=user_id)

manager = ConnectionManager()

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
    PROJECT_MANAGER = "project_manager"
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

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: "UserResponse"  # Forward reference

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

# Subtask Comment Model
class SubtaskComment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    username: str  # For easy display
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Enhanced TodoItem (Subtask) Model
class TodoItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    description: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    assigned_users: List[str] = []  # User IDs assigned to this subtask
    assigned_usernames: List[str] = []  # Usernames for easy display
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    comments: List[SubtaskComment] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # User ID who created this subtask

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
    assigned_teams: List[str] = []  # Team IDs assigned to this task
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
    auto_calculated_status: ProjectStatus = ProjectStatus.ACTIVE  # Auto-calculated based on tasks
    status_override: Optional[ProjectStatus] = None  # Manual override by project manager
    owner_id: str  # User who owns this project
    collaborators: List[str] = []  # User IDs with access to this project
    project_managers: List[str] = []  # User IDs who can manage this project
    assigned_teams: List[str] = []  # Team IDs assigned to this project
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    task_count: int = 0
    completed_task_count: int = 0
    progress_percentage: float = 0.0  # Calculated progress based on task completion

class PerformanceMetrics(BaseModel):
    user_id: str
    date: datetime
    tasks_completed: int = 0
    tasks_created: int = 0
    total_time_spent: int = 0  # in minutes
    productivity_score: float = 0.0
    accuracy_score: float = 0.0  # estimated vs actual time accuracy

# Activity Log Model
class ActivityLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # User who performed the action
    action: str  # Action performed (created, updated, deleted, etc.)
    entity_type: str  # Type of entity (task, project, user, etc.)
    entity_id: str  # ID of the entity affected
    entity_name: str  # Name/title of the entity for display
    project_id: Optional[str] = None  # Project context if applicable
    details: Dict[str, Any] = {}  # Additional details about the action
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Notification Model
class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # User who should receive the notification
    title: str  # Notification title
    message: str  # Notification message
    type: str  # Type of notification (overdue, deadline, blocked, etc.)
    priority: str  # Priority level (low, medium, high)
    read: bool = False  # Whether the notification has been read
    entity_type: Optional[str] = None  # Related entity type
    entity_id: Optional[str] = None  # Related entity ID
    project_id: Optional[str] = None  # Project context if applicable
    action_url: Optional[str] = None  # URL to navigate to when clicked
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

# Create/Update Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[str] = None
    estimated_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    assigned_users: List[str] = []
    assigned_teams: List[str] = []
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
    assigned_teams: Optional[List[str]] = None
    collaborators: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    collaborators: List[str] = []
    project_managers: List[str] = []
    assigned_teams: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    status_override: Optional[ProjectStatus] = None
    collaborators: Optional[List[str]] = None
    project_managers: Optional[List[str]] = None
    assigned_teams: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# Subtask Management Models
class SubtaskCreate(BaseModel):
    text: str
    description: Optional[str] = None
    assigned_users: List[str] = []
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None

class SubtaskUpdate(BaseModel):
    text: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    assigned_users: Optional[List[str]] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None

class SubtaskCommentCreate(BaseModel):
    comment: str

class SubtaskCommentUpdate(BaseModel):
    comment: str

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

async def get_current_admin_user(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_project_manager(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role not in [UserRole.PROJECT_MANAGER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project manager access required"
        )
    return current_user

async def check_project_manager_access(project_id: str, current_user: UserInDB):
    """Check if current user can manage the given project"""
    # Admin can manage all projects
    if current_user.role == UserRole.ADMIN:
        return True
    
    # Project managers can manage projects they're assigned to
    if current_user.role == UserRole.PROJECT_MANAGER:
        project = await db.projects.find_one({"id": project_id})
        if project and (
            current_user.id in project.get("project_managers", []) or
            current_user.id == project.get("owner_id")
        ):
            return True
    
    return False

async def log_activity(user_id: str, action: str, entity_type: str, entity_id: str, entity_name: str, project_id: str = None, details: Dict[str, Any] = None):
    """Log user activity for audit trail"""
    activity = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        project_id=project_id,
        details=details or {}
    )
    await db.activity_logs.insert_one(activity.dict())

async def create_notification(user_id: str, title: str, message: str, notification_type: str, priority: str = "medium", entity_type: str = None, entity_id: str = None, project_id: str = None, action_url: str = None):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        priority=priority,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        action_url=action_url
    )
    await db.notifications.insert_one(notification.dict())

async def calculate_project_status(project_id: str):
    """Calculate auto project status based on tasks"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return ProjectStatus.ACTIVE
    
    # Get all tasks for this project
    tasks = await db.tasks.find({"project_id": project_id}).to_list(1000)
    
    if not tasks:
        return ProjectStatus.ACTIVE
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
    in_progress_tasks = len([t for t in tasks if t.get("status") == "in_progress"])
    blocked_tasks = len([t for t in tasks if t.get("status") == "blocked"])
    
    # Handle datetime parsing for overdue tasks
    overdue_tasks = 0
    for task in tasks:
        if task.get("due_date") and task.get("status") != "completed":
            try:
                due_date = task["due_date"]
                if isinstance(due_date, str):
                    # Parse string datetime
                    due_date_obj = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                else:
                    # Already a datetime object
                    due_date_obj = due_date
                
                if due_date_obj < datetime.utcnow():
                    overdue_tasks += 1
            except (ValueError, TypeError) as e:
                # Skip tasks with invalid datetime formats
                continue
    
    # Calculate progress percentage
    progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Determine status
    if progress == 100:
        return ProjectStatus.COMPLETED
    elif blocked_tasks > 0 or overdue_tasks > 0:
        return ProjectStatus.ON_HOLD  # At Risk
    elif in_progress_tasks > 0:
        return ProjectStatus.ACTIVE  # In Progress
    else:
        return ProjectStatus.ACTIVE  # Not Started

async def update_project_progress(project_id: str):
    """Update project progress and auto-calculated status"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    
    # Calculate new status and progress
    auto_status = await calculate_project_status(project_id)
    
    # Get tasks for progress calculation
    tasks = await db.tasks.find({"project_id": project_id}).to_list(1000)
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
    progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Update project
    update_data = {
        "auto_calculated_status": auto_status,
        "progress_percentage": progress,
        "task_count": total_tasks,
        "completed_task_count": completed_tasks,
        "updated_at": datetime.utcnow()
    }
    
    # Use override status if set, otherwise use auto-calculated
    if not project.get("status_override"):
        update_data["status"] = auto_status
    
    await db.projects.update_one({"id": project_id}, {"$set": update_data})

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

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Verify user authentication via WebSocket
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Token missing")
            return
        
        # Verify JWT token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_user_id = payload.get("user_id")
            if token_user_id != user_id:
                await websocket.close(code=1008, reason="Token mismatch")
                return
        except JWTError:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Connect user to WebSocket manager
        await manager.connect(websocket, user_id)
        
        try:
            # Send welcome message
            await manager.send_personal_message({
                "type": "connection_established",
                "message": "Real-time updates connected",
                "user_id": user_id
            }, user_id)
            
            # Keep connection alive and handle incoming messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                elif message.get("type") == "user_typing":
                    # Broadcast typing indicators to relevant users
                    task_id = message.get("task_id")
                    if task_id:
                        task = await db.tasks.find_one({"id": task_id})
                        if task:
                            await manager.broadcast_task_update({
                                **task,
                                "typing_user": user_id
                            }, "user_typing", user_id)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
        except Exception as e:
            logging.error(f"WebSocket error for user {user_id}: {str(e)}")
            manager.disconnect(websocket, user_id)
    
    except Exception as e:
        logging.error(f"WebSocket connection error: {str(e)}")
        await websocket.close(code=1011, reason="Internal error")

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
    
    # Log activity
    await log_activity(
        user_id=current_user.id,
        action="created",
        entity_type="task",
        entity_id=task.id,
        entity_name=task.title,
        project_id=task.project_id,
        details={"priority": task.priority, "status": task.status}
    )
    
    # Update project progress if task belongs to a project
    if task.project_id:
        await update_project_progress(task.project_id)
    
    # Broadcast real-time update to collaborators
    await manager.broadcast_task_update(task.dict(), "created", current_user.id)
    
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    current_user: UserInDB = Depends(get_current_active_user),
    project_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None
):
    # Get user's team IDs to find shared tasks
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    # Base filter - user can see tasks they:
    # 1. Own
    # 2. Are assigned to
    # 3. Collaborate on
    # 4. Are assigned to their teams
    # 5. Belong to projects they have access to (owner or collaborator)
    # 6. Belong to projects their teams have access to
    filter_dict = {
        "$or": [
            {"owner_id": current_user.id},
            {"assigned_users": current_user.id},
            {"collaborators": current_user.id}
        ]
    }
    
    # Add team-assigned tasks if user has teams
    if user_teams:
        filter_dict["$or"].append({"assigned_teams": {"$in": user_teams}})
    
    # Add project-based access if user has teams or project access
    project_access_conditions = []
    
    # Projects user owns or collaborates on
    user_projects = await db.projects.find({
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    }).to_list(1000)
    
    user_project_ids = [p["id"] for p in user_projects]
    
    if user_project_ids:
        project_access_conditions.append({"project_id": {"$in": user_project_ids}})
    
    # Add team-based project access if user has teams
    if user_teams:
        team_projects = await db.projects.find({
            "team_ids": {"$in": user_teams}
        }).to_list(1000)
        
        team_project_ids = [p["id"] for p in team_projects]
        if team_project_ids:
            project_access_conditions.append({"project_id": {"$in": team_project_ids}})
    
    # Add project access conditions to main filter
    if project_access_conditions:
        filter_dict["$or"].extend(project_access_conditions)
    
    # Apply additional filters
    if project_id:
        # Verify user has access to this specific project
        project = await db.projects.find_one({
            "id": project_id,
            "$or": [
                {"owner_id": current_user.id},
                {"collaborators": current_user.id},
                {"team_ids": {"$in": user_teams}} if user_teams else {}
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

@api_router.get("/tasks/search/{query}")
async def search_tasks(query: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Search tasks by title for dashboard quick search"""
    # Get user's team IDs to find team-assigned tasks
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    # Build base access filter
    filter_conditions = [
        {"owner_id": current_user.id},
        {"assigned_users": current_user.id},
        {"collaborators": current_user.id}
    ]
    
    # Add team-assigned tasks if user has teams
    if user_teams:
        filter_conditions.append({"assigned_teams": {"$in": user_teams}})
    
    # Add project-based access
    project_access_conditions = []
    
    # Projects user owns or collaborates on
    user_projects = await db.projects.find({
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    }).to_list(1000)
    
    user_project_ids = [p["id"] for p in user_projects]
    
    if user_project_ids:
        project_access_conditions.append({"project_id": {"$in": user_project_ids}})
    
    # Add team-based project access if user has teams
    if user_teams:
        team_projects = await db.projects.find({
            "team_ids": {"$in": user_teams}
        }).to_list(1000)
        
        team_project_ids = [p["id"] for p in team_projects]
        if team_project_ids:
            project_access_conditions.append({"project_id": {"$in": team_project_ids}})
    
    # Add project access conditions to main filter
    if project_access_conditions:
        filter_conditions.extend(project_access_conditions)
    
    # Build the search filter
    search_filter = {
        "$and": [
            {"$or": filter_conditions},
            {"title": {"$regex": query, "$options": "i"}}  # Case-insensitive search
        ]
    }
    
    # Limit results for quick search
    tasks = await db.tasks.find(search_filter).sort("created_at", -1).limit(10).to_list(10)
    
    # Return simplified task data for search results
    return [
        {
            "id": task["id"],
            "title": task["title"],
            "description": task.get("description", ""),
            "status": task["status"],
            "priority": task["priority"],
            "project_name": task.get("project_name", ""),
            "due_date": task.get("due_date"),
            "created_at": task["created_at"]
        }
        for task in tasks
    ]

@api_router.get("/teams/user")
async def get_user_teams(current_user: UserInDB = Depends(get_current_active_user)):
    """Get teams that the current user belongs to"""
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    if not user_teams:
        return []
    
    teams = await db.teams.find({
        "id": {"$in": user_teams},
        "is_active": True
    }).sort("name", 1).to_list(1000)
    
    # Return simplified team data for dropdown
    return [
        {
            "id": team["id"],
            "name": team["name"],
            "description": team.get("description", ""),
            "member_count": len(team.get("members", []))
        }
        for team in teams
    ]

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    # Get user's team IDs to find team-assigned tasks
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    # Build filter conditions
    filter_conditions = [
        {"owner_id": current_user.id},
        {"assigned_users": current_user.id},
        {"collaborators": current_user.id}
    ]
    
    # Add team-assigned tasks if user has teams
    if user_teams:
        filter_conditions.append({"assigned_teams": {"$in": user_teams}})
    
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": filter_conditions
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    return Task(**task)

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: UserInDB = Depends(get_current_active_user)):
    # Get user's team IDs to find team-assigned tasks
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    # Build filter conditions
    filter_conditions = [
        {"owner_id": current_user.id},
        {"assigned_users": current_user.id},
        {"collaborators": current_user.id}
    ]
    
    # Add team-assigned tasks if user has teams
    if user_teams:
        filter_conditions.append({"assigned_teams": {"$in": user_teams}})
    
    task = await db.tasks.find_one({
        "id": task_id,
        "$or": filter_conditions
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    update_dict = {k: v for k, v in task_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    # Track status changes for activity logging
    status_changed = False
    old_status = task.get("status")
    new_status = update_dict.get("status")
    
    # Handle status change to completed
    if update_dict.get("status") == "completed" and task.get("status") != "completed":
        update_dict["completed_at"] = datetime.utcnow()
        # Update project completed task count
        if task.get("project_id"):
            await db.projects.update_one(
                {"id": task["project_id"]},
                {"$inc": {"completed_task_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
        status_changed = True
    elif new_status and old_status != new_status:
        status_changed = True
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
    updated_task = await db.tasks.find_one({"id": task_id})
    
    # Log activity
    activity_details = {}
    if status_changed:
        activity_details["status_change"] = {"from": old_status, "to": new_status}
    
    await log_activity(
        user_id=current_user.id,
        action="updated",
        entity_type="task",
        entity_id=task_id,
        entity_name=task["title"],
        project_id=task.get("project_id"),
        details=activity_details
    )
    
    # Update project progress if task belongs to a project
    if task.get("project_id"):
        await update_project_progress(task["project_id"])
    
    # Create notifications for status changes
    if status_changed and new_status in ["blocked", "overdue"]:
        # Get project managers and team members
        if task.get("project_id"):
            project = await db.projects.find_one({"id": task["project_id"]})
            if project:
                notify_users = set(project.get("project_managers", []))
                notify_users.add(project.get("owner_id"))
                
                for user_id in notify_users:
                    if user_id and user_id != current_user.id:
                        await create_notification(
                            user_id=user_id,
                            title=f"Task Status Alert",
                            message=f"Task '{task['title']}' is now {new_status}",
                            notification_type="task_status_alert",
                            priority="high" if new_status == "blocked" else "medium",
                            entity_type="task",
                            entity_id=task_id,
                            project_id=task.get("project_id")
                        )
    
    # Broadcast real-time update to collaborators
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    task = await db.tasks.find_one({
        "id": task_id,
        "owner_id": current_user.id  # Only owner can delete
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or you don't have permission to delete it")
    
    # Broadcast deletion before actually deleting
    await manager.broadcast_task_update(task, "deleted", current_user.id)
    
    # Update project task count
    if task.get("project_id"):
        await db.projects.update_one(
            {"id": task["project_id"]},
            {"$inc": {"task_count": -1}, "$set": {"updated_at": datetime.utcnow()}}
        )
    
    await db.tasks.delete_one({"id": task_id})
    return {"message": "Task deleted successfully"}

# Subtask Management Endpoints
@api_router.post("/tasks/{task_id}/subtasks", response_model=TodoItem)
async def create_subtask(
    task_id: str, 
    subtask_data: SubtaskCreate, 
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Get usernames for assigned users
    assigned_usernames = []
    if subtask_data.assigned_users:
        assigned_users = await db.users.find(
            {"id": {"$in": subtask_data.assigned_users}}
        ).to_list(100)
        assigned_usernames = [user["username"] for user in assigned_users]
    
    # Create subtask
    subtask_dict = subtask_data.dict()
    subtask_dict["created_by"] = current_user.id
    subtask_dict["assigned_usernames"] = assigned_usernames
    
    subtask = TodoItem(**subtask_dict)
    
    # Add subtask to task's todos array
    await db.tasks.update_one(
        {"id": task_id},
        {
            "$push": {"todos": subtask.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Get updated task and broadcast change
    updated_task = await db.tasks.find_one({"id": task_id})
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return subtask

@api_router.put("/tasks/{task_id}/subtasks/{subtask_id}", response_model=TodoItem)
async def update_subtask(
    task_id: str,
    subtask_id: str,
    subtask_update: SubtaskUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Find the subtask
    subtask_index = -1
    current_subtask = None
    for i, todo in enumerate(task.get("todos", [])):
        if todo["id"] == subtask_id:
            subtask_index = i
            current_subtask = todo
            break
    
    if subtask_index == -1:
        raise HTTPException(status_code=404, detail="Subtask not found")
    
    # Prepare update data
    update_dict = {k: v for k, v in subtask_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    # Handle completion
    if update_dict.get("completed") and not current_subtask.get("completed"):
        update_dict["completed_at"] = datetime.utcnow()
    elif update_dict.get("completed") is False:
        update_dict["completed_at"] = None
    
    # Get usernames for assigned users if being updated
    if "assigned_users" in update_dict and update_dict["assigned_users"]:
        assigned_users = await db.users.find(
            {"id": {"$in": update_dict["assigned_users"]}}
        ).to_list(100)
        update_dict["assigned_usernames"] = [user["username"] for user in assigned_users]
    elif "assigned_users" in update_dict and not update_dict["assigned_users"]:
        update_dict["assigned_usernames"] = []
    
    # Update the subtask in the array
    update_operations = {}
    for key, value in update_dict.items():
        update_operations[f"todos.{subtask_index}.{key}"] = value
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {**update_operations, "updated_at": datetime.utcnow()}}
    )
    
    # Get updated task and broadcast change
    updated_task = await db.tasks.find_one({"id": task_id})
    
    # Find and return the updated subtask
    updated_subtask = None
    for todo in updated_task.get("todos", []):
        if todo["id"] == subtask_id:
            updated_subtask = TodoItem(**todo)
            break
    
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return updated_subtask

@api_router.delete("/tasks/{task_id}/subtasks/{subtask_id}")
async def delete_subtask(
    task_id: str,
    subtask_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Remove subtask from todos array
    result = await db.tasks.update_one(
        {"id": task_id},
        {
            "$pull": {"todos": {"id": subtask_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subtask not found")
    
    # Get updated task and broadcast change
    updated_task = await db.tasks.find_one({"id": task_id})
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return {"message": "Subtask deleted successfully"}

# Subtask Comments Endpoints
@api_router.post("/tasks/{task_id}/subtasks/{subtask_id}/comments", response_model=SubtaskComment)
async def add_subtask_comment(
    task_id: str,
    subtask_id: str,
    comment_data: SubtaskCommentCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Find the subtask
    subtask_index = -1
    for i, todo in enumerate(task.get("todos", [])):
        if todo["id"] == subtask_id:
            subtask_index = i
            break
    
    if subtask_index == -1:
        raise HTTPException(status_code=404, detail="Subtask not found")
    
    # Create comment
    comment = SubtaskComment(
        user_id=current_user.id,
        username=current_user.username,
        comment=comment_data.comment
    )
    
    # Add comment to subtask
    await db.tasks.update_one(
        {"id": task_id},
        {
            "$push": {f"todos.{subtask_index}.comments": comment.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Get updated task and broadcast change
    updated_task = await db.tasks.find_one({"id": task_id})
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return comment

@api_router.put("/tasks/{task_id}/subtasks/{subtask_id}/comments/{comment_id}", response_model=SubtaskComment)
async def update_subtask_comment(
    task_id: str,
    subtask_id: str,
    comment_id: str,
    comment_update: SubtaskCommentUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Find the subtask and comment
    subtask_index = -1
    comment_index = -1
    current_comment = None
    
    for i, todo in enumerate(task.get("todos", [])):
        if todo["id"] == subtask_id:
            subtask_index = i
            for j, comment in enumerate(todo.get("comments", [])):
                if comment["id"] == comment_id:
                    comment_index = j
                    current_comment = comment
                    break
            break
    
    if subtask_index == -1:
        raise HTTPException(status_code=404, detail="Subtask not found")
    if comment_index == -1:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify user owns the comment
    if current_comment["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    
    # Update comment
    await db.tasks.update_one(
        {"id": task_id},
        {
            "$set": {
                f"todos.{subtask_index}.comments.{comment_index}.comment": comment_update.comment,
                f"todos.{subtask_index}.comments.{comment_index}.updated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Get updated task and find the updated comment
    updated_task = await db.tasks.find_one({"id": task_id})
    updated_comment = updated_task["todos"][subtask_index]["comments"][comment_index]
    
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return SubtaskComment(**updated_comment)

@api_router.delete("/tasks/{task_id}/subtasks/{subtask_id}/comments/{comment_id}")
async def delete_subtask_comment(
    task_id: str,
    subtask_id: str,
    comment_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify user has access to the task
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
    
    # Find the subtask and comment to verify ownership
    subtask_index = -1
    comment_to_delete = None
    
    for i, todo in enumerate(task.get("todos", [])):
        if todo["id"] == subtask_id:
            subtask_index = i
            for comment in todo.get("comments", []):
                if comment["id"] == comment_id:
                    comment_to_delete = comment
                    break
            break
    
    if subtask_index == -1:
        raise HTTPException(status_code=404, detail="Subtask not found")
    if not comment_to_delete:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify user owns the comment
    if comment_to_delete["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    
    # Remove comment from subtask
    await db.tasks.update_one(
        {"id": task_id},
        {
            "$pull": {f"todos.{subtask_index}.comments": {"id": comment_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Get updated task and broadcast change
    updated_task = await db.tasks.find_one({"id": task_id})
    await manager.broadcast_task_update(updated_task, "updated", current_user.id)
    
    return {"message": "Comment deleted successfully"}

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

# Helper function to build task access filter
async def build_task_access_filter(task_id: str, current_user: UserInDB):
    """Build filter to check if user has access to a task (including team assignments)"""
    user_teams = current_user.team_ids if hasattr(current_user, 'team_ids') else []
    
    filter_conditions = [
        {"owner_id": current_user.id},
        {"assigned_users": current_user.id},
        {"collaborators": current_user.id}
    ]
    
    # Add team-assigned tasks if user has teams
    if user_teams:
        filter_conditions.append({"assigned_teams": {"$in": user_teams}})
    
    return {
        "id": task_id,
        "$or": filter_conditions
    }

# Timer endpoints
@api_router.post("/tasks/{task_id}/timer/start")
async def start_task_timer(task_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """Start timer for a task and set status to in_progress"""
    task_filter = await build_task_access_filter(task_id, current_user)
    task = await db.tasks.find_one(task_filter)
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
    task_filter = await build_task_access_filter(task_id, current_user)
    task = await db.tasks.find_one(task_filter)
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
    task_filter = await build_task_access_filter(task_id, current_user)
    task = await db.tasks.find_one(task_filter)
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
    task_filter = await build_task_access_filter(task_id, current_user)
    task = await db.tasks.find_one(task_filter)
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
    task_filter = await build_task_access_filter(task_id, current_user)
    task = await db.tasks.find_one(task_filter)
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

# Admin User Management endpoints
@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(current_user: UserInDB = Depends(get_current_admin_user)):
    """Get all users (admin only)"""
    users = await db.users.find({}).sort("created_at", -1).to_list(1000)
    return [UserResponse(**user) for user in users]

@api_router.post("/admin/users", response_model=UserResponse)
async def create_user_by_admin(user_data: AdminUserCreate, current_user: UserInDB = Depends(get_current_admin_user)):
    """Create a new user (admin only)"""
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
    
    return UserResponse(**user.dict())

@api_router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(user_id: str, user_update: AdminUserUpdate, current_user: UserInDB = Depends(get_current_admin_user)):
    """Update a user (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for duplicate email/username if being updated
    if user_update.email or user_update.username:
        filter_conditions = []
        if user_update.email:
            filter_conditions.append({"email": user_update.email})
        if user_update.username:
            filter_conditions.append({"username": user_update.username})
        
        existing_user = await db.users.find_one({
            "$or": filter_conditions,
            "id": {"$ne": user_id}  # Exclude current user
        })
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already exists"
            )
    
    update_dict = {k: v for k, v in user_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.users.update_one({"id": user_id}, {"$set": update_dict})
    updated_user = await db.users.find_one({"id": user_id})
    return UserResponse(**updated_user)

@api_router.delete("/admin/users/{user_id}")
async def delete_user_by_admin(user_id: str, current_user: UserInDB = Depends(get_current_admin_user)):
    """Delete a user (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    # Remove user from all teams
    await db.teams.update_many(
        {"$or": [{"members": user_id}, {"team_lead_id": user_id}]},
        {"$pull": {"members": user_id}, "$unset": {"team_lead_id": ""}}
    )
    
    # Deactivate instead of delete to preserve data integrity
    await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "User deactivated successfully"}

# Team Management endpoints
@api_router.get("/admin/teams", response_model=List[Team])
async def get_all_teams(current_user: UserInDB = Depends(get_current_admin_user)):
    """Get all teams (admin only)"""
    teams = await db.teams.find({"is_active": True}).sort("created_at", -1).to_list(1000)
    return [Team(**team) for team in teams]

@api_router.post("/admin/teams", response_model=Team)
async def create_team(team_data: TeamCreate, current_user: UserInDB = Depends(get_current_admin_user)):
    """Create a new team (admin only)"""
    # Check if team name already exists
    existing_team = await db.teams.find_one({"name": team_data.name, "is_active": True})
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already exists"
        )
    
    # Validate team lead and members exist
    if team_data.team_lead_id:
        team_lead = await db.users.find_one({"id": team_data.team_lead_id, "is_active": True})
        if not team_lead:
            raise HTTPException(status_code=404, detail="Team lead not found")
    
    for member_id in team_data.members:
        member = await db.users.find_one({"id": member_id, "is_active": True})
        if not member:
            raise HTTPException(status_code=404, detail=f"Member with ID {member_id} not found")
    
    team_dict = team_data.dict()
    team_dict["created_by"] = current_user.id
    
    team = Team(**team_dict)
    await db.teams.insert_one(team.dict())
    
    # Update users' team_ids
    if team_data.members:
        await db.users.update_many(
            {"id": {"$in": team_data.members}},
            {"$addToSet": {"team_ids": team.id}}
        )
    
    if team_data.team_lead_id and team_data.team_lead_id not in team_data.members:
        await db.users.update_one(
            {"id": team_data.team_lead_id},
            {"$addToSet": {"team_ids": team.id}}
        )
    
    return team

@api_router.put("/admin/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, team_update: TeamUpdate, current_user: UserInDB = Depends(get_current_admin_user)):
    """Update a team (admin only)"""
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check for duplicate name if being updated
    if team_update.name and team_update.name != team["name"]:
        existing_team = await db.teams.find_one({
            "name": team_update.name,
            "is_active": True,
            "id": {"$ne": team_id}
        })
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team name already exists"
            )
    
    # Validate new team lead and members
    if team_update.team_lead_id:
        team_lead = await db.users.find_one({"id": team_update.team_lead_id, "is_active": True})
        if not team_lead:
            raise HTTPException(status_code=404, detail="Team lead not found")
    
    if team_update.members:
        for member_id in team_update.members:
            member = await db.users.find_one({"id": member_id, "is_active": True})
            if not member:
                raise HTTPException(status_code=404, detail=f"Member with ID {member_id} not found")
    
    update_dict = {k: v for k, v in team_update.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    # Handle member changes
    if team_update.members is not None:
        # Remove team from old members
        old_members = set(team.get("members", []))
        new_members = set(team_update.members)
        
        members_to_remove = old_members - new_members
        members_to_add = new_members - old_members
        
        if members_to_remove:
            await db.users.update_many(
                {"id": {"$in": list(members_to_remove)}},
                {"$pull": {"team_ids": team_id}}
            )
        
        if members_to_add:
            await db.users.update_many(
                {"id": {"$in": list(members_to_add)}},
                {"$addToSet": {"team_ids": team_id}}
            )
    
    await db.teams.update_one({"id": team_id}, {"$set": update_dict})
    updated_team = await db.teams.find_one({"id": team_id})
    return Team(**updated_team)

@api_router.delete("/admin/teams/{team_id}")
async def delete_team(team_id: str, current_user: UserInDB = Depends(get_current_admin_user)):
    """Delete a team (admin only)"""
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Remove team from all users
    await db.users.update_many(
        {"team_ids": team_id},
        {"$pull": {"team_ids": team_id}}
    )
    
    # Deactivate team instead of deleting
    await db.teams.update_one(
        {"id": team_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Team deleted successfully"}

@api_router.get("/admin/teams/{team_id}", response_model=Team)
async def get_team(team_id: str, current_user: UserInDB = Depends(get_current_admin_user)):
    """Get a specific team (admin only)"""
    team = await db.teams.find_one({"id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return Team(**team)

# Admin Dashboard Analytics
@api_router.get("/admin/analytics/dashboard")
async def get_admin_dashboard_analytics(current_user: UserInDB = Depends(get_current_admin_user)):
    """Get comprehensive admin dashboard analytics"""
    
    # Get all data for admin analytics
    all_users = await db.users.find({"is_active": True}).to_list(1000)
    all_teams = await db.teams.find({"is_active": True}).to_list(1000)
    all_projects = await db.projects.find({}).to_list(1000)
    all_tasks = await db.tasks.find({}).to_list(1000)
    
    # Create user and team lookup maps
    users_map = {user["id"]: user for user in all_users}
    teams_map = {team["id"]: team for team in all_teams}
    
    # Current date calculations
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Basic statistics
    total_users = len(all_users)
    admin_users = len([u for u in all_users if u.get("role") == "admin"])
    project_manager_users = len([u for u in all_users if u.get("role") == "project_manager"])
    regular_users = total_users - admin_users - project_manager_users
    total_teams = len(all_teams)
    total_projects = len(all_projects)
    active_projects = len([p for p in all_projects if p.get("status") == "active"])
    completed_projects = len([p for p in all_projects if p.get("status") == "completed"])
    
    # Task statistics
    total_tasks = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.get("status") == "completed"])
    in_progress_tasks = len([t for t in all_tasks if t.get("status") == "in_progress"])
    todo_tasks = len([t for t in all_tasks if t.get("status") == "todo"])
    
    # Tasks scheduled this week
    tasks_scheduled_this_week = []
    task_hours_scheduled_this_week = 0
    for task in all_tasks:
        if task.get("due_date") or task.get("start_time"):
            try:
                task_date = None
                if task.get("start_time"):
                    task_date = datetime.fromisoformat(task["start_time"].replace('Z', '+00:00')) if isinstance(task["start_time"], str) else task["start_time"]
                elif task.get("due_date"):
                    task_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00')) if isinstance(task["due_date"], str) else task["due_date"]
                
                if task_date and week_start <= task_date <= week_end:
                    tasks_scheduled_this_week.append(task)
                    task_hours_scheduled_this_week += task.get("estimated_duration", 0) / 60  # Convert minutes to hours
            except:
                continue
    
    # Past deadline tasks
    past_deadline_tasks = []
    for task in all_tasks:
        if task.get("due_date") and task.get("status") != "completed":
            try:
                due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00')) if isinstance(task["due_date"], str) else task["due_date"]
                if due_date < now:
                    past_deadline_tasks.append(task)
            except:
                continue
    
    # Completed tasks this week
    completed_tasks_this_week = []
    completed_task_hours_this_week = 0
    for task in all_tasks:
        if task.get("status") == "completed" and task.get("completed_at"):
            try:
                completed_date = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00')) if isinstance(task["completed_at"], str) else task["completed_at"]
                if week_start <= completed_date <= week_end:
                    completed_tasks_this_week.append(task)
                    completed_task_hours_this_week += (task.get("timer_elapsed_seconds", 0) or task.get("estimated_duration", 0) * 60) / 3600  # Convert to hours
            except:
                continue
    
    # Tasks by Project analytics
    tasks_by_project = {}
    for project in all_projects:
        project_tasks = [t for t in all_tasks if t.get("project_id") == project["id"]]
        tasks_by_project[project["name"]] = {
            "total": len(project_tasks),
            "completed": len([t for t in project_tasks if t.get("status") == "completed"]),
            "in_progress": len([t for t in project_tasks if t.get("status") == "in_progress"]),
            "todo": len([t for t in project_tasks if t.get("status") == "todo"])
        }
    
    # Tasks by Team analytics
    tasks_by_team = {}
    for team in all_teams:
        team_tasks = []
        team_member_ids = team.get("members", [])
        for task in all_tasks:
            if any(member_id in task.get("assigned_users", []) for member_id in team_member_ids):
                team_tasks.append(task)
        
        tasks_by_team[team["name"]] = {
            "total": len(team_tasks),
            "completed": len([t for t in team_tasks if t.get("status") == "completed"]),
            "in_progress": len([t for t in team_tasks if t.get("status") == "in_progress"]),
            "todo": len([t for t in team_tasks if t.get("status") == "todo"])
        }
    
    # Projects by ETA analytics
    projects_by_eta = {"On Time": 0, "At Risk": 0, "Overdue": 0, "No Deadline": 0}
    for project in all_projects:
        if not project.get("end_date"):
            projects_by_eta["No Deadline"] += 1
        else:
            try:
                end_date = datetime.fromisoformat(project["end_date"].replace('Z', '+00:00')) if isinstance(project["end_date"], str) else project["end_date"]
                progress = project.get("progress_percentage", 0)
                days_remaining = (end_date - now).days
                
                if end_date < now and progress < 100:
                    projects_by_eta["Overdue"] += 1
                elif days_remaining < 7 and progress < 80:
                    projects_by_eta["At Risk"] += 1
                else:
                    projects_by_eta["On Time"] += 1
            except:
                projects_by_eta["No Deadline"] += 1
    
    # Tasks by Assignee analytics
    tasks_by_assignee = {}
    for user in all_users:
        user_tasks = []
        for task in all_tasks:
            if user["id"] in task.get("assigned_users", []) or task.get("owner_id") == user["id"]:
                user_tasks.append(task)
        
        if user_tasks:  # Only include users with tasks
            tasks_by_assignee[user["full_name"]] = {
                "total": len(user_tasks),
                "completed": len([t for t in user_tasks if t.get("status") == "completed"]),
                "in_progress": len([t for t in user_tasks if t.get("status") == "in_progress"]),
                "todo": len([t for t in user_tasks if t.get("status") == "todo"]),
                "overdue": len([t for t in user_tasks if t in past_deadline_tasks])
            }
    
    # Completed hours week over week (last 8 weeks)
    completed_hours_weekly = []
    for week_offset in range(8, 0, -1):
        week_start_offset = now - timedelta(days=now.weekday() + (week_offset * 7))
        week_end_offset = week_start_offset + timedelta(days=6)
        
        week_completed_tasks = []
        for task in all_tasks:
            if task.get("status") == "completed" and task.get("completed_at"):
                try:
                    completed_date = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00')) if isinstance(task["completed_at"], str) else task["completed_at"]
                    if week_start_offset <= completed_date <= week_end_offset:
                        week_completed_tasks.append(task)
                except:
                    continue
        
        total_hours = sum((t.get("timer_elapsed_seconds", 0) or t.get("estimated_duration", 0) * 60) / 3600 for t in week_completed_tasks)
        completed_hours_weekly.append({
            "week": week_start_offset.strftime("%Y-W%U"),
            "date": week_start_offset.strftime("%b %d"),
            "hours": round(total_hours, 1)
        })
    
    # Team completion estimates
    team_completion_estimates = {}
    for team in all_teams:
        team_member_ids = team.get("members", [])
        team_tasks = [t for t in all_tasks if any(member_id in t.get("assigned_users", []) for member_id in team_member_ids) and t.get("status") != "completed"]
        
        if team_tasks:
            total_estimated_hours = sum(t.get("estimated_duration", 0) for t in team_tasks) / 60  # Convert to hours
            avg_completion_rate = 8  # Assume 8 hours per day per team member
            
            estimated_days = max(1, total_estimated_hours / (len(team_member_ids) * avg_completion_rate)) if team_member_ids else 1
            team_completion_estimates[team["name"]] = {
                "estimated_days": round(estimated_days, 1),
                "remaining_tasks": len(team_tasks),
                "estimated_hours": round(total_estimated_hours, 1)
            }
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = await db.users.count_documents({"created_at": {"$gte": week_ago}})
    recent_tasks = await db.tasks.count_documents({"created_at": {"$gte": week_ago}})
    recent_projects = await db.projects.count_documents({"created_at": {"$gte": week_ago}})
    
    # Top teams by task completion
    top_teams = []
    for team in all_teams:
        team_member_ids = team.get("members", [])
        team_completed_tasks = sum(1 for t in all_tasks if any(member_id in t.get("assigned_users", []) for member_id in team_member_ids) and t.get("status") == "completed")
        team_total_tasks = sum(1 for t in all_tasks if any(member_id in t.get("assigned_users", []) for member_id in team_member_ids))
        
        if team_total_tasks > 0:
            top_teams.append({
                "_id": team["id"],
                "name": team["name"],
                "task_count": team_completed_tasks,
                "members": len(team_member_ids),
                "completion_rate": round((team_completed_tasks / team_total_tasks) * 100, 1)
            })
    
    top_teams.sort(key=lambda x: x["completion_rate"], reverse=True)
    top_teams = top_teams[:5]
    
    # Most active users (by task completion)
    most_active_users = []
    for user in all_users:
        user_completed_tasks = sum(1 for t in all_tasks if (user["id"] in t.get("assigned_users", []) or t.get("owner_id") == user["id"]) and t.get("status") == "completed")
        
        if user_completed_tasks > 0:
            most_active_users.append({
                "user_id": user["id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "completed_tasks": user_completed_tasks
            })
    
    most_active_users.sort(key=lambda x: x["completed_tasks"], reverse=True)
    most_active_users = most_active_users[:5]
    
    return {
        "overview": {
            "total_users": total_users,
            "admin_users": admin_users,
            "project_manager_users": project_manager_users,
            "regular_users": regular_users,
            "total_teams": total_teams,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "todo_tasks": todo_tasks,
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2),
            
            # New metrics
            "tasks_scheduled_this_week": len(tasks_scheduled_this_week),
            "task_hours_scheduled_this_week": round(task_hours_scheduled_this_week, 1),
            "past_deadline_tasks": len(past_deadline_tasks),
            "completed_tasks_this_week": len(completed_tasks_this_week),
            "completed_task_hours_this_week": round(completed_task_hours_this_week, 1)
        },
        "recent_activity": {
            "new_users_week": recent_users,
            "new_tasks_week": recent_tasks,
            "new_projects_week": recent_projects
        },
        "top_teams": top_teams,
        "most_active_users": most_active_users,
        "analytics": {
            "tasks_by_project": tasks_by_project,
            "tasks_by_team": tasks_by_team,
            "projects_by_eta": projects_by_eta,
            "tasks_by_assignee": tasks_by_assignee,
            "completed_hours_weekly": completed_hours_weekly,
            "team_completion_estimates": team_completion_estimates
        },
        "generated_at": datetime.utcnow().isoformat()
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

# Project Manager Dashboard endpoints
@api_router.get("/pm/dashboard")
async def get_project_manager_dashboard(current_user: UserInDB = Depends(get_current_project_manager)):
    """Get enhanced project manager dashboard analytics"""
    
    # Get projects the user can manage
    if current_user.role == UserRole.ADMIN:
        # Admin can see all projects
        projects = await db.projects.find({}).to_list(1000)
        # Get all tasks for admin
        all_tasks = await db.tasks.find({}).to_list(1000)
        all_users = await db.users.find({"is_active": True}).to_list(1000)
        all_teams = await db.teams.find({"is_active": True}).to_list(1000)
    else:
        # Project managers can see projects they're assigned to
        projects = await db.projects.find({
            "$or": [
                {"project_managers": current_user.id},
                {"owner_id": current_user.id}
            ]
        }).to_list(1000)
        
        # Get tasks for managed projects and assigned to user
        project_ids = [p["id"] for p in projects]
        all_tasks = await db.tasks.find({
            "$or": [
                {"project_id": {"$in": project_ids}},
                {"assigned_users": current_user.id},
                {"collaborators": current_user.id},
                {"owner_id": current_user.id}
            ]
        }).to_list(1000)
        
        # Get relevant users and teams
        all_users = await db.users.find({"is_active": True}).to_list(1000)
        all_teams = await db.teams.find({"is_active": True}).to_list(1000)
    
    # Create user and team lookup maps
    users_map = {user["id"]: user for user in all_users}
    teams_map = {team["id"]: team for team in all_teams}
    
    # Current date calculations
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Basic project statistics
    total_projects = len(projects)
    active_projects = len([p for p in projects if p.get("status") == "active"])
    completed_projects = len([p for p in projects if p.get("status") == "completed"])
    at_risk_projects = len([p for p in projects if p.get("status") == "on_hold"])
    
    # Enhanced task analytics
    tasks_assigned_to_me = [t for t in all_tasks if current_user.id in t.get("assigned_users", []) or t.get("owner_id") == current_user.id]
    
    # Tasks scheduled this week
    tasks_scheduled_this_week = []
    task_hours_scheduled_this_week = 0
    for task in all_tasks:
        if task.get("due_date") or task.get("start_time"):
            try:
                task_date = None
                if task.get("start_time"):
                    task_date = datetime.fromisoformat(task["start_time"].replace('Z', '+00:00')) if isinstance(task["start_time"], str) else task["start_time"]
                elif task.get("due_date"):
                    task_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00')) if isinstance(task["due_date"], str) else task["due_date"]
                
                if task_date and week_start <= task_date <= week_end:
                    tasks_scheduled_this_week.append(task)
                    task_hours_scheduled_this_week += task.get("estimated_duration", 0) / 60  # Convert minutes to hours
            except:
                continue
    
    # Past deadline tasks
    past_deadline_tasks = []
    for task in all_tasks:
        if task.get("due_date") and task.get("status") != "completed":
            try:
                due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00')) if isinstance(task["due_date"], str) else task["due_date"]
                if due_date < now:
                    past_deadline_tasks.append(task)
            except:
                continue
    
    # Completed tasks this week
    completed_tasks_this_week = []
    completed_task_hours_this_week = 0
    for task in all_tasks:
        if task.get("status") == "completed" and task.get("completed_at"):
            try:
                completed_date = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00')) if isinstance(task["completed_at"], str) else task["completed_at"]
                if week_start <= completed_date <= week_end:
                    completed_tasks_this_week.append(task)
                    completed_task_hours_this_week += (task.get("timer_elapsed_seconds", 0) or task.get("estimated_duration", 0) * 60) / 3600  # Convert to hours
            except:
                continue
    
    # Tasks by Project analytics
    tasks_by_project = {}
    for project in projects:
        project_tasks = [t for t in all_tasks if t.get("project_id") == project["id"]]
        tasks_by_project[project["name"]] = {
            "total": len(project_tasks),
            "completed": len([t for t in project_tasks if t.get("status") == "completed"]),
            "in_progress": len([t for t in project_tasks if t.get("status") == "in_progress"]),
            "todo": len([t for t in project_tasks if t.get("status") == "todo"])
        }
    
    # Tasks by Team analytics
    tasks_by_team = {}
    for team in all_teams:
        team_tasks = []
        team_member_ids = team.get("members", [])
        for task in all_tasks:
            if any(member_id in task.get("assigned_users", []) for member_id in team_member_ids):
                team_tasks.append(task)
        
        tasks_by_team[team["name"]] = {
            "total": len(team_tasks),
            "completed": len([t for t in team_tasks if t.get("status") == "completed"]),
            "in_progress": len([t for t in team_tasks if t.get("status") == "in_progress"]),
            "todo": len([t for t in team_tasks if t.get("status") == "todo"])
        }
    
    # Projects by ETA analytics
    projects_by_eta = {"On Time": 0, "At Risk": 0, "Overdue": 0, "No Deadline": 0}
    for project in projects:
        if not project.get("end_date"):
            projects_by_eta["No Deadline"] += 1
        else:
            try:
                end_date = datetime.fromisoformat(project["end_date"].replace('Z', '+00:00')) if isinstance(project["end_date"], str) else project["end_date"]
                progress = project.get("progress_percentage", 0)
                days_remaining = (end_date - now).days
                
                if end_date < now and progress < 100:
                    projects_by_eta["Overdue"] += 1
                elif days_remaining < 7 and progress < 80:
                    projects_by_eta["At Risk"] += 1
                else:
                    projects_by_eta["On Time"] += 1
            except:
                projects_by_eta["No Deadline"] += 1
    
    # Tasks by Assignee analytics
    tasks_by_assignee = {}
    for user in all_users:
        user_tasks = []
        for task in all_tasks:
            if user["id"] in task.get("assigned_users", []) or task.get("owner_id") == user["id"]:
                user_tasks.append(task)
        
        if user_tasks:  # Only include users with tasks
            tasks_by_assignee[user["full_name"]] = {
                "total": len(user_tasks),
                "completed": len([t for t in user_tasks if t.get("status") == "completed"]),
                "in_progress": len([t for t in user_tasks if t.get("status") == "in_progress"]),
                "todo": len([t for t in user_tasks if t.get("status") == "todo"]),
                "overdue": len([t for t in user_tasks if t in past_deadline_tasks])
            }
    
    # Completed hours week over week (last 8 weeks)
    completed_hours_weekly = []
    for week_offset in range(8, 0, -1):
        week_start_offset = now - timedelta(days=now.weekday() + (week_offset * 7))
        week_end_offset = week_start_offset + timedelta(days=6)
        
        week_completed_tasks = []
        for task in all_tasks:
            if task.get("status") == "completed" and task.get("completed_at"):
                try:
                    completed_date = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00')) if isinstance(task["completed_at"], str) else task["completed_at"]
                    if week_start_offset <= completed_date <= week_end_offset:
                        week_completed_tasks.append(task)
                except:
                    continue
        
        total_hours = sum((t.get("timer_elapsed_seconds", 0) or t.get("estimated_duration", 0) * 60) / 3600 for t in week_completed_tasks)
        completed_hours_weekly.append({
            "week": week_start_offset.strftime("%Y-W%U"),
            "date": week_start_offset.strftime("%b %d"),
            "hours": round(total_hours, 1)
        })
    
    # Team completion estimates
    team_completion_estimates = {}
    for team in all_teams:
        team_member_ids = team.get("members", [])
        team_tasks = [t for t in all_tasks if any(member_id in t.get("assigned_users", []) for member_id in team_member_ids) and t.get("status") != "completed"]
        
        if team_tasks:
            total_estimated_hours = sum(t.get("estimated_duration", 0) for t in team_tasks) / 60  # Convert to hours
            avg_completion_rate = 8  # Assume 8 hours per day per team member
            
            estimated_days = max(1, total_estimated_hours / (len(team_member_ids) * avg_completion_rate)) if team_member_ids else 1
            team_completion_estimates[team["name"]] = {
                "estimated_days": round(estimated_days, 1),
                "remaining_tasks": len(team_tasks),
                "estimated_hours": round(total_estimated_hours, 1)
            }
    
    # Get team members for workload calculation
    team_members = set()
    for project in projects:
        team_members.update(project.get("collaborators", []))
        team_members.update(project.get("project_managers", []))
        team_members.add(project.get("owner_id"))
    
    # Enhanced team workload
    team_workload = {}
    for member_id in team_members:
        if member_id and member_id in users_map:
            user = users_map[member_id]
            member_tasks = [t for t in all_tasks if member_id in t.get("assigned_users", []) or member_id in t.get("collaborators", []) or t.get("owner_id") == member_id]
            active_tasks = [t for t in member_tasks if t.get("status") in ["todo", "in_progress"]]
            overdue_member_tasks = [t for t in member_tasks if t in past_deadline_tasks]
            
            team_workload[member_id] = {
                "user": {
                    "id": user["id"],
                    "full_name": user["full_name"],
                    "role": user["role"]
                },
                "tasks": {
                    "total": len(member_tasks),
                    "active": len(active_tasks),
                    "completed": len([t for t in member_tasks if t.get("status") == "completed"]),
                    "overdue": len(overdue_member_tasks)
                },
                "availability": "available" if len(active_tasks) <= 5 else "busy"
            }
    
    # Recent activity
    week_ago = datetime.utcnow() - timedelta(days=7)
    project_ids = [p["id"] for p in projects]
    recent_activities = await db.activity_logs.find({
        "project_id": {"$in": project_ids},
        "timestamp": {"$gte": week_ago}
    }).sort("timestamp", -1).limit(20).to_list(20)
    
    return {
        "overview": {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "at_risk_projects": at_risk_projects,
            "total_tasks": len(all_tasks),
            "completed_tasks": len([t for t in all_tasks if t.get("status") == "completed"]),
            "in_progress_tasks": len([t for t in all_tasks if t.get("status") == "in_progress"]),
            "overdue_tasks": len(past_deadline_tasks),
            "blocked_tasks": len([t for t in all_tasks if t.get("status") == "blocked"]),
            "team_size": len(team_members),
            
            # New metrics
            "tasks_assigned_to_me": len(tasks_assigned_to_me),
            "tasks_scheduled_this_week": len(tasks_scheduled_this_week),
            "task_hours_scheduled_this_week": round(task_hours_scheduled_this_week, 1),
            "past_deadline_tasks": len(past_deadline_tasks),
            "completed_tasks_this_week": len(completed_tasks_this_week),
            "completed_task_hours_this_week": round(completed_task_hours_this_week, 1)
        },
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "status": p["status"],
                "auto_calculated_status": p.get("auto_calculated_status", p["status"]),
                "progress_percentage": p.get("progress_percentage", 0),
                "task_count": p.get("task_count", 0),
                "completed_task_count": p.get("completed_task_count", 0),
                "start_date": p.get("start_date"),
                "end_date": p.get("end_date"),
                "assigned_teams": p.get("assigned_teams", []),
                "project_managers": p.get("project_managers", []),
                "updated_at": p.get("updated_at")
            }
            for p in projects
        ],
        "team_workload": team_workload,
        "recent_activities": [
            {
                "id": a["id"],
                "user_id": a["user_id"],
                "action": a["action"],
                "entity_type": a["entity_type"],
                "entity_name": a["entity_name"],
                "project_id": a.get("project_id"),
                "timestamp": a["timestamp"]
            }
            for a in recent_activities
        ],
        
        # New analytics sections
        "analytics": {
            "tasks_by_project": tasks_by_project,
            "tasks_by_team": tasks_by_team,
            "projects_by_eta": projects_by_eta,
            "tasks_by_assignee": tasks_by_assignee,
            "completed_hours_weekly": completed_hours_weekly,
            "team_completion_estimates": team_completion_estimates
        }
    }

@api_router.get("/pm/projects")
async def get_managed_projects(current_user: UserInDB = Depends(get_current_project_manager)):
    """Get projects that the current user can manage"""
    
    if current_user.role == UserRole.ADMIN:
        # Admin can see all projects
        projects = await db.projects.find({}).to_list(1000)
    else:
        # Project managers can see projects they're assigned to
        projects = await db.projects.find({
            "$or": [
                {"project_managers": current_user.id},
                {"owner_id": current_user.id}
            ]
        }).to_list(1000)
    
    # Update project progress for all projects
    for project in projects:
        await update_project_progress(project["id"])
    
    # Re-fetch updated projects
    updated_projects = await db.projects.find({
        "id": {"$in": [p["id"] for p in projects]}
    }).to_list(1000)
    
    return [Project(**project) for project in updated_projects]

@api_router.put("/pm/projects/{project_id}/status")
async def update_project_status(project_id: str, status_update: dict, current_user: UserInDB = Depends(get_current_project_manager)):
    """Update project status (manual override)"""
    
    # Check if user can manage this project
    if not await check_project_manager_access(project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update status override
    new_status = status_update.get("status")
    if new_status:
        update_data = {
            "status": new_status,
            "status_override": new_status,
            "updated_at": datetime.utcnow()
        }
        
        await db.projects.update_one({"id": project_id}, {"$set": update_data})
        
        # Log activity
        await log_activity(
            user_id=current_user.id,
            action="status_updated",
            entity_type="project",
            entity_id=project_id,
            entity_name=project["name"],
            project_id=project_id,
            details={"old_status": project["status"], "new_status": new_status}
        )
        
        # Create notifications for team members
        team_members = set(project.get("collaborators", []) + project.get("project_managers", []))
        if project.get("owner_id"):
            team_members.add(project["owner_id"])
        
        for member_id in team_members:
            if member_id != current_user.id:
                await create_notification(
                    user_id=member_id,
                    title="Project Status Updated",
                    message=f"Project '{project['name']}' status changed to {new_status}",
                    notification_type="project_update",
                    priority="medium",
                    entity_type="project",
                    entity_id=project_id,
                    project_id=project_id
                )
    
    return {"message": "Project status updated successfully"}

@api_router.get("/pm/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, current_user: UserInDB = Depends(get_current_project_manager)):
    """Get tasks for a specific project"""
    
    # Check if user can manage this project
    if not await check_project_manager_access(project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    tasks = await db.tasks.find({"project_id": project_id}).sort("created_at", -1).to_list(1000)
    return [Task(**task) for task in tasks]

@api_router.get("/pm/projects/{project_id}/team")
async def get_project_team(project_id: str, current_user: UserInDB = Depends(get_current_project_manager)):
    """Get team members for a specific project"""
    
    # Check if user can manage this project
    if not await check_project_manager_access(project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all team members
    team_member_ids = set(project.get("collaborators", []) + project.get("project_managers", []))
    if project.get("owner_id"):
        team_member_ids.add(project["owner_id"])
    
    # Get user details
    team_members = await db.users.find({"id": {"$in": list(team_member_ids)}}).to_list(1000)
    
    # Get task assignments for each member
    project_tasks = await db.tasks.find({"project_id": project_id}).to_list(1000)
    
    member_workload = {}
    for member in team_members:
        member_id = member["id"]
        member_tasks = [t for t in project_tasks if member_id in t.get("assigned_users", []) or member_id in t.get("collaborators", []) or t.get("owner_id") == member_id]
        
        active_tasks = [t for t in member_tasks if t.get("status") in ["todo", "in_progress"]]
        completed_tasks = [t for t in member_tasks if t.get("status") == "completed"]
        
        # Handle datetime parsing for overdue tasks
        overdue_tasks = []
        for task in member_tasks:
            if task.get("due_date") and task.get("status") != "completed":
                try:
                    due_date = task["due_date"]
                    if isinstance(due_date, str):
                        # Parse string datetime
                        due_date_obj = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        # Already a datetime object
                        due_date_obj = due_date
                    
                    if due_date_obj < datetime.utcnow():
                        overdue_tasks.append(task)
                except (ValueError, TypeError) as e:
                    # Skip tasks with invalid datetime formats
                    continue
        
        member_workload[member_id] = {
            "user": {
                "id": member["id"],
                "username": member["username"],
                "full_name": member["full_name"],
                "email": member["email"],
                "role": member["role"]
            },
            "tasks": {
                "total": len(member_tasks),
                "active": len(active_tasks),
                "completed": len(completed_tasks),
                "overdue": len(overdue_tasks)
            },
            "availability": "busy" if len(active_tasks) > 3 else "available"
        }
    
    return list(member_workload.values())

@api_router.get("/pm/activity")
async def get_project_activity(current_user: UserInDB = Depends(get_current_project_manager), project_id: str = None, limit: int = 50):
    """Get activity log for projects"""
    
    # Get projects the user can manage
    if current_user.role == UserRole.ADMIN:
        # Admin can see all projects
        managed_projects = await db.projects.find({}).to_list(1000)
    else:
        # Project managers can see projects they're assigned to
        managed_projects = await db.projects.find({
            "$or": [
                {"project_managers": current_user.id},
                {"owner_id": current_user.id}
            ]
        }).to_list(1000)
    
    managed_project_ids = [p["id"] for p in managed_projects]
    
    # Build filter
    filter_dict = {"project_id": {"$in": managed_project_ids}}
    if project_id:
        if project_id not in managed_project_ids:
            raise HTTPException(status_code=403, detail="Access denied")
        filter_dict["project_id"] = project_id
    
    activities = await db.activity_logs.find(filter_dict).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return [
        {
            "id": a["id"],
            "user_id": a["user_id"],
            "action": a["action"],
            "entity_type": a["entity_type"],
            "entity_name": a["entity_name"],
            "project_id": a.get("project_id"),
            "details": a.get("details", {}),
            "timestamp": a["timestamp"]
        }
        for a in activities
    ]

@api_router.get("/pm/notifications")
async def get_project_notifications(current_user: UserInDB = Depends(get_current_project_manager), unread_only: bool = False):
    """Get notifications for project manager"""
    
    filter_dict = {"user_id": current_user.id}
    if unread_only:
        filter_dict["read"] = False
    
    notifications = await db.notifications.find(filter_dict).sort("created_at", -1).limit(100).to_list(100)
    
    return [
        {
            "id": n["id"],
            "title": n["title"],
            "message": n["message"],
            "type": n["type"],
            "priority": n["priority"],
            "read": n["read"],
            "entity_type": n.get("entity_type"),
            "entity_id": n.get("entity_id"),
            "project_id": n.get("project_id"),
            "action_url": n.get("action_url"),
            "created_at": n["created_at"]
        }
        for n in notifications
    ]

@api_router.put("/pm/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: UserInDB = Depends(get_current_project_manager)):
    """Mark a notification as read"""
    
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}

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