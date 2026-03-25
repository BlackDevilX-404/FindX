# FindX
<<<<<<< HEAD
An AI-powered enterprise search system that understands natural language queries and delivers accurate, context-aware answers from internal company documents using Retrieval-Augmented Generation (RAG).
=======

FindX is an enterprise RAG prototype with a FastAPI backend and a React frontend. It combines JWT authentication, MongoDB-based user storage, ChromaDB vector search, sentence-transformer embeddings, and Groq-powered answer generation.

The current system focuses on:

- secure login with roles
- role-based access control at the API layer
- role-based search inside retrieval
- grounded answers with evidence snippets
- a minimal ChatGPT-style dark frontend

## 1. What This Project Does

FindX lets authenticated users search only the documents they are allowed to access.

There are three roles:

- `Admin`
- `HR`
- `Developer`

The main behavior is:

1. A user logs in and receives a JWT token.
2. The backend reads the role from the token.
3. The role is mapped to allowed document categories.
4. ChromaDB retrieval is filtered so unauthorized chunks are never sent to the LLM.
5. Groq generates an answer only from authorized retrieved context.
6. The frontend shows the answer plus evidence snippets in a right-hand sidebar.

## 2. Tech Stack

### Backend

- FastAPI
- MongoDB
- ChromaDB
- sentence-transformers
- LangChain Groq integration
- PyMuPDF
- PyJWT

### Frontend

- React
- Vite
- Tailwind CSS v4

### Model and Retrieval

- Embedding model: `sentence-transformers/all-mpnet-base-v2`
- LLM provider: Groq
- Default LLM: `llama-3.3-70b-versatile`

## 3. Core Features

- JWT authentication
- seeded demo users
- RBAC for upload and query endpoints
- RBS through category-based Chroma filters
- grounded answer generation
- source snippets returned to the UI
- query logging in MongoDB
- legacy per-workspace compatibility search
- simple ChatGPT-inspired dark UI
- evidence viewer sidebar
- collapsible history and ingest sidebar
- optional browser microphone input

## 4. Architecture Overview

### High-Level Flow

```text
React UI
  -> login / upload / chat requests
FastAPI
  -> auth validation
  -> RBAC enforcement
  -> RAG retrieval
MongoDB
  -> users
  -> document records
  -> query logs
ChromaDB
  -> vector chunks with metadata
Groq LLM
  -> grounded answer from retrieved context only
```

### Request Flow for `/api/chat`

1. Frontend sends `query`, `chat_id`, and `chat_history`.
2. FastAPI validates the JWT.
3. Backend resolves the user scope.
4. Backend maps role to allowed categories.
5. ChromaDB is queried with a category filter.
6. Retrieved chunks are ranked.
7. If enterprise chunks are unavailable, the backend may use the legacy workspace store as a compatibility fallback.
8. The LLM receives only the selected authorized context.
9. Backend returns:

```json
{
  "answer": "string",
  "explanation": "string",
  "sources": [
    {
      "document": "string",
      "snippet": "string",
      "page": 1,
      "confidence": "50%"
    }
  ]
}
```

## 5. Repository Structure

```text
FindX/
|- Backend/
|  |- main.py
|  |- server.py
|  |- auth.py
|  |- db.py
|  |- rag.py
|  |- pdf_chroma_ingest.py
|  |- pdf_ppt_extract.py
|  |- process_ppt.py
|  |- orchestrate.py
|  |- orchestarte.py
|  |- downloads/
|  |- jsons/
|  `- chroma_db_storage/
|- Frontend/
|  |- src/
|  |  |- App.jsx
|  |  |- index.css
|  |  |- main.jsx
|  |  |- lib/api.js
|  |  |- config/api.js
|  |  |- data/mockData.js
|  |  `- components/
|  `- package.json
|- requirements.txt
`- README.md
```

## 6. Backend Module Guide

### `Backend/main.py`

Primary FastAPI entrypoint.

Responsibilities:

- bootstraps the database
- creates the RAG service
- exposes auth, upload, query, and health endpoints
- enforces role checks
- resolves query scope for authenticated users

Main routes:

- `POST /login`
- `POST /api/auth/login`
- `GET /me`
- `GET /api/auth/me`
- `POST /upload`
- `POST /api/upload/file`
- `POST /query`
- `POST /api/chat`
- `GET /health`

