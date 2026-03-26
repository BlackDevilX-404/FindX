import os
import json
import re
import uuid
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import chromadb
import fitz
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from openpyxl import load_workbook
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from docx import Document as DocxDocument

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
ROLE_VISIBILITY_ACCESS = {
    ROLE_ADMIN: ["private", "hr", "developer", "both"],
    ROLE_HR: ["hr", "both"],
    ROLE_DEVELOPER: ["developer", "both"],
}
VALID_CATEGORIES = sorted({category for values in ROLE_CATEGORY_ACCESS.values() for category in values})
CATEGORY_VARIANTS = {
    category: {category, category.lower(), category.title()}
    for category in VALID_CATEGORIES
}
VALID_VISIBILITY_SCOPES = ["private", "hr", "developer", "both"]

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
FOLLOW_UP_HINTS = {
    "it",
    "its",
    "they",
    "them",
    "that",
    "those",
    "this",
    "these",
    "he",
    "she",
    "their",
    "there",
    "same",
}
SMALL_TALK_PATTERNS = [
    re.compile(r"^(hi|hello|hey)( there)?[!. ]*$", re.IGNORECASE),
    re.compile(r"^good (morning|afternoon|evening)[!. ]*$", re.IGNORECASE),
    re.compile(r"^(thanks|thank you|ok thanks)[!. ]*$", re.IGNORECASE),
    re.compile(r"^(who are you|what can you do)\??$", re.IGNORECASE),
]


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


@dataclass
class PlannedQuery:
    text: str
    reason: str


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
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    long_paragraphs = [paragraph for paragraph in paragraphs if len(paragraph) > 40]
    if long_paragraphs:
        return long_paragraphs

    normalized = normalize_text(text)
    return [normalized] if normalized else []


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


def allowed_visibility_scopes_for_role(role: str) -> list[str]:
    return ROLE_VISIBILITY_ACCESS.get(normalize_role(role), [])


def validate_category(category: str) -> str:
    normalized = normalize_category_value(category)
    if normalized not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Allowed values: {', '.join(VALID_CATEGORIES)}")
    return normalized


def normalize_visibility_scope(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in VALID_VISIBILITY_SCOPES else "private"


def validate_visibility_scope(scope: str) -> str:
    normalized = str(scope or "").strip().lower()
    if normalized not in VALID_VISIBILITY_SCOPES:
        raise ValueError(
            f"Invalid visibility scope '{scope}'. Allowed values: {', '.join(VALID_VISIBILITY_SCOPES)}"
        )
    return normalized


def category_matches_allowed(value: Any, allowed_categories: list[str]) -> bool:
    if not allowed_categories:
        return False
    return normalize_category_value(value) in {category.upper() for category in allowed_categories}


def visibility_matches_allowed(value: Any, allowed_scopes: list[str]) -> bool:
    if not allowed_scopes:
        return False
    return normalize_visibility_scope(value) in {scope.lower() for scope in allowed_scopes}


def build_category_where_filter(allowed_categories: list[str]) -> dict[str, Any]:
    category_values = sorted(
        {
            variant
            for category in allowed_categories
            for variant in CATEGORY_VARIANTS.get(category.upper(), {category.upper()})
        }
    )
    return {"category": {"$in": category_values}}


def build_access_where_filter(allowed_categories: list[str], allowed_visibility_scopes: list[str]) -> dict[str, Any]:
    category_filter = build_category_where_filter(allowed_categories)
    visibility_filter = {"visibility_scope": {"$in": sorted({scope.lower() for scope in allowed_visibility_scopes})}}
    return {"$and": [category_filter, visibility_filter]}


def format_confidence(score: float) -> str:
    percentage = max(0, min(99, round(score * 100)))
    return f"{percentage}%"


def build_metadata_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value is not None}


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
            raise ValueError(
                "Unsupported file type. Supported formats: PDF, PPT, PPTX, DOCX, TXT, MD, CSV, JSON, XLSX."
            )

        relative_base = Path("downloads") / file_path.stem
        converter = Ppt2Pdf(str(relative_base).replace("\\", "/"), extension[1:])
        converter.convert_ppt_to_pdf()
        pdf_path = self.base_dir / f"{relative_base}.pdf"

        if not pdf_path.exists():
            raise ValueError("PPT conversion failed. PDF output was not created.")

        return pdf_path

    def _extract_docx_pages(self, file_path: Path) -> list[dict[str, Any]]:
        document = DocxDocument(file_path)
        blocks: list[str] = []

        for paragraph in document.paragraphs:
            text = normalize_text(paragraph.text)
            if text:
                blocks.append(text)

        for table in document.tables:
            row_texts: list[str] = []
            for row in table.rows:
                cells = [normalize_text(cell.text) for cell in row.cells if normalize_text(cell.text)]
                if cells:
                    row_texts.append(" | ".join(cells))
            if row_texts:
                blocks.append("\n".join(row_texts))

        combined = "\n\n".join(blocks).strip()
        if not combined:
            return []

        return [{"page": 1, "text": combined}]

    def _extract_spreadsheet_pages(self, file_path: Path) -> list[dict[str, Any]]:
        workbook = load_workbook(filename=file_path, read_only=True, data_only=True)
        pages: list[dict[str, Any]] = []

        try:
            for sheet_index, sheet in enumerate(workbook.worksheets, start=1):
                rows: list[str] = []
                for row in sheet.iter_rows(values_only=True):
                    cells = [normalize_text(str(cell)) for cell in row if cell is not None and normalize_text(str(cell))]
                    if cells:
                        rows.append(" | ".join(cells))

                sheet_text = normalize_text(f"Sheet: {sheet.title}\n\n" + "\n".join(rows))
                if sheet_text:
                    pages.append({"page": sheet_index, "text": sheet_text})
        finally:
            workbook.close()

        return pages

    def _extract_text_file_pages(self, file_path: Path) -> list[dict[str, Any]]:
        extension = file_path.suffix.lower()

        if extension == ".csv":
            with file_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.reader(handle)
                rows = [" | ".join(normalize_text(cell) for cell in row if normalize_text(cell)) for row in reader]
                text = "\n".join(row for row in rows if row.strip())
        elif extension == ".json":
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
            try:
                parsed = json.loads(raw)
                text = json.dumps(parsed, indent=2, ensure_ascii=True)
            except json.JSONDecodeError:
                text = raw
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")

        normalized = normalize_text(text)
        if not normalized:
            return []

        return [{"page": 1, "text": normalized}]

    def _extract_pages_from_file(self, file_path: Path) -> list[dict[str, Any]]:
        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return self._extract_pages(file_path)
        if extension in {".ppt", ".pptx"}:
            return self._extract_pages(self._convert_to_pdf_if_needed(file_path))
        if extension == ".docx":
            return self._extract_docx_pages(file_path)
        if extension == ".xlsx":
            return self._extract_spreadsheet_pages(file_path)
        if extension in {".txt", ".md", ".csv", ".json"}:
            return self._extract_text_file_pages(file_path)

        raise ValueError(
            "Unsupported file type. Supported formats: PDF, PPT, PPTX, DOCX, TXT, MD, CSV, JSON, XLSX."
        )

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
        visibility_scope: str,
        uploaded_by: str,
    ) -> IngestResult:
        validated_category = validate_category(category)
        validated_visibility_scope = validate_visibility_scope(visibility_scope)
        pages = self._extract_pages_from_file(file_path)
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
                build_metadata_payload(
                    {
                        "document_id": document_id,
                        "document": document_name,
                        "category": validated_category,
                        "sensitivity": sensitivity,
                        "visibility_scope": validated_visibility_scope,
                        "page": chunk["page"],
                        "uploaded_by": uploaded_by,
                    }
                )
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

    @staticmethod
    def _extract_message_text(message: dict[str, Any]) -> str:
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return normalize_text(content)

        text = message.get("text")
        if isinstance(text, str) and text.strip():
            return normalize_text(text)

        return ""

    def _normalize_chat_history(self, chat_history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
        normalized_history: list[dict[str, str]] = []
        for message in chat_history or []:
            role = str(message.get("role") or "").strip().lower()
            if role not in {"user", "assistant"}:
                continue

            text = self._extract_message_text(message)
            if not text:
                continue

            normalized_history.append({"role": role, "content": text})

        return normalized_history[-6:]

    @staticmethod
    def _history_to_text(chat_history: list[dict[str, str]]) -> str:
        if not chat_history:
            return "No prior conversation."

        lines = []
        for message in chat_history:
            speaker = "User" if message["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {message['content']}")
        return "\n".join(lines)

    @staticmethod
    def _is_small_talk(query_text: str) -> bool:
        normalized = query_text.strip()
        return any(pattern.match(normalized) for pattern in SMALL_TALK_PATTERNS)

    @staticmethod
    def _looks_like_follow_up(query_text: str) -> bool:
        normalized = normalize_text(query_text).lower()
        if len(normalized.split()) <= 5:
            return True

        tokens = set(WORD_PATTERN.findall(normalized))
        return any(token in FOLLOW_UP_HINTS for token in tokens)

    def _rewrite_query_with_history(
        self,
        query_text: str,
        chat_history: list[dict[str, str]],
    ) -> str:
        if not chat_history:
            return query_text

        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Rewrite the user's latest question into a standalone enterprise search query. "
                        "Preserve intent, include missing references from the conversation, and return only the rewritten query. "
                        "If no rewrite is needed, return the original question."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Conversation:\n{self._history_to_text(chat_history)}\n\n"
                        f"Latest question:\n{query_text}"
                    )
                ),
            ]
        )

        rewritten = normalize_text(self._read_llm_text(response.content))
        return rewritten or query_text

    def _generate_keyword_query(self, query_text: str) -> str:
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Convert the user's request into a compact retrieval query for enterprise documents. "
                        "Keep only the core subject, constraints, and policy terms. Return one line only."
                    )
                ),
                HumanMessage(content=query_text),
            ]
        )
        keyword_query = normalize_text(self._read_llm_text(response.content))
        return keyword_query or query_text

    @staticmethod
    def _read_llm_text(content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )

        return ""

    def _plan_queries(
        self,
        query_text: str,
        chat_history: list[dict[str, str]],
    ) -> list[PlannedQuery]:
        planned_queries = [PlannedQuery(text=normalize_text(query_text), reason="original user question")]

        if chat_history and self._looks_like_follow_up(query_text):
            rewritten = self._rewrite_query_with_history(query_text, chat_history)
            if rewritten and rewritten.lower() != planned_queries[0].text.lower():
                planned_queries.append(PlannedQuery(text=rewritten, reason="rewritten follow-up with conversation context"))

        keyword_query = self._generate_keyword_query(planned_queries[0].text)
        if keyword_query and all(keyword_query.lower() != item.text.lower() for item in planned_queries):
            planned_queries.append(PlannedQuery(text=keyword_query, reason="compressed retrieval query"))

        return planned_queries

    def _filter_results_by_access(
        self,
        results: dict[str, Any],
        allowed_categories: list[str],
        allowed_visibility_scopes: list[str],
    ) -> dict[str, list[list[Any]]]:
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        filtered_documents: list[Any] = []
        filtered_metadatas: list[Any] = []
        filtered_distances: list[Any] = []

        for document_text, metadata, distance in zip(documents, metadatas, distances):
            if not metadata:
                continue
            if not category_matches_allowed(metadata.get("category"), allowed_categories):
                continue
            if not visibility_matches_allowed(metadata.get("visibility_scope"), allowed_visibility_scopes):
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
        allowed_visibility_scopes = allowed_visibility_scopes_for_role(role)
        if not allowed_categories or not allowed_visibility_scopes:
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
            where=build_access_where_filter(allowed_categories, allowed_visibility_scopes),
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
        locally_filtered = self._filter_results_by_access(
            compatibility_results,
            allowed_categories=allowed_categories,
            allowed_visibility_scopes=allowed_visibility_scopes,
        )
        return self._rank_chunks(query_text, locally_filtered, top_k=top_k)

    def update_document_visibility(self, document_id: str, visibility_scope: str) -> bool:
        validated_visibility_scope = validate_visibility_scope(visibility_scope)
        results = self.collection.get(
            where={"document_id": {"$eq": document_id}},
            include=["metadatas"],
        )

        ids = results.get("ids") or []
        metadatas = results.get("metadatas") or []
        if not ids:
            return False

        next_metadatas = [
            build_metadata_payload(
                {
                    **(metadata or {}),
                    "visibility_scope": validated_visibility_scope,
                }
            )
            for metadata in metadatas
        ]
        self.collection.update(ids=ids, metadatas=next_metadatas)
        return True

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

    @staticmethod
    def _merge_ranked_chunks(question: str, chunk_groups: list[list[RetrievedChunk]], top_k: int) -> list[RetrievedChunk]:
        scored: list[RetrievedChunk] = []
        seen: set[tuple[str, Optional[int], str]] = set()

        for chunk_group in chunk_groups:
            for chunk in chunk_group:
                fingerprint = (chunk.document, chunk.page, chunk.text[:180])
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                rescored = round((chunk.score * 0.82) + (keyword_overlap(question, chunk.text) * 0.18), 4)
                scored.append(
                    RetrievedChunk(
                        document=chunk.document,
                        category=chunk.category,
                        sensitivity=chunk.sensitivity,
                        page=chunk.page,
                        text=chunk.text,
                        score=rescored,
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

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

    def _answer_small_talk(self, query_text: str) -> QueryResult:
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are FindX, an enterprise document assistant. "
                        "Respond briefly to greetings or capability questions."
                    )
                ),
                HumanMessage(content=query_text),
            ]
        )
        answer = normalize_text(self._read_llm_text(response.content))
        return QueryResult(
            answer=answer or "Hello. I can help you search the indexed company documents you are allowed to access.",
            explanation="No document retrieval was needed because this request was conversational rather than document-specific.",
            sources=[],
        )

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
        chat_history: list[dict[str, Any]] | None = None,
        top_k: int = 4,
    ) -> QueryResult:
        normalized_role = normalize_role(role)
        allowed_categories = allowed_categories_for_role(normalized_role)
        allowed_visibility_scopes = allowed_visibility_scopes_for_role(normalized_role)
        if not allowed_categories or not allowed_visibility_scopes:
            return QueryResult(
                answer="No accessible data found for your role",
                explanation="Your role does not have access to any searchable document categories.",
                sources=[],
            )

        if self._is_small_talk(query_text):
            return self._answer_small_talk(query_text)

        normalized_history = self._normalize_chat_history(chat_history)
        planned_queries = self._plan_queries(query_text, normalized_history)

        enterprise_candidates: list[list[RetrievedChunk]] = []
        for planned_query in planned_queries:
            enterprise_chunks = self._query_enterprise_chunks(
                query_text=planned_query.text,
                role=normalized_role,
                top_k=top_k,
            )
            if enterprise_chunks:
                enterprise_candidates.append(enterprise_chunks)

        selected_chunks = self._merge_ranked_chunks(
            question=query_text,
            chunk_groups=enterprise_candidates,
            top_k=top_k,
        )

        if not selected_chunks:
            legacy_candidates: list[list[RetrievedChunk]] = []
            for planned_query in planned_queries:
                legacy_chunks = self._query_legacy_chunks(
                    query_text=planned_query.text,
                    chat_id=chat_id,
                    doc_uuid=doc_uuid,
                    top_k=top_k,
                )
                if legacy_chunks:
                    legacy_candidates.append(legacy_chunks)
            selected_chunks = self._merge_ranked_chunks(
                question=query_text,
                chunk_groups=legacy_candidates,
                top_k=top_k,
            )

        if not selected_chunks or not self._is_confident_enough(query_text, selected_chunks):
            return QueryResult(
                answer="No accessible data found for your role",
                explanation="The agent searched accessible documents, including rewritten retrieval attempts, but did not find a strong enough grounded match for this question.",
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
