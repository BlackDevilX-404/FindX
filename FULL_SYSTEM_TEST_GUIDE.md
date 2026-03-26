# FindX Full-System Test Guide

This guide covers end-to-end validation of the current FindX backend and frontend using the live API in `Backend/main.py` and the retrieval and verification pipeline in `Backend/rag.py`.

## 1. What To Validate

Use this guide to confirm that the current system works across:

- authentication
- RBAC and visibility enforcement
- upload and indexing
- grounded retrieval
- streamed responses
- follow-up rewriting
- exact-page retrieval
- verifier-driven refinement
- document visibility and delete behavior

This is the current meaning of "full agentic RAG" in FindX: scoped retrieval, retrieval planning, follow-up handling, page-aware lookup, verifier-backed final answers, and grounded responses with sources.

## 2. Prerequisites

Before testing, make sure:

- MongoDB is running
- `Backend/.env` contains a valid `GROQ_API_KEY`
- `Backend/.env` contains a valid `MONGODB_URI`
- `Backend/.env` contains a valid `JWT_SECRET`
- Python dependencies are installed in `.venv`
- frontend dependencies are installed in `Frontend/node_modules`

Seeded demo users come from `Backend/db.py`:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@findx.ai` | `admin123` |
| HR | `hr@findx.ai` | `hr123` |
| Developer | `developer@findx.ai` | `developer123` |

## 3. Start The System

### Backend

```powershell
cd e:\EASA\FindX\Backend
..\.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd e:\EASA\FindX\Frontend
npm run dev
```

### Health Check

```powershell
curl.exe -s http://localhost:8000/health
```

Expected result:

- backend responds successfully
- Mongo bootstrap has already seeded demo users if they were missing

## 4. Core Test Data

Upload these as `Admin` before running retrieval tests:

- one `HR` document with visibility `hr`
- one `TECH` document with visibility `developer`
- one `GENERAL` document with visibility `both`
- one optional large PDF to observe long-ingestion progress
- one optional document with known content on a specific page for exact-page validation

If you already have `ITC-Report-and-Accounts-2025.pdf` indexed, keep it for the page-specific test case.

## 5. Authentication And RBAC Checks

### Login

```powershell
$adminLogin = curl.exe -s -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@findx.ai","password":"admin123"}'

$hrLogin = curl.exe -s -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"hr@findx.ai","password":"hr123"}'

$developerLogin = curl.exe -s -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"developer@findx.ai","password":"developer123"}'
```

Check that all three responses contain:

- `access_token`
- `token_type`
- `user.role`

### Current User

```powershell
$adminToken = ($adminLogin | ConvertFrom-Json).access_token

curl.exe -s http://localhost:8000/api/auth/me `
  -H "Authorization: Bearer $adminToken"
```

Confirm the returned role matches the logged-in user.

### Role Enforcement

Use `HR` and `Developer` tokens against admin-only endpoints:

- `POST /api/upload/file`
- `PATCH /api/documents/{document_id}/visibility`
- `DELETE /api/documents/{document_id}`

Expected result:

- `HR` gets `403`
- `Developer` gets `403`

## 6. Upload And Ingestion Checks

### Upload A Small File

```powershell
curl.exe -s -X POST http://localhost:8000/api/upload/file `
  -H "Authorization: Bearer $adminToken" `
  -F "file=@e:\EASA\FindX\README.md" `
  -F "category=GENERAL" `
  -F "visibility_scope=both"
```

Confirm the response contains:

- `document_id`
- `document`
- `category`
- `chunks_indexed`

### Observe Large Upload Progress

Upload a large PDF and watch the backend terminal.

Expected terminal stages:

- `[Upload]`
- `[Ingest] [EXTRACT]`
- `[Ingest] [CHUNK]`
- `[Ingest] [INDEX]`
- `[Ingest] [DONE]`

Expected behavior:

- ingestion progress is visible in the backend terminal
- the upload request returns only after indexing completes

## 7. Retrieval And Streaming Checks