### `Backend/server.py`

Compatibility entrypoint:

```python
from main import app
```

Use this if you want to keep older run commands such as:

```bash
uvicorn server:app --reload
```

### `Backend/auth.py`

Authentication and authorization layer.

Responsibilities:

- password hashing with PBKDF2
- password verification
- JWT token creation
- JWT decoding
- current-user dependency
- reusable role guard with `require_roles(...)`

Defined roles:

- `Admin`
- `HR`
- `Developer`

### `Backend/db.py`

MongoDB integration layer.

Collections:

- `users`
- `documents`
- `query_logs`

Responsibilities:

- create indexes
- migrate legacy user records
- seed demo users
- store uploaded document records
- log all search queries

### `Backend/rag.py`

Main enterprise RAG service.

Responsibilities:

- validate document categories
- map roles to allowed categories
- chunk and embed uploaded PDFs/PPTs
- store enterprise chunks in ChromaDB
- query enterprise chunks using category filters
- rank chunks
- gate weak results
- call Groq with authorized context only
- return structured answer, explanation, and sources

### `Backend/pdf_chroma_ingest.py`

Legacy workspace retrieval support.

Responsibilities:

- read JSON-extracted PDF text
- store per-workspace chunks in a legacy Chroma collection
- rank and return chunks from older collections
- recover readable source names
- recover page numbers from legacy metadata
- expand heading-only matches into richer page-level snippets

This module is useful because some older uploaded data exists in collections such as `chat_hr-user`.

### `Backend/pdf_ppt_extract.py`

PDF to JSON extractor using PyMuPDF and Pillow.

Responsibilities:

- read each page
- extract text
- extract images
- save JSON to `Backend/jsons/`
- save images to `Backend/jsons/ExtractedImages/`

### `Backend/process_ppt.py`

Converts PowerPoint files to PDF using Aspose Slides before chunking and ingestion.

### `Backend/orchestrate.py` and `Backend/orchestarte.py`

Older orchestration code paths kept in the repo for legacy use and compatibility. The current enterprise backend path is centered on:

- `main.py`
- `auth.py`
- `db.py`
- `rag.py`

## 7. Frontend Module Guide

The frontend is a single-page React app with a dark minimal UI inspired by ChatGPT.

### `Frontend/src/App.jsx`

Application shell and state manager.

Responsibilities:

- restores auth state from local storage
- handles login/logout
- stores frontend chat history per user
- submits chat requests to the backend
- opens and closes both sidebars
- normalizes returned sources
- controls upload state and document state

### `Frontend/src/lib/api.js`

Frontend API client wrapper.

Responsibilities:

- builds backend URLs
- stores JWT in local storage
- calls login
- fetches current user
- sends chat messages
- uploads files

### `Frontend/src/config/api.js`

API base URL configuration:

```js
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
```

### `Frontend/src/components/LoginPage.jsx`

Simple login screen with:

- email field
- password field
- sign-in button
- demo email buttons

### `Frontend/src/components/Navbar.jsx`

Minimal top bar with:

- `New chat`
- `Logout`

### `Frontend/src/components/AccessSidebar.jsx`

Left sidebar.

Contains:

- conversation history
- `+ New chat`
- content ingest panel
- close button

### `Frontend/src/components/SourceViewer.jsx`

Right sidebar for evidence.

Displays:

- document title
- page
- confidence
- retrieved snippet

### `Frontend/src/components/ChatWindow.jsx`

Centered message area with:

- user and assistant messages
- citations
- suggested queries
- typing indicator

### `Frontend/src/components/InputBox.jsx`

Composer with:

- textarea
- send button
- microphone icon
- browser speech-recognition support if available

### `Frontend/src/components/AdminDashboard.jsx`

Admin-only document management screen.

Supports:

- listing files
- upload controls
- visibility changes
- deletion
- basic file stats

### `Frontend/src/data/mockData.js`

Frontend helper data used for:

- demo account shortcuts
- visibility labels
- initial local document list
- suggested questions
- welcome chat seed
- local-only chat history behavior

Important note:

- The actual answer generation now comes from the backend.
- Some UI document state is still partially mocked/local for convenience.

## 8. RBAC Design

RBAC is enforced before request processing.

### Rules

