# FindX Project Presentation Guide

This version is intentionally short and presentation-ready. Use it to explain what FindX does, how it works, and why it is different from a basic RAG chatbot.

## 1. One-Line Pitch

FindX is a secure enterprise agentic RAG system that lets users query internal documents, get grounded answers with evidence, and retrieve exact pages when precision matters.

## 2. Problem and Solution

### Problem

Organizations store important knowledge in large PDFs, reports, policies, and internal files. Finding the right information is slow, and generic LLM chat is risky because it can ignore access control and produce unsupported answers.

### Solution

FindX combines:

- secure login and role handling
- access-aware retrieval
- agentic query planning
- exact-page lookup
- verifier-backed grounded answering

The result is a system that is not just smart, but also safer, more explainable, and more useful for enterprise document workflows.

## 3. Architecture

### High-Level Architecture

- `React` frontend for login, upload, chat, streaming responses, and evidence viewing
- `FastAPI` backend for auth, upload, retrieval orchestration, and chat APIs
- `MongoDB` for users, query logs, and document records
- `ChromaDB` for vector storage and metadata filtering
- `Sentence Transformers` for embeddings
- `Groq LLM` for query rewriting, retrieval guidance, grounding verification, and final answer generation

### Architecture Message To Say

"The frontend is the interaction layer, but the real intelligence is in the backend pipeline where access control, retrieval planning, verification, and answer generation happen together."

## 4. End-to-End Flow

### Upload Flow

1. Admin uploads a document.
2. Backend validates role and metadata.
3. File is stored locally.
4. Text is extracted and chunked.
5. Chunks are embedded and written to ChromaDB in batches.
6. Progress is printed in the terminal during extract, chunk, and index stages.

### Query Flow

1. User logs in and gets a JWT token.
2. Backend reads the role from the token.
3. Role is mapped to allowed categories and visibility scopes.
4. Query is classified as conversational or document-grounded.
5. If needed, the system rewrites short follow-up questions into clearer retrieval queries.
6. If the user asks for a specific page in a resolved document, the system retrieves that exact page first.
7. Otherwise, the backend runs retrieval planning and gathers evidence from accessible chunks only.
8. The LLM drafts an answer from authorized context.
9. A verifier checks whether the draft is actually supported.
10. If grounding is weak, one focused retrieval refinement can run.
11. The final verified answer is returned with sources.

## 5. Important Points To Highlight

### 1. Security Before Intelligence

FindX does not trust the model to enforce security by itself. Access control is applied before any context reaches the LLM.

Why it matters:

- prevents unauthorized data leakage
- makes the system realistic for enterprise use
- is stronger than plain semantic search chatbots

### 2. Agentic Retrieval, Not Single-Step RAG

This is not just upload, embed, retrieve, answer. The system can:

- rewrite follow-up questions
- run multiple retrieval attempts
- merge and rank evidence
- verify the answer before finalizing

Why it matters:

- better handling of ambiguous questions
- stronger grounding
- more intelligent retrieval behavior

### 3. Exact-Page Precision

If a user asks for a specific page in a document, FindX prioritizes that page instead of returning semantically similar content from other pages.

Why it matters:

- supports document review use cases
- reduces hallucination in page-based questions
- shows precision, not just similarity search

### 4. Verifier-Backed Answers

The backend does not immediately trust the first drafted answer. It checks whether the answer is supported by retrieved evidence and can refine retrieval once if needed.

Why it matters:

- reduces unsupported answers
- improves trustworthiness
- makes the system more agentic than a basic RAG pipeline

### 5. Explainability

Answers are returned with source snippets and page references.

Why it matters:

- users can inspect supporting evidence
- answers are easier to trust
- the system behaves like decision support, not black-box chat

## 6. What Makes FindX Different

Compared to a basic RAG system, FindX adds:

- role-aware retrieval filtering
- visibility-aware document access
- follow-up rewriting
- exact-page retrieval
- verifier-backed answer finalization
- legacy compatibility fallback

Good line to say:

"FindX is not only retrieval-augmented generation. It is retrieval-aware, access-aware, and verification-aware."

## 7. Best Demo Flow

Use a short, strong demo:

1. Log in as `Admin`.
2. Upload a document and show terminal-side ingestion progress.
3. Ask a normal document question.
4. Ask a short follow-up question.
5. Ask an exact-page question such as `Explain page #205 in the ITC pdf.`
6. Show the evidence panel and cited page.
7. Mention that different roles see different document scopes.

## 8. Strong Closing

Use a closing like this:

"FindX shows that enterprise AI becomes much more useful when retrieval is secure, precise, explainable, and verified before the answer is shown."
