"""
Comprehensive debugging script to verify visibility data in both MongoDB and Chroma

Run this to see exactly how visibility is being stored and filtered
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timezone
try:
    from pymongo import MongoClient
    from chromadb import PersistentClient
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install pymongo chromadb")
    sys.exit(1)

# Import the RAG config
from rag import (
    ROLE_VISIBILITY_ACCESS,
    ROLE_ADMIN,
    ROLE_HR,
    ROLE_DEVELOPER,
    allowed_visibility_scopes_for_role,
    normalize_visibility_scope,
)
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "findx")

# Connect to MongoDB
mongo_client = MongoClient(MONGODB_URI)
mongo_db = mongo_client[MONGODB_DB_NAME]
documents_col = mongo_db["documents"]

# Connect to Chroma
chroma_client = PersistentClient(path=str(Path(__file__).parent / "chroma_db_storage"))
collection = chroma_client.get_or_create_collection("enterprise_chunks")

print("\n" + "="*80)
print("VISIBILITY DEBUGGING REPORT")
print("="*80)

# 1. Check Visibility Configuration
print("\n1. ROLE-BASED VISIBILITY CONFIGURATION")
print("-" * 80)
for role, scopes in ROLE_VISIBILITY_ACCESS.items():
    print(f"  {role:12} can access: {scopes}")

# 2. MongoDB Document Inventory
print("\n2. MONGODB DOCUMENTS INVENTORY")
print("-" * 80)
mongo_docs = list(documents_col.find({}, {"_id": 0}))
print(f"Total documents in MongoDB: {len(mongo_docs)}")

if mongo_docs:
    print("\nDocuments by visibility scope:")
    visibility_counts = {}
    for doc in mongo_docs:
        doc_id = doc.get("document_id", "UNKNOWN")
        vis_scope = doc.get("visibility_scope", "MISSING")
        visibility_counts[vis_scope] = visibility_counts.get(vis_scope, 0) + 1
        print(
            f"  {doc_id[:16]:16} | {vis_scope:10} | Category: {doc.get('category', 'UNKNOWN'):8} | "
            f"Chunks: {doc.get('chunks_indexed', 0)}"
        )
    
    print("\nVisibility scope distribution:")
    for vis_scope, count in sorted(visibility_counts.items()):
        print(f"  {vis_scope:12} : {count} document(s)")

# 3. Chroma Collection Inventory
print("\n3. CHROMA COLLECTION INVENTORY")
print("-" * 80)
try:
    # Get all items
    all_items = collection.get(include=["metadatas"])
    all_ids = all_items.get("ids") or []
    all_metadatas = all_items.get("metadatas") or []
    
    print(f"Total chunks in Chroma: {len(all_ids)}")
    
    if all_ids:
        # Analyze visibility in Chroma
        chroma_visibility_counts = {}
        document_visibility_map = {}
        
        for metadata in all_metadatas:
            if not metadata:
                continue
            
            doc_id = metadata.get("document_id", "UNKNOWN")
            vis_scope = metadata.get("visibility_scope", "MISSING")
            
            chroma_visibility_counts[vis_scope] = chroma_visibility_counts.get(vis_scope, 0) + 1
            
            if doc_id not in document_visibility_map:
                document_visibility_map[doc_id] = vis_scope
        
        print("\nChroma visibility scope distribution:")
        for vis_scope, count in sorted(chroma_visibility_counts.items()):
            print(f"  {vis_scope:12} : {count} chunk(s)")
        
        print("\nChroma documents by visibility:")
        for doc_id, vis_scope in sorted(document_visibility_map.items()):
            chunk_count = sum(1 for m in all_metadatas if m.get("document_id") == doc_id)
            print(f"  {doc_id[:16]:16} | {vis_scope:10} | {chunk_count:4} chunks")
except Exception as e:
    print(f"ERROR reading Chroma: {e}")

# 4. MongoDB vs Chroma Comparison
print("\n4. MONGODB vs CHROMA DATA CONSISTENCY")
print("-" * 80)

if mongo_docs and all_metadatas:
    mongo_doc_ids = {doc.get("document_id") for doc in mongo_docs if doc.get("document_id")}
    chroma_doc_ids = {m.get("document_id") for m in all_metadatas if m and m.get("document_id")}
    
    print(f"Documents only in MongoDB: {mongo_doc_ids - chroma_doc_ids}")
    print(f"Documents only in Chroma: {chroma_doc_ids - mongo_doc_ids}")
    
    print("\nVisibility scope consistency check:")
    for doc_id in mongo_doc_ids & chroma_doc_ids:
        mongo_doc = next((d for d in mongo_docs if d.get("document_id") == doc_id), None)
        mongo_vis = mongo_doc.get("visibility_scope", "MISSING") if mongo_doc else "NOT_FOUND"
        
        chroma_chunks = [m for m in all_metadatas if m and m.get("document_id") == doc_id]
        chroma_vis = chroma_chunks[0].get("visibility_scope", "MISSING") if chroma_chunks else "NO_CHUNKS"
        
        status = "✓" if mongo_vis == chroma_vis else "✗ MISMATCH"
        print(f"  {status} {doc_id[:16]:16} | MongoDB: {mongo_vis:10} | Chroma: {chroma_vis:10}")

# 5. Role-Based Access Simulation
print("\n5. ROLE-BASED ACCESS SIMULATION")
print("-" * 80)

test_roles = [ROLE_DEVELOPER, ROLE_HR, ROLE_ADMIN]

for role in test_roles:
    allowed_scopes = allowed_visibility_scopes_for_role(role)
    print(f"\nRole: {role}")
    print(f"  Allowed visibility scopes: {allowed_scopes}")
    print(f"  Normalized: {sorted({scope.lower() for scope in allowed_scopes})}")
    
    # Simulate filtering from MongoDB
    if mongo_docs:
        accessible_docs = [
            doc.get("document_id") for doc in mongo_docs
            if doc.get("visibility_scope", "private").lower() in {s.lower() for s in allowed_scopes}
        ]
        print(f"  Accessible documents from MongoDB: {len(accessible_docs)}")
        for doc_id in accessible_docs[:3]:
            print(f"    - {doc_id}")
        if len(accessible_docs) > 3:
            print(f"    ... and {len(accessible_docs) - 3} more")

# 6. Chroma WHERE Filter Test
print("\n6. CHROMA WHERE FILTER TEST")
print("-" * 80)

test_filters = [
    ("Developer documents", {"visibility_scope": {"$in": ["developer", "both"]}}),
    ("HR documents", {"visibility_scope": {"$in": ["hr", "both"]}}),
    ("Private documents", {"visibility_scope": {"$in": ["private"]}}),
]

for filter_name, where_filter in test_filters:
    print(f"\nFilter: {filter_name}")
    print(f"  WHERE clause: {where_filter}")
    try:
        results = collection.get(where=where_filter, include=["metadatas"])
        result_ids = results.get("ids") or []
        result_metadatas = results.get("metadatas") or []
        print(f"  Chroma returned: {len(result_ids)} chunk(s)")
        
        if result_ids:
            # Show sample of results
            for i, metadata in enumerate(result_metadatas[:3]):
                if metadata:
                    print(f"    [{i+1}] {metadata.get('document_id')} visibility={metadata.get('visibility_scope')}")
            if len(result_ids) > 3:
                print(f"    ... and {len(result_ids) - 3} more chunks")
    except Exception as e:
        print(f"  ERROR: {str(e)}")

# 7. Issue Diagnosis
print("\n7. POTENTIAL ISSUES IDENTIFIED")
print("-" * 80)

issues = []

# Check if documents have visibility_scope
if mongo_docs:
    docs_without_visibility = [d.get("document_id") for d in mongo_docs if "visibility_scope" not in d]
    if docs_without_visibility:
        issues.append(f"MongoDB: {len(docs_without_visibility)} document(s) missing visibility_scope field")

# Check if Chroma chunks have visibility_scope
if all_metadatas:
    chunks_without_visibility = sum(1 for m in all_metadatas if m and "visibility_scope" not in m)
    if chunks_without_visibility:
        issues.append(f"Chroma: {chunks_without_visibility} chunk(s) missing visibility_scope field")

# Check for type mismatches
if all_metadatas and mongo_docs:
    visibility_types_mongo = set()
    visibility_types_chroma = set()
    
    for doc in mongo_docs:
        vis = doc.get("visibility_scope")
        if vis is not None:
            visibility_types_mongo.add(type(vis).__name__)
    
    for metadata in all_metadatas:
        if metadata:
            vis = metadata.get("visibility_scope")
            if vis is not None:
                visibility_types_chroma.add(type(vis).__name__)
    
    if visibility_types_mongo != visibility_types_chroma:
        issues.append(
            f"Type mismatch: MongoDB has {visibility_types_mongo}, Chroma has {visibility_types_chroma}"
        )

if issues:
    print("\nIssues found:")
    for i, issue in enumerate(issues, 1):
        print(f"  [{i}] {issue}")
else:
    print("✓ No obvious issues found in data consistency")

print("\n" + "="*80)
print("END OF REPORT")
print("="*80 + "\n")