- `Admin`
  - can upload documents
  - can query documents
  - can view all categories
- `HR`
  - cannot upload through the protected backend endpoint
  - can query allowed categories
- `Developer`
  - cannot upload through the protected backend endpoint
  - can query allowed categories

### Endpoint Permissions

| Endpoint | Access |
|---|---|
| `POST /login` | public |
| `GET /me` | authenticated |
| `POST /upload` | admin only |
| `POST /query` | authenticated |

### Enforcement

RBAC is implemented with:

- `get_current_user()`
- `require_roles(...)`

Unauthorized requests return:

- `401` for missing or invalid token
- `403` for forbidden access

## 9. Role-Based Search Design

RBS is the data-level security layer inside retrieval.

### Allowed Categories

| Role | Allowed Categories |
|---|---|
| `Admin` | `HR`, `TECH`, `FINANCE`, `GENERAL` |
| `HR` | `HR`, `GENERAL` |
| `Developer` | `TECH`, `GENERAL` |

### Enterprise Document Metadata

Each enterprise chunk stores metadata shaped like:

```json
{
  "document_id": "uuid",
  "document": "Benefits_Handbook.pdf",
  "category": "HR",
  "sensitivity": "confidential",
  "page": 6,
  "uploaded_by": "admin"
}
```

### Retrieval Filter

The backend filters ChromaDB with:

```python
where = {
    "category": {"$in": allowed_categories}
}
```

### Security Guarantee

- unauthorized categories are excluded before ranking
- unauthorized chunks are never sent to the LLM
- if nothing useful is found, the user gets a safe fallback

Safe fallback:

```text
No accessible data found for your role
```

## 10. Legacy Compatibility Path

This project currently supports two retrieval paths:

### Enterprise path

- collection: `enterprise_chunks`
- category-aware
- preferred path

### Legacy path

- collections like `chat_hr-user`
- older workspace-based chunk storage
- used only when enterprise chunks are missing for a query scope

This was added so existing indexed content does not instantly break while the system moves to the enterprise RBAC/RBS design.

## 11. Prompting Strategy

### Backend Answer Prompt

The backend prompt strategy in `Backend/rag.py` is intentionally strict:

- answer only from retrieved context
- say clearly when context is insufficient
- do not invent policy details
- keep answers concise

In practice, the LLM is given:

1. the user question
2. only the authorized retrieved snippets
3. instructions to ground the answer entirely in those snippets

### Frontend Design Prompt

The frontend was shaped around a simple, minimal, ChatGPT-like brief:

```text
Create a black, minimal chat UI similar in feel to ChatGPT.
Keep the login screen very simple with only email and password.
Show demo email shortcuts.
On the chat page, keep only New chat and Logout in the navbar.
Use a left sidebar for history and content ingest.
Use a right sidebar for evidence.
Make both sidebars collapsible.
Keep the center focused on the conversation.
Replace the Mic text with a microphone icon.
Avoid clutter, large dashboard cards, and extra control boxes.
```

### Why This Prompt Matters

This prompt explains the current frontend direction:

- dark theme
- low visual noise
- centered chat
- evidence-first explainability
- minimal actions

## 12. Frontend UX Details

### Visual Style

- dark theme
- background `#212121`
- card surfaces around `#171717` and `#212121`
- simple rounded panels
- minimal chrome
- no marketing-style hero sections

### Layout

- top navbar
- left collapsible sidebar for history and ingest
- centered chat conversation
- right collapsible evidence viewer

### Login UX

- simple form
- clear demo entry points
- direct error message display

### Chat UX

- user message bubble on the right
- assistant messages centered in the main feed
- citation chips below assistant response
- explanation text below answer
- evidence opens in the right sidebar

### Admin UX

- document list
- upload
- visibility changes
- delete action
- summary cards for file counts

## 13. API Reference

### `POST /api/auth/login`

Request:

```json
{
  "email": "hr@findx.ai",
  "password": "hr123"
}
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": "hr-user",
    "username": "hr",
    "role": "HR",
    "email": "hr@findx.ai"
  }
}
```

### `GET /api/auth/me`

Headers:

```text
Authorization: Bearer <token>
```

Response:

```json
{
  "id": "hr-user",
  "username": "hr",
  "role": "HR",
  "email": "hr@findx.ai"
}
```

