#!/usr/bin/env python3
"""
Create an admin user for TaskFlow Pro
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from datetime import datetime
import uuid

async def create_admin_user():
    # Database connection
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_database']
    
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
        await client.close()
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
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())