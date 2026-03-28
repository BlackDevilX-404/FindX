import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

try:
    from .auth import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_HR, hash_password
except ImportError:
    from auth import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_HR, hash_password

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "findx")

client = MongoClient(MONGODB_URI)
db: Database = client[MONGODB_DB_NAME]

users_col: Collection = db["users"]
documents_col: Collection = db["documents"]
query_logs_col: Collection = db["query_logs"]

LEGACY_USER_MAPPING = {
    "admin@findx.ai": {"username": "admin", "role": ROLE_ADMIN},
    "hr@findx.ai": {"username": "hr", "role": ROLE_HR},
    "employee@findx.ai": {
        "username": "developer",
        "role": ROLE_DEVELOPER,
        "email": "developer@findx.ai",
        "id": "developer-user",
    },
    "developer@findx.ai": {"username": "developer", "role": ROLE_DEVELOPER},
}


def ensure_indexes() -> None:
    users_col.create_index([("username", ASCENDING)], unique=True)
    users_col.create_index([("email", ASCENDING)], unique=True)
    documents_col.create_index([("document_id", ASCENDING)], unique=True)
    documents_col.create_index([("category", ASCENDING)])
    documents_col.create_index([("uploaded_by", ASCENDING)])
    documents_col.create_index([("system_id", ASCENDING)])
    documents_col.create_index([("system_id", ASCENDING), ("uploaded_by", ASCENDING)])
    query_logs_col.create_index([("username", ASCENDING)])
    query_logs_col.create_index([("timestamp", DESCENDING)])


def migrate_legacy_users() -> None:
    for email, updates in LEGACY_USER_MAPPING.items():
        users_col.update_many(
            {"email": email},
            {"$set": updates},
        )

    users_col.update_many(
        {"username": "developer"},
        {
            "$set": {
                "email": "developer@findx.ai",
                "id": "developer-user",
                "role": ROLE_DEVELOPER,
            }
        },
    )

    users_without_username = list(users_col.find({"username": {"$exists": False}}))
    for user in users_without_username:
        fallback_email = str(user.get("email", "")).strip().lower()
        fallback_username = fallback_email.split("@", 1)[0] if fallback_email else str(user.get("id") or user["_id"])
        users_col.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "username": fallback_username,
                    "role": user.get("role", ROLE_DEVELOPER),
                }
            },
        )


def _demo_users() -> list[dict[str, Any]]:
    return [
        {
            "id": "admin-user",
            "username": "admin",
            "email": "admin@findx.ai",
            "password": hash_password("admin123"),
            "role": ROLE_ADMIN,
        },
        {
            "id": "hr-user",
            "username": "hr",
            "email": "hr@findx.ai",
            "password": hash_password("hr123"),
            "role": ROLE_HR,
        },
        {
            "id": "developer-user",
            "username": "developer",
            "email": "developer@findx.ai",
            "password": hash_password("developer123"),
            "role": ROLE_DEVELOPER,
        },
    ]


def seed_demo_users() -> None:
    for user in _demo_users():
        users_col.update_one(
            {"username": user["username"]},
            {"$setOnInsert": user},
            upsert=True,
        )


def store_document_record(
    document_id: str,
    document: str,
    category: str,
    sensitivity: str | None,
    visibility_scope: str,
    uploaded_by: str,
    chunks_indexed: int,
    system_id: str,
) -> None:
    documents_col.update_one(
        {"document_id": document_id},
        {
            "$set": {
                "document_id": document_id,
                "document": document,
                "category": category,
                "sensitivity": sensitivity,
                "visibility_scope": visibility_scope,
                "uploaded_by": uploaded_by,
                "chunks_indexed": chunks_indexed,
                "system_id": system_id,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "created_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )


def update_document_visibility(document_id: str, visibility_scope: str) -> bool:
    result = documents_col.update_one(
        {"document_id": document_id},
        {
            "$set": {
                "visibility_scope": visibility_scope,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    
    if result.matched_count == 0:
        print(f"[DB Warning] Document {document_id} not found for visibility update", flush=True)
        return False
    
    if result.modified_count == 0:
        print(f"[DB Info] Document {document_id} visibility already set to '{visibility_scope}'", flush=True)
        return True
    
    # Verify the update was successful
    updated_doc = documents_col.find_one({"document_id": document_id})
    if updated_doc and updated_doc.get("visibility_scope") == visibility_scope:
        print(f"[DB] Document {document_id} visibility confirmed updated to '{visibility_scope}'", flush=True)
        return True
    else:
        print(
            f"[DB ERROR] Failed to verify visibility update for document {document_id}. "
            f"Expected '{visibility_scope}' but got '{updated_doc.get('visibility_scope') if updated_doc else 'NOT FOUND'}'",
            flush=True
        )
        return False


def delete_document_record(document_id: str) -> bool:
    result = documents_col.delete_one({"document_id": document_id})
    return result.deleted_count > 0


def list_document_records(system_id: str | None = None) -> list[dict[str, Any]]:
    """
    List document records, optionally filtered by system_id.
    
    Args:
        system_id: Optional system identifier to filter documents. If provided,
                  only documents uploaded from that system are returned.
    
    Returns:
        List of document records matching the criteria.
    """
    query = {}
    if system_id:
        query["system_id"] = system_id
    return list(documents_col.find(query, {"_id": 0}))


def log_query(username: str, role: str, query: str) -> None:
    query_logs_col.insert_one(
        {
            "username": username,
            "role": role,
            "query": query,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def bootstrap_database() -> None:
    migrate_legacy_users()
    ensure_indexes()
    seed_demo_users()
