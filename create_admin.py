#!/usr/bin/env python3
"""
Create an admin user for TaskFlow Pro
"""
import asyncio
import sys
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def create_admin_user():
    # Database connection using environment variables
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Admin user details
    admin_email = "admin@taskflow.com"
    admin_username = "admin"
    admin_password = "admin123!A"  # Strong password for security
    admin_full_name = "TaskFlow Admin"
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"email": admin_email})
    if existing_admin:
        print(f"✅ Admin user already exists!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        client.close()
        return
    
    # Hash password
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": admin_email,
        "username": admin_username,
        "full_name": admin_full_name,
        "role": "admin",
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True,
        "avatar_url": None,
        "preferences": {},
        "team_ids": [],
        "last_login": None
    }
    
    # Insert into database
    await db.users.insert_one(admin_user)
    
    print("🎉 Admin user created successfully!")
    print("=" * 50)
    print("ADMIN CREDENTIALS:")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print(f"Role: admin")
    print("=" * 50)
    print("\n📝 Instructions:")
    print("1. Go to the TaskFlow Pro login page")
    print("2. Use the credentials above to login") 
    print("3. Once logged in, navigate to /admin to access the admin panel")
    print("4. ⚠️  IMPORTANT: Change the password after first login for security!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())