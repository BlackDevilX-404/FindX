import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import chromadb
import fitz
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

try:
    from .auth import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_HR
    from .pdf_chroma_ingest import ChromaMultimodalDB
    from .process_ppt import Ppt2Pdf
except ImportError:
    from auth import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_HR
    from pdf_chroma_ingest import ChromaMultimodalDB
    from process_ppt import Ppt2Pdf

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ROLE_CATEGORY_ACCESS = {
    ROLE_ADMIN: ["HR", "TECH", "FINANCE", "GENERAL"],
    ROLE_HR: ["HR", "GENERAL"],
    ROLE_DEVELOPER: ["TECH", "GENERAL"],
}
VALID_CATEGORIES = sorted({category for values in ROLE_CATEGORY_ACCESS.values() for category in values})
CATEGORY_VARIANTS = {
    category: {category, category.lower(), category.title()}
    for category in VALID_CATEGORIES
}

WORD_PATTERN = re.compile(r"[a-zA-Z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "as",
    "at",
    "be",
    "by",
    "document",
    "file",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "pdf",
    "rule",
    "rules",
    "say",
    "says",
    "tell",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
}

MIN_HIGH_CONFIDENT_SCORE = 0.60
MIN_CONFIDENT_SCORE = 0.30
MIN_LEXICAL_OVERLAP = 0.08
MIN_LIGHT_OVERLAP = 0.04


class SourceItem(BaseModel):
    document: str
    snippet: str
    page: int | None = None
    confidence: str | None = None


class QueryResult(BaseModel):
    answer: str
    explanation: str
    sources: list[SourceItem] = Field(default_factory=list)


class IngestResult(BaseModel):
    document_id: str
    document: str
    category: str
    sensitivity: str | None = None
    chunks_indexed: int


@dataclass
class RetrievedChunk:
    document: str
    category: str
    sensitivity: str | None
    page: Optional[int]
    text: str
    score: float


def normalize_text(text: str) -> str:
    normalized = (
        (text or "")
        .replace("\u2022", "- ")
        .replace("\u25cf", "- ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
        .replace("\u200b", "")
    )
    return re.sub(r"\s+", " ", normalized).strip()


def split_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if len(paragraph.strip()) > 40]


