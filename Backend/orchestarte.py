import os
import re
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

try:
    from .pdf_chroma_ingest import ChromaMultimodalDB, RetrievedChunk
except ImportError:
    from pdf_chroma_ingest import ChromaMultimodalDB, RetrievedChunk


SMALL_TALK_PATTERNS = [
    re.compile(r"^(hi|hello|hey)( there)?[!. ]*$", re.IGNORECASE),
    re.compile(r"^good (morning|afternoon|evening)[!. ]*$", re.IGNORECASE),
    re.compile(r"^(thanks|thank you|ok thanks)[!. ]*$", re.IGNORECASE),
    re.compile(r"^(who are you|what can you do)\??$", re.IGNORECASE),
]


class SourceCitation(BaseModel):
    id: str
    doc: str
    doc_uuid: str
    page: Optional[int] = None
    confidence: str
    text: str


class OrchestratorResponse(BaseModel):
    answer: str
    explanation: str
    sources: List[SourceCitation] = Field(default_factory=list)
    status: str = "success"


class QueryOrchestrator:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        load_dotenv()
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

        self.llm = ChatGroq(
            model=model_name,
            temperature=0,
            groq_api_key=api_key,
        )
        print(f"[Orchestrator] Groq model ready: {model_name}")
        self.answer_system_prompt = (
            "You are FindX, a grounded enterprise document assistant.\n"
            "Answer ONLY from the retrieved company context provided to you.\n"
            "If the context is partial, say what is supported and what remains unclear.\n"
            "If the context is insufficient, say you could not find enough support in the indexed files.\n"
            "Keep the answer concise, professional, and easy to scan.\n"
            "Do not mention embeddings, vector search, chunks, or internal tooling."
        )

    @staticmethod
    def _normalize_output_text(text: str) -> str:
        return (
            (text or "")
            .replace("\u2022", "- ")
            .replace("\u25cf", "- ")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u00a0", " ")
        )

    @staticmethod
    def _read_text(content) -> str:
        if isinstance(content, str):
            return QueryOrchestrator._normalize_output_text(content).strip()

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            text = "\n".join(part for part in text_parts if part)
            return QueryOrchestrator._normalize_output_text(text).strip()

        return ""

    @staticmethod
    def _is_small_talk(user_query: str) -> bool:
        normalized = user_query.strip()
        return any(pattern.match(normalized) for pattern in SMALL_TALK_PATTERNS)

    @staticmethod
    def _format_history(chat_history: List[BaseMessage], limit: int = 4) -> str:
        relevant_messages = chat_history[-limit:]
        if not relevant_messages:
            return "No prior conversation."

        lines = []
        for message in relevant_messages:
            if isinstance(message, HumanMessage):
                role = "User"
            elif isinstance(message, AIMessage):
                role = "Assistant"
            else:
                role = "Message"

            text = QueryOrchestrator._read_text(message.content)
            if text:
                lines.append(f"{role}: {text}")

        return "\n".join(lines) if lines else "No prior conversation."

    @staticmethod
    def _build_context_block(chunks: List[RetrievedChunk]) -> str:
        context_parts = []
        for index, chunk in enumerate(chunks, start=1):
            page_label = f"Page {chunk.page}" if chunk.page is not None else "Page unavailable"
            context_parts.append(
                "\n".join(
                    [
                        f"[S{index}] Document: {chunk.source_name}",
                        f"Doc UUID: {chunk.doc_uuid}",
                        f"Location: {page_label}",
                        f"Match confidence: {chunk.confidence}",
                        f"Snippet: {chunk.text}",
                    ]
                )
            )

        return "\n\n".join(context_parts)

    @staticmethod
    def _build_explanation(sources: List[SourceCitation], doc_uuid: Optional[str] = None) -> str:
        if not sources:
            base = "FindX searched the indexed files for this workspace and did not find a strong enough document match to answer confidently."
            if doc_uuid:
                return f"{base} The search was narrowed to document {doc_uuid}."
            return base

        unique_docs = []
        for source in sources:
            if source.doc not in unique_docs:
                unique_docs.append(source.doc)

        lead_source = sources[0]
        doc_summary = ", ".join(unique_docs[:3])
        if len(unique_docs) > 3:
            doc_summary += ", and more"

        return (
            f"Grounded in {len(sources)} retrieved passage(s) from {len(unique_docs)} document(s): "
            f"{doc_summary}. Strongest supporting passage came from {lead_source.doc} "
            f"with an approximate retrieval confidence of {lead_source.confidence}."
        )

    def _answer_small_talk(self, user_query: str) -> OrchestratorResponse:
        message = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are FindX, a professional enterprise search assistant. "
                        "Respond briefly to greetings or capability questions."
                    )
                ),
                HumanMessage(content=user_query),
            ]
        )
        answer = self._read_text(message.content) or "Hello. I can help you search the indexed company documents."
        return OrchestratorResponse(
            answer=answer,
            explanation="No document retrieval was needed because this request was conversational rather than document-specific.",
            sources=[],
        )

    def _generate_grounded_answer(
        self,
        user_query: str,
        chat_history: List[BaseMessage],
        chunks: List[RetrievedChunk],
    ) -> str:
        history_block = self._format_history(chat_history)
        context_block = self._build_context_block(chunks)

        prompt = (
            f"Recent conversation:\n{history_block}\n\n"
            f"Current user question:\n{user_query}\n\n"
            f"Retrieved company context:\n{context_block}\n\n"
            "Write a concise answer grounded only in the retrieved context. "
            "If the snippets do not fully answer the question, acknowledge the limitation."
        )

        response = self.llm.invoke(
            [
                SystemMessage(content=self.answer_system_prompt),
                HumanMessage(content=prompt),
            ]
        )
        answer = self._read_text(response.content)
        return answer or "I could not produce a grounded answer from the retrieved document context."

    def answer(
        self,
        user_query: str,
        chat_id: str,
        doc_uuid: Optional[str] = None,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> OrchestratorResponse:
        if chat_history is None:
            chat_history = []

        if self._is_small_talk(user_query):
            return self._answer_small_talk(user_query)

        print("[Orchestrator] Starting retrieval...")
        db = ChromaMultimodalDB(chat_id=chat_id, doc_uuid=doc_uuid)
        chunks = db.query_chunks(
            question=user_query,
            top_k=4,
            only_doc=doc_uuid,
            max_per_doc=2,
        )

        if not chunks:
            return OrchestratorResponse(
                answer=(
                    "I could not find enough relevant company context in the indexed documents "
                    "to answer that confidently."
                ),
                explanation=self._build_explanation([], doc_uuid=doc_uuid),
                sources=[],
            )

        print("[Orchestrator] Retrieval completed. Starting grounded generation...")
        answer = self._generate_grounded_answer(
            user_query=user_query,
            chat_history=chat_history,
            chunks=chunks,
        )
        sources = [SourceCitation(**chunk.to_source_payload()) for chunk in chunks]

        print("[Orchestrator] Grounded generation completed successfully.")
        return OrchestratorResponse(
            answer=answer,
            explanation=self._build_explanation(sources, doc_uuid=doc_uuid),
            sources=sources,
        )


if __name__ == "__main__":
    orchestrator = QueryOrchestrator()
    sample_chat_id = "demo_chat"
    sample_doc_uuid = None
    memory: list[BaseMessage] = []

    print("Type your question (Ctrl+C to stop):")
    while True:
        try:
            user_q = input("> ").strip()
            if not user_q:
                continue

            result = orchestrator.answer(
                user_query=user_q,
                chat_id=sample_chat_id,
                doc_uuid=sample_doc_uuid,
                chat_history=memory,
            )
            print(f"\n{result.answer}\n")
            memory.extend([HumanMessage(content=user_q), AIMessage(content=result.answer)])
        except KeyboardInterrupt:
            print("\nExiting...")
            break