### `POST /api/upload/file`

Admin only.

Multipart form fields:

- `file`
- `category`
- `sensitivity`
- `session_id`

Response:

```json
{
  "message": "Document uploaded and indexed successfully",
  "document_id": "uuid",
  "document": "Benefits_Handbook.pdf",
  "category": "HR",
  "sensitivity": "confidential",
  "chunks_indexed": 24
}
```

### `POST /api/chat`

Request:

```json
{
  "query": "Summarize the maternity leave eligibility rule.",
  "chat_id": "hr-user",
  "doc_uuid": null,
  "chat_history": []
}
```

Response:

```json
{
  "answer": "string",
  "explanation": "string",
  "sources": [
    {
      "document": "Benefits_Handbook.pdf",
      "snippet": "Maternity leave is available...",
      "page": 6,
      "confidence": "94%"
    }
  ]
}
```

### `GET /health`

Response:

```json
{
  "status": "ok",
  "message": "Backend is running"
}
```

## 14. Local Setup

### Prerequisites

- Python 3.11+ or 3.12
- Node.js 18+
- MongoDB running locally or remotely
- Groq API key

### Backend Setup

From the repo root:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `Backend/.env` based on:

```env
GROQ_API_KEY=replace-with-your-groq-key
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DB_NAME=findx
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

Run the backend:

```bash
cd Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Compatibility run command:

```bash
cd Backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd Frontend
npm install
npm run dev
```

Optional frontend API override:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Production Build

```bash
cd Frontend
npm run build
```

## 15. Demo Credentials

The backend seeds these users automatically if they do not exist:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@findx.ai` | `admin123` |
| HR | `hr@findx.ai` | `hr123` |
| Developer | `developer@findx.ai` | `developer123` |

## 16. Data Stores

### MongoDB

Used for:

- users
- document records
- query logs

### ChromaDB

Used for:

- enterprise chunk embeddings
- legacy workspace chunk embeddings

### Local Filesystem

Used for:

- uploaded source files in `Backend/downloads/`
- extracted JSON in `Backend/jsons/`
- extracted images in `Backend/jsons/ExtractedImages/`

## 17. Logging

Every query is recorded in MongoDB as:

```json
{
  "username": "hr",
  "role": "HR",
  "query": "Summarize the maternity leave eligibility rule.",
  "timestamp": "UTC datetime"
}
```

## 18. Important Implementation Notes

- The enterprise RBAC/RBS backend is the main path.
- Some frontend document management behavior still uses local mock state for convenience.
- The upload UI does not yet fully expose backend category selection in an enterprise-perfect way.
- Legacy content can still be searched if enterprise chunks are unavailable.
- If the indexed data itself is unrelated, retrieval will still return "No accessible data found for your role."

## 19. Known Limitations

- frontend document state is not fully backend-driven
- legacy and enterprise retrieval coexist during migration
- upload flow needs stronger category wiring from the frontend
- there is no full admin user-management panel yet
- document deletion currently affects frontend state, not a full backend governance lifecycle
- source confidence is a retrieval heuristic, not a calibrated probability

## 20. Recommended Next Improvements

- wire category and sensitivity controls directly into the upload API from the frontend
- replace local document state with real backend document CRUD
- add reranking
- add document ownership and delete APIs in the backend
- add admin user management endpoints
- add ingestion status tracking
- add audit views for query logs
- add tests for auth, RBAC, and retrieval filters

## 21. Verification Commands

Useful commands used during development:

```bash
python -m py_compile Backend/main.py Backend/rag.py Backend/auth.py Backend/db.py Backend/pdf_chroma_ingest.py
```

```bash
cd Frontend
npm run build
```

## 22. Security Notes

- never commit a real `GROQ_API_KEY`
- use a strong random `JWT_SECRET`
- rotate any exposed key immediately
- keep `.env` out of version control
- enforce RBAC before processing uploads or queries
- enforce RBS before sending any context to the LLM

## 23. Current Project Status

The project is already functional as an enterprise RAG prototype with:

- login
- role-aware search
- grounded answers
- evidence display
- admin upload flow
- query logging

The best next milestone is to finish the migration from partially local frontend document state to a fully backend-driven document lifecycle.
>>>>>>> 79fd667 (Bibin, refined rag approach with chatgpt clean theme)
