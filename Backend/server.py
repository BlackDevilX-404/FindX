import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
    serialize_user,
)
from db import bootstrap_database, sessions_col
from pdf_chroma_ingest import ChromaMultimodalDB
from process_ppt import Ppt2Pdf
from pdf_ppt_extract import Pdf2Json
# Import LangChain message types to format history for the ReAct loop
from langchain_core.messages import HumanMessage, AIMessage
# Import your custom Orchestrator
from orchestarte import QueryOrchestrator

video_extensions: list[str] = []

# 1. Initialize FastAPI App
app = FastAPI(
    title="Hackastorm Enterprise Search API",
    description="Agentic RAG Backend",
    version="1.0.0"
)

# 2. Add CORS Middleware (CRITICAL for hackathons)
# This allows your React/Flutter frontend to talk to this backend running on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=False,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

UPLOAD_DIR = "downloads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
bootstrap_database()



# 3. Initialize the AI Orchestrator globally
# Doing this here means it only loads once when the server starts, not on every request.
print("Initializing Agentic Orchestrator...")
try:
    orchestrator = QueryOrchestrator()
    print("Orchestrator initialized successfully with Groq!")
except Exception as e:
    print(f"Failed to initialize orchestrator: {e}")
    orchestrator = None


# 4. Define Request & Response Schemas (For Frontend communication)
class Message(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="The text content of the message")

class ChatRequest(BaseModel):
    query: str = Field(..., example="What is the remote work policy?")
    chat_id: str = Field(default="default_session", example="user_123_session")
    doc_uuid: Optional[str] = Field(default=None, description="Optional: ID of a specific document to search")
    chat_history: List[Message] = Field(default=[], description="Previous conversation context")

class ChatResponse(BaseModel):
    answer: str
    status: str = "success"


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    print(f"[Auth] Login request received for: {request.email}")
    user = authenticate_user(request.email, request.password)
    if not user:
        print(f"[Auth] Login failed for: {request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user)
    print(f"[Auth] Login successful for: {request.email}")
    return TokenResponse(access_token=access_token, user=serialize_user(user))


@app.get("/api/auth/me")
async def read_current_user(current_user=Depends(get_current_user)):
    print(f"[Auth] Session restored for: {current_user['email']}")
    return serialize_user(current_user)




def process_pdf_ppt_pipeline(session_id, user_email, input_path, ext, original_name):
    filename = os.path.basename(input_path) # System UUID
    file_size = os.path.getsize(input_path) if os.path.exists(input_path) else 0
    
    # 1. Ingest
    print(f"[Upload] Extraction started for file: {original_name}")
    Pdf2Json(filename).extract()
    print("[Upload] Extraction completed successfully.")
    print("[Upload] Starting text ingestion...")
    ChromaMultimodalDB(session_id, filename).ingest_text()
    print("[Upload] Text ingestion completed successfully.")
    
    msg_text = "Document Uploaded Successfully..."
    
    # 2. Create the "Card" Message
    user_file_msg = {
        "role": "user",
        "text": f"Uploaded: {original_name}",
        "file": {
            "name": original_name, 
            "size": file_size, 
            "type": "application/pdf"
        },
        "time": datetime.utcnow()
    }
    
    # 3. Update DB (FIXED: Added "name": filename back)
    sessions_col.update_one(
        {"_id": session_id},
        {
            "$push": {
                "files": {
                    "name": filename,         # <--- RESTORED THIS (Prevents KeyError)
                    "system_name": filename, 
                    "user_name": original_name, 
                    "ext": ext
                },
                "messages": {
                    "$each": [
                        user_file_msg,
                        {"role": "assistant", "text": msg_text, "time": datetime.utcnow()}
                    ]
                }
            }
        }
    )
    return msg_text


def build_document_response(filename, original_name, ext, current_user, summary):
    visibility_scope = "both" if current_user["role"] == "Admin" else ("hr" if current_user["role"] == "HR" else "employee")
    return {
        "id": filename,
        "doc_uuid": filename,
        "name": original_name,
        "type": ext.replace(".", "").upper(),
        "ownerId": current_user["id"],
        "ownerName": current_user["name"],
        "uploadedAt": datetime.utcnow().isoformat(),
        "visibilityScope": visibility_scope,
        "summary": summary,
    }
# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload/file")
def upload_file(session_id: str = Form(...), file: UploadFile = File(...), current_user=Depends(get_current_user)):
    print(f"[Upload] Upload request received from {current_user['email']} for file: {file.filename}")
    session = sessions_col.find_one({"_id": session_id, "user_email": current_user["email"]})
    if not session:
        print(f"[Upload] No session found. Creating session: {session_id}")
        sessions_col.update_one(
            {"_id": session_id},
            {
                "$setOnInsert": {
                    "_id": session_id,
                    "user_email": current_user["email"],
                    "user_id": current_user["id"],
                    "messages": [],
                    "files": [],
                    "created_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
    
    ext = os.path.splitext(file.filename)[1].lower()
    original_name = file.filename # Capture the original name
    
    path = os.path.join(UPLOAD_DIR,f"{uuid.uuid4()}{ext}")
    
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)
    print(f"[Upload] File saved successfully: {path}")

    if ext in [".pdf",".ppt",".pptx"]:
        base_path = os.path.splitext(path)[0]
        
        if ext != ".pdf":
            # Convert PPT to PDF
            print("[Upload] PPT detected. Starting PPT to PDF conversion...")
            Ppt2Pdf(base_path, ext[1:]).convert_ppt_to_pdf()
            print("[Upload] PPT to PDF conversion completed successfully.")
        
        # Pass original_name to pipeline
        summary = process_pdf_ppt_pipeline(session_id, current_user["email"], base_path, ext, original_name)
    
    else:
        raise HTTPException(400,"Unsupported")

    print(f"[Upload] Upload pipeline completed for file: {original_name}")
    return {
        "summary": summary,
        "document": build_document_response(
            filename=os.path.basename(os.path.splitext(path)[0]),
            original_name=original_name,
            ext=ext,
            current_user=current_user,
            summary=summary,
        ),
    }
# 5. The Main Chat Endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user=Depends(get_current_user)):
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="AI Orchestrator is not initialized. Check API keys.")

    try:
        print(f"[Chat] Query received from {current_user['email']}: {request.query}")
        resolved_chat_id = (
            request.chat_id
            if request.chat_id and request.chat_id != "default_session"
            else current_user["email"]
        )

        # Step A: Convert the frontend JSON history into LangChain Message Objects
        formatted_history = []
        for msg in request.chat_history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted_history.append(AIMessage(content=msg.content))

        # Step B: Pass everything to the ReAct Agent
        # Because we are using Groq, this call will execute multiple reasoning steps internally very fast
        print("[Chat] Retrieval and generation started...")
        final_answer = orchestrator.answer(
            user_query=request.query,
            chat_id=resolved_chat_id,
            doc_uuid=request.doc_uuid,
            chat_history=formatted_history
        )
        print("[Chat] Answer generated successfully.")

        # Step C: Return the string to the frontend
        return ChatResponse(answer=final_answer)

    except Exception as e:
        # Catch any rate limit errors or Groq crashes so the server doesn't die
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")


# 6. A simple Health Check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}