def sentence_chunks(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def sliding_chunks(tokens: list[str], size: int = 220, overlap: int = 40):
    index = 0
    while index < len(tokens):
        yield tokens[index : index + size]
        index += size - overlap


def keyword_overlap(question: str, text: str) -> float:
    question_terms = {
        token
        for token in WORD_PATTERN.findall(question.lower())
        if token not in STOP_WORDS and len(token) > 2
    }
    if not question_terms:
        return 0.0

    text_terms = {
        token
        for token in WORD_PATTERN.findall(text.lower())
        if token not in STOP_WORDS and len(token) > 2
    }
    if not text_terms:
        return 0.0

    return len(question_terms & text_terms) / len(question_terms)


def normalize_role(role: str) -> str:
    value = str(role or "").strip().lower()
    mapping = {
        ROLE_ADMIN.lower(): ROLE_ADMIN,
        ROLE_HR.lower(): ROLE_HR,
        ROLE_DEVELOPER.lower(): ROLE_DEVELOPER,
    }
    return mapping.get(value, str(role or "").strip())


def normalize_category_value(value: Any) -> str:
    return str(value or "").strip().upper()


def allowed_categories_for_role(role: str) -> list[str]:
    return ROLE_CATEGORY_ACCESS.get(normalize_role(role), [])


def validate_category(category: str) -> str:
    normalized = normalize_category_value(category)
    if normalized not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Allowed values: {', '.join(VALID_CATEGORIES)}")
    return normalized


def category_matches_allowed(value: Any, allowed_categories: list[str]) -> bool:
    if not allowed_categories:
        return False
    return normalize_category_value(value) in {category.upper() for category in allowed_categories}


def build_category_where_filter(allowed_categories: list[str]) -> dict[str, Any]:
    category_values = sorted(
        {
            variant
            for category in allowed_categories
            for variant in CATEGORY_VARIANTS.get(category.upper(), {category.upper()})
        }
    )
    return {"category": {"$in": category_values}}


def format_confidence(score: float) -> str:
    percentage = max(0, min(99, round(score * 100)))
    return f"{percentage}%"


class EnterpriseRAGService:
    _chroma_client = None
    _embedder: Optional[SentenceTransformer] = None

    def __init__(self, collection_name: str = "enterprise_chunks", model_name: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

        self.base_dir = Path(__file__).resolve().parent
        self.downloads_dir = self.base_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir = self.base_dir / "chroma_db_storage"
        self.collection_name = collection_name

        if EnterpriseRAGService._chroma_client is None:
            EnterpriseRAGService._chroma_client = chromadb.PersistentClient(path=str(self.storage_dir))

        self.client = EnterpriseRAGService._chroma_client
        self.collection = self.client.get_or_create_collection(self.collection_name)
        self.embedder = self._get_embedder()
        self.llm = ChatGroq(model=model_name, temperature=0, groq_api_key=api_key)

    @classmethod
    def _get_embedder(cls) -> SentenceTransformer:
        if cls._embedder is None:
            cls._embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        return cls._embedder

    def save_upload(self, filename: str, file_bytes: bytes) -> Path:
        extension = Path(filename).suffix.lower()
        stored_path = self.downloads_dir / f"{uuid.uuid4().hex}{extension}"
        stored_path.write_bytes(file_bytes)
        return stored_path

    def _convert_to_pdf_if_needed(self, file_path: Path) -> Path:
        extension = file_path.suffix.lower()
        if extension == ".pdf":
            return file_path

        if extension not in {".ppt", ".pptx"}:
            raise ValueError("Unsupported file type. Only PDF, PPT, and PPTX are supported.")

        relative_base = Path("downloads") / file_path.stem
        converter = Ppt2Pdf(str(relative_base).replace("\\", "/"), extension[1:])
        converter.convert_ppt_to_pdf()
        pdf_path = self.base_dir / f"{relative_base}.pdf"

        if not pdf_path.exists():
            raise ValueError("PPT conversion failed. PDF output was not created.")

        return pdf_path

    def _extract_pages(self, pdf_path: Path) -> list[dict[str, Any]]:
        document = fitz.open(pdf_path)
        pages: list[dict[str, Any]] = []

        for page_number, page in enumerate(document, start=1):
            text = normalize_text(page.get_text())
            if text:
                pages.append({"page": page_number, "text": text})

        document.close()
        return pages

    def _chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []

        for page in pages:
            for paragraph in split_paragraphs(page["text"]):
                tokens = " ".join(sentence_chunks(paragraph)).split()
                for token_window in sliding_chunks(tokens):
                    chunk_text = normalize_text(" ".join(token_window))
                    if chunk_text:
                        chunks.append({"page": page["page"], "text": chunk_text})

        return chunks

    def ingest_document(
        self,
        file_path: Path,
        document_name: str,
        category: str,
        sensitivity: str | None,
        uploaded_by: str,
    ) -> IngestResult:
        validated_category = validate_category(category)
        pdf_path = self._convert_to_pdf_if_needed(file_path)
        pages = self._extract_pages(pdf_path)
        chunks = self._chunk_pages(pages)

        if not chunks:
            raise ValueError("No extractable text found in the uploaded document.")

        document_id = uuid.uuid4().hex
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.encode(
            texts,
            batch_size=24,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        self.collection.add(
            ids=[f"{document_id}:{index}" for index in range(len(chunks))],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": document_id,
                    "document": document_name,
                    "category": validated_category,
                    "sensitivity": sensitivity,
                    "page": chunk["page"],
                    "uploaded_by": uploaded_by,
                }
                for chunk in chunks
            ],
        )

        return IngestResult(
            document_id=document_id,
            document=document_name,
            category=validated_category,
            sensitivity=sensitivity,
            chunks_indexed=len(chunks),
        )

    def _rank_chunks(self, question: str, results: dict[str, Any], top_k: int) -> list[RetrievedChunk]:
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        ranked_chunks: list[RetrievedChunk] = []
        for document_text, metadata, distance in zip(documents, metadatas, distances):
            if not document_text or not metadata:
                continue

            text = normalize_text(document_text)
            if not text:
                continue

            semantic_score = 1.0 / (1.0 + max(float(distance or 0.0), 0.0))
            lexical_score = keyword_overlap(question, text)
            combined_score = round((semantic_score * 0.78) + (lexical_score * 0.22), 4)

            ranked_chunks.append(
                RetrievedChunk(
                    document=str(metadata.get("document") or "Unknown document"),
                    category=normalize_category_value(metadata.get("category") or "GENERAL"),
                    sensitivity=metadata.get("sensitivity"),
                    page=metadata.get("page"),
                    text=text,
                    score=combined_score,
                )
            )

        ranked_chunks.sort(key=lambda item: item.score, reverse=True)

        selected: list[RetrievedChunk] = []
        seen: set[tuple[str, str]] = set()
        for chunk in ranked_chunks:
            fingerprint = (chunk.document, chunk.text[:180])
            if fingerprint in seen:
                continue

            selected.append(chunk)
            seen.add(fingerprint)
            if len(selected) >= top_k:
                break

        return selected

    def _filter_results_by_allowed_categories(
        self,
        results: dict[str, Any],
        allowed_categories: list[str],
    ) -> dict[str, list[list[Any]]]:
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        filtered_documents: list[Any] = []
        filtered_metadatas: list[Any] = []
        filtered_distances: list[Any] = []

        for document_text, metadata, distance in zip(documents, metadatas, distances):
            if not metadata or not category_matches_allowed(metadata.get("category"), allowed_categories):
                continue
            filtered_documents.append(document_text)
            filtered_metadatas.append(metadata)
            filtered_distances.append(distance)

        return {
            "documents": [filtered_documents],
            "metadatas": [filtered_metadatas],
            "distances": [filtered_distances],
        }

    def _query_enterprise_chunks(self, query_text: str, role: str, top_k: int) -> list[RetrievedChunk]:
        allowed_categories = allowed_categories_for_role(role)
        if not allowed_categories:
            return []

        query_embedding = self.embedder.encode(
            query_text,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        fetch_k = max(top_k * 5, 20)
        filtered_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            where=build_category_where_filter(allowed_categories),
            include=["documents", "metadatas", "distances"],
        )
        ranked_chunks = self._rank_chunks(query_text, filtered_results, top_k=top_k)
        if ranked_chunks:
            return ranked_chunks

        if self.collection.count() == 0:
            return []

        compatibility_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
        )
        locally_filtered = self._filter_results_by_allowed_categories(
            compatibility_results,
            allowed_categories=allowed_categories,
        )
        return self._rank_chunks(query_text, locally_filtered, top_k=top_k)

    def _query_legacy_chunks(
        self,
        query_text: str,
        chat_id: str | None,
        doc_uuid: str | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chat_id:
            return []

        legacy_db = ChromaMultimodalDB(chat_id=chat_id, doc_uuid=doc_uuid)
        legacy_chunks = legacy_db.query_chunks(
            question=query_text,
            top_k=top_k,
            only_doc=doc_uuid,
            max_per_doc=2,
        )

        return [
            RetrievedChunk(
                document=chunk.source_name,
                category="LEGACY",
                sensitivity=None,
                page=chunk.page,
                text=normalize_text(chunk.text),
                score=chunk.score,
            )
            for chunk in legacy_chunks
            if normalize_text(chunk.text)
        ]

    def _is_confident_enough(self, question: str, chunks: list[RetrievedChunk]) -> bool:
        if not chunks:
            return False

        top_chunk = chunks[0]
        top_overlap = keyword_overlap(question, top_chunk.text)

        if top_chunk.score >= MIN_HIGH_CONFIDENT_SCORE:
            return True

        if top_overlap >= MIN_LEXICAL_OVERLAP:
            return True

        if top_chunk.score >= MIN_CONFIDENT_SCORE and top_overlap >= MIN_LIGHT_OVERLAP:
            return True

        if len(chunks) >= 2:
            second_overlap = keyword_overlap(question, chunks[1].text)
            average_score = (top_chunk.score + chunks[1].score) / 2
            max_overlap = max(top_overlap, second_overlap)
            if average_score >= MIN_CONFIDENT_SCORE and max_overlap >= MIN_LIGHT_OVERLAP:
                return True

        return False

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        lines: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            location = f"Page {chunk.page}" if chunk.page else "Page unavailable"
            lines.append(
                "\n".join(
                    [
                        f"[S{index}] Document: {chunk.document}",
                        f"Category: {chunk.category}",
                        f"Location: {location}",
                        f"Snippet: {chunk.text}",
                    ]
                )
            )
        return "\n\n".join(lines)

    def _generate_answer(self, query_text: str, chunks: list[RetrievedChunk]) -> str:
        context = self._build_context(chunks)
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are an enterprise RAG assistant. "
                        "Answer strictly from the retrieved context. "
                        "If the context is insufficient, say so clearly. "
                        "Do not invent policy details."
                    )
                ),
                HumanMessage(
                    content=(
                        f"User question:\n{query_text}\n\n"
                        f"Authorized retrieved context:\n{context}\n\n"
                        "Write a concise answer grounded only in that context."
                    )
                ),
            ]
        )

        if isinstance(response.content, str):
            return normalize_text(response.content)

        if isinstance(response.content, list):
            text = "\n".join(
                item.get("text", "")
                for item in response.content
                if isinstance(item, dict) and item.get("type") == "text"
            )
            return normalize_text(text)

        return "No accessible data found for your role"

    def _build_explanation(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No accessible data found for your role"

        unique_documents: list[str] = []
        for chunk in chunks:
            if chunk.document not in unique_documents:
                unique_documents.append(chunk.document)

        lead_chunk = chunks[0]
        document_summary = ", ".join(unique_documents[:3])
        if len(unique_documents) > 3:
            document_summary += ", and more"

        return (
            f"Grounded in {len(chunks)} retrieved passage(s) from {len(unique_documents)} document(s): "
            f"{document_summary}. Top supporting match scored about {format_confidence(lead_chunk.score)}."
        )

    def query(
        self,
        query_text: str,
        role: str,
        chat_id: str | None = None,
        doc_uuid: str | None = None,
        top_k: int = 4,
    ) -> QueryResult:
        normalized_role = normalize_role(role)
        allowed_categories = allowed_categories_for_role(normalized_role)
        if not allowed_categories:
            return QueryResult(
                answer="No accessible data found for your role",
                explanation="Your role does not have access to any searchable document categories.",
                sources=[],
            )

        enterprise_chunks = self._query_enterprise_chunks(
            query_text=query_text,
            role=normalized_role,
            top_k=top_k,
        )
        if enterprise_chunks:
            selected_chunks = enterprise_chunks
        else:
            legacy_chunks = self._query_legacy_chunks(
                query_text=query_text,
                chat_id=chat_id,
                doc_uuid=doc_uuid,
                top_k=top_k,
            )
            selected_chunks = legacy_chunks

        if not selected_chunks or not self._is_confident_enough(query_text, selected_chunks):
            return QueryResult(
                answer="No accessible data found for your role",
                explanation="The accessible documents did not contain a strong enough match for this question.",
                sources=[],
            )

        answer = self._generate_answer(query_text, selected_chunks)
        sources = [
            SourceItem(
                document=chunk.document,
                snippet=chunk.text[:320],
                page=chunk.page,
                confidence=format_confidence(chunk.score),
            )
            for chunk in selected_chunks
        ]
        return QueryResult(
            answer=answer,
            explanation=self._build_explanation(selected_chunks),
            sources=sources,
        )
