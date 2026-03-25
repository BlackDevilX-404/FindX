import os
from typing import Any

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from auth import hash_password

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "findx")

client = MongoClient(MONGODB_URI)
db: Database = client[MONGODB_DB_NAME]

users_col: Collection = db["users"]
sessions_col: Collection = db["sessions"]
documents_col: Collection = db["documents"]


def ensure_indexes() -> None:
    users_col.create_index([("email", ASCENDING)], unique=True)
    sessions_col.create_index([("user_email", ASCENDING)])
    documents_col.create_index([("ownerId", ASCENDING)])


def _demo_users() -> list[dict[str, Any]]:
    return [
        {
            "id": "admin-user",
            "name": "Aarav Patel",
            "email": "admin@findx.ai",
            "password": hash_password("admin123"),
            "role": "Admin",
            "department": "Platform Security",
            "is_demo_user": True,
        },
        {
            "id": "hr-user",
            "name": "Meera Shah",
            "email": "hr@findx.ai",
            "password": hash_password("hr123"),
            "role": "HR",
            "department": "People Operations",
            "is_demo_user": True,
        },
        {
            "id": "employee-user",
            "name": "Rohan Singh",
            "email": "employee@findx.ai",
            "password": hash_password("employee123"),
            "role": "Employee",
            "department": "Product Design",
            "is_demo_user": True,
        },
    ]


def seed_demo_users() -> None:
    for user in _demo_users():
        users_col.update_one(
            {"email": user["email"]},
            {
                "$setOnInsert": user,
            },
            upsert=True,
        )


def bootstrap_database() -> None:
    ensure_indexes()
    seed_demo_users()


bootstrap_database()