### Standard Query

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"Summarize the HR leave policy.","chat_history":[]}'
```

Confirm:

- `answer` is non-empty
- `sources` is non-empty for document-grounded queries
- the cited document and page match the uploaded content

### Streamed Query

```powershell
curl.exe -N -X POST http://localhost:8000/api/chat/stream `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"Summarize the HR leave policy.","chat_history":[]}'
```

Confirm:

- multiple `token` events appear before completion
- one final `final` event is sent
- the concatenated token text matches the final answer text

## 8. Agentic RAG Behavior Checks

### Follow-Up Rewrite

Run a first query:

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"Summarize the employee probation policy.","chat_history":[]}'
```

Then run a short follow-up with history:

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"what about extension?","chat_history":[{"role":"user","content":"Summarize the employee probation policy."},{"role":"assistant","content":"Previous grounded answer here."}]}'
```

Confirm:

- the second answer stays on the same topic
- retrieval remains grounded in the intended document area

### Exact-Page Retrieval

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"Explain page #205 in the ITC pdf.","chat_history":[]}'
```

Confirm one of these outcomes:

- returned sources include page `205`
- or the system states that page `205` is not indexed or has no extractable text

Reject this as a failure if:

- the answer is based on unrelated pages such as `132`, `216`, or `256`

### Verifier Refinement

Ask a vague but answerable question, for example:

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"What does the policy say about exceptions?","chat_history":[]}'
```

Watch the backend terminal for verifier logs:

- `[Verifier] [START]`
- `[Verifier] [RESULT]`
- `[Verifier] [REFINE]`
- `[Verifier] [FINAL]`

Confirm:

- the system may run one refinement round
- the final answer remains grounded
- the backend does not loop indefinitely

### Unsupported Question

Ask about content that is not present in any indexed document:

```powershell
curl.exe -s -X POST http://localhost:8000/api/chat `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"query":"What does the indexed data say about the Mars travel reimbursement policy?","chat_history":[]}'
```

Confirm:

- the system returns an insufficiency-style answer
- it does not fabricate unsupported details

## 9. Access-Control Regression Checks

Repeat targeted queries with `HR` and `Developer` tokens.

Confirm:

- `HR` cannot retrieve `developer`-only content
- `Developer` cannot retrieve `hr`-only content
- both roles can retrieve documents marked `both`
- `private` documents stay effectively admin-only

This must hold both for normal retrieval and for verifier-triggered refinement.

## 10. Visibility And Delete Checks

### Change Visibility

```powershell
curl.exe -s -X PATCH http://localhost:8000/api/documents/<document_id>/visibility `
  -H "Authorization: Bearer $adminToken" `
  -H "Content-Type: application/json" `
  -d '{"visibility_scope":"developer"}'
```

Confirm:

- the API returns success
- subsequent retrieval changes immediately for `HR` and `Developer`

### Delete A Document

```powershell
curl.exe -s -X DELETE http://localhost:8000/api/documents/<document_id> `
  -H "Authorization: Bearer $adminToken"
```

Confirm:

- the API returns success
- the deleted document no longer appears in `sources`
- document-specific queries against it fail safely

## 11. Acceptance Criteria

The system passes full-system testing when all of these are true:

- authorized users receive grounded answers with sources
- unauthorized content does not leak across roles
- upload and ingestion progress is visible in the backend terminal
- exact-page requests return the requested page or a precise insufficiency response
- the verifier can request at most one refinement round
- unsupported questions return insufficiency instead of hallucinated detail
- streamed responses produce valid `token` and `final` events
- visibility changes and deletes take effect in retrieval

## 12. Failure Signals To Watch For

Treat these as regressions:

- `500 Internal Server Error` on visibility updates or retrieval
- exact-page questions answering from the wrong page
- verifier logs showing repeated uncontrolled refinement
- answers with empty or irrelevant sources for grounded queries
- role-restricted content appearing for the wrong user
- upload requests returning before indexing is finished

## 13. Useful Local Checks

```powershell
python -m py_compile Backend/main.py Backend/rag.py Backend/auth.py Backend/db.py Backend/pdf_chroma_ingest.py
```

```powershell
cd e:\EASA\FindX\Frontend
npm run build
```
