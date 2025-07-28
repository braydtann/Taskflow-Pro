#!/usr/bin/env python3
"""
Script to promote a user to project manager role
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

async def promote_user_to_pm():
    """Promote a user to project manager role"""
    
    # Database connection
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client.taskflow
    
    try:
        # Get email from command line argument
        if len(sys.argv) != 2:
            print("Usage: python promote_to_pm.py <user_email>")
            return
        
        user_email = sys.argv[1]
        
        # Find user by email
        user = await db.users.find_one({"email": user_email})
        if not user:
            print(f"❌ User with email {user_email} not found!")
            return
        
        # Update user role to project_manager
        await db.users.update_one(
            {"email": user_email},
            {"$set": {"role": "project_manager", "updated_at": "2024-01-01T00:00:00Z"}}
        )
        
        print(f"✅ User {user_email} promoted to Project Manager!")
        print(f"👤 User: {user['full_name']} ({user['username']})")
        print(f"🔄 Role updated from '{user['role']}' to 'project_manager'")
        print("\n🎯 The user can now:")
        print("- Access the PM Dashboard")
        print("- Manage projects they're assigned to")
        print("- View team workload and analytics")
        print("- Receive project notifications")
        
    except Exception as e:
        print(f"❌ Error promoting user: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(promote_user_to_pm())