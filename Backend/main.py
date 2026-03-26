import json
import time
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from .auth import (
        LoginRequest,
        TokenResponse,
        authenticate_user,
        create_access_token,
        get_current_user,
        require_roles,
        serialize_user,
        ROLE_ADMIN,
    )
    from .db import bootstrap_database, delete_document_record, log_query, store_document_record
    from .db import update_document_visibility as update_document_visibility_record
    from .rag import (
        EnterpriseRAGService,
        IngestResult,
        QueryResult,
        SourceItem,
        validate_visibility_scope,
    )
except ImportError:
    from auth import (
        LoginRequest,
        TokenResponse,
        authenticate_user,
        create_access_token,
        get_current_user,
        require_roles,
        serialize_user,
        ROLE_ADMIN,
    )
    from db import bootstrap_database, delete_document_record, log_query, store_document_record
    from db import update_document_visibility as update_document_visibility_record
    from rag import (
        EnterpriseRAGService,
        IngestResult,
        QueryResult,
        SourceItem,
        validate_visibility_scope,
    )

bootstrap_database()
rag_service = EnterpriseRAGService()

app = FastAPI(
    title="FindX Enterprise Agentic RAG API",
    description="FastAPI backend with JWT auth, RBAC, agentic retrieval orchestration, and role-based search over ChromaDB",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    chat_id: str | None = None
    doc_uuid: str | None = None
    chat_history: list[dict[str, Any]] = Field(default_factory=list)


class QueryResponse(BaseModel):
    answer: str
    explanation: str
    sources: list[SourceItem] = Field(default_factory=list)


class UploadResponse(BaseModel):
    message: str
    document_id: str
    document: str
    category: str
    sensitivity: str | None = None
    chunks_indexed: int


class VisibilityUpdateRequest(BaseModel):
    visibility_scope: str = Field(...)


def _format_file_size(byte_count: int) -> str:
    size = float(max(byte_count, 0))
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes)}m {remaining_seconds:04.1f}s"


def _resolve_query_scope(request: QueryRequest, current_user: dict[str, Any]) -> str | None:
    requested_chat_id = (request.chat_id or "").strip()
    current_role = current_user["role"]

    if current_role == ROLE_ADMIN:
        return requested_chat_id or str(current_user.get("id") or current_user["username"])

    allowed_scopes = {
        str(current_user.get("id") or "").strip(),
        str(current_user.get("username") or "").strip(),
        str(current_user.get("email") or "").strip(),
    }
    allowed_scopes.discard("")

    if requested_chat_id and requested_chat_id not in allowed_scopes:
        raise HTTPException(status_code=403, detail="You cannot query another user's workspace")

    return requested_chat_id or str(current_user.get("id") or current_user["username"])


def _build_upload_response(result: IngestResult) -> UploadResponse:
    return UploadResponse(
        message="Document uploaded and indexed successfully",
        document_id=result.document_id,
        document=result.document,
        category=result.category,
        sensitivity=result.sensitivity,
        chunks_indexed=result.chunks_indexed,
    )


@app.post("/login", response_model=TokenResponse)
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.principal, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")

    access_token = create_access_token(user)
    return TokenResponse(access_token=access_token, user=serialize_user(user))


@app.get("/me")
@app.get("/api/auth/me")
async def read_current_user(current_user: dict[str, Any] = Depends(get_current_user)):
    return serialize_user(current_user)


@app.post("/upload", response_model=UploadResponse)
@app.post("/api/upload/file", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("GENERAL"),
    sensitivity: str | None = Form(None),
    visibility_scope: str = Form("private"),
    session_id: str | None = Form(None),
    current_user: dict[str, Any] = Depends(require_roles(ROLE_ADMIN)),
):
    filename = file.filename or "uploaded-file"
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    upload_started_at = time.perf_counter()
    print(
        (
            f"[Upload] [{filename}] Received from {current_user['username']} | "
            f"size={_format_file_size(len(file_bytes))} | "
            f"category={category} | visibility={visibility_scope}"
        ),
        flush=True,
    )

    try:
        stored_path = rag_service.save_upload(filename, file_bytes)
        result = rag_service.ingest_document(
            file_path=stored_path,
            document_name=filename,
            category=category,
            sensitivity=sensitivity,
            visibility_scope=visibility_scope,
            uploaded_by=current_user["username"],
        )
    except ValueError as exc:
        print(
            f"[Upload] [{filename}] Rejected after {_format_duration(time.perf_counter() - upload_started_at)} | {exc}",
            flush=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(
            f"[Upload] [{filename}] Failed after {_format_duration(time.perf_counter() - upload_started_at)} | {exc}",
            flush=True,
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    store_document_record(
        document_id=result.document_id,
        document=result.document,
        category=result.category,
        sensitivity=result.sensitivity,
        visibility_scope=validate_visibility_scope(visibility_scope),
        uploaded_by=current_user["username"],
        chunks_indexed=result.chunks_indexed,
    )
    print(
        (
            f"[Upload] [{filename}] Completed in {_format_duration(time.perf_counter() - upload_started_at)} | "
            f"document_id={result.document_id} | chunks_indexed={result.chunks_indexed}"
        ),
        flush=True,
    )
    return _build_upload_response(result)


@app.patch("/api/documents/{document_id}/visibility")
async def update_document_visibility(
    document_id: str,
    request: VisibilityUpdateRequest,
    current_user: dict[str, Any] = Depends(require_roles(ROLE_ADMIN)),
):
    normalized_scope = validate_visibility_scope(request.visibility_scope)
    updated_in_index = rag_service.update_document_visibility(document_id, normalized_scope)
    updated_in_db = update_document_visibility_record(document_id, normalized_scope)

    if not updated_in_index and not updated_in_db:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "visibility_scope": normalized_scope,
        "message": "Document visibility updated successfully",
    }


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(require_roles(ROLE_ADMIN)),
):
    deleted_from_index = rag_service.delete_document(document_id)
    deleted_from_db = delete_document_record(document_id)

    if not deleted_from_index and not deleted_from_db:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "message": "Document deleted successfully",
    }


@app.post("/query", response_model=QueryResponse)
@app.post("/api/chat", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    log_query(
        username=current_user["username"],
        role=current_user["role"],
        query=request.query,
    )

    try:
        result = rag_service.query(
            request.query,
            role=current_user["role"],
            chat_id=_resolve_query_scope(request, current_user),
            doc_uuid=request.doc_uuid,
            chat_history=request.chat_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc

    return QueryResponse(
        answer=result.answer,
        explanation=result.explanation,
        sources=result.sources,
    )


@app.post("/api/chat/stream")
async def stream_query_documents(
    request: QueryRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    log_query(
        username=current_user["username"],
        role=current_user["role"],
        query=request.query,
    )

    try:
        stream = rag_service.stream_query(
            request.query,
            role=current_user["role"],
            chat_id=_resolve_query_scope(request, current_user),
            doc_uuid=request.doc_uuid,
            chat_history=request.chat_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc

    def iter_events():
        try:
            for event in stream:
                yield json.dumps(event) + "\n"
        except Exception as exc:
            yield json.dumps(
                {
                    "type": "error",
                    "detail": f"Query failed: {exc}",
                }
            ) + "\n"

    return StreamingResponse(
        iter_events(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}
