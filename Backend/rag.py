import os
import json
import re
import uuid
import csv
from dataclasses import dataclass, replace
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
    from .db import list_document_records
    from .pdf_chroma_ingest import ChromaMultimodalDB
    from .process_ppt import Ppt2Pdf
except ImportError:
    from auth import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_HR
    from db import list_document_records
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
FILE_REFERENCE_PATTERN = re.compile(r"\b[\w.-]+\.(pdf|ppt|pptx|docx|txt|md|csv|json|xlsx)\b", re.IGNORECASE)
DEFAULT_AGENT_TOP_K = 4
MIN_AGENT_TOP_K = 2
MAX_AGENT_TOP_K = 8
MAX_AGENT_STEPS = 3
TARGET_CHUNK_TOKENS = 280
CHUNK_OVERLAP_TOKENS = 60
SHORT_PARAGRAPH_WORDS = 45
MAX_EXPANDED_CONTEXT_TOKENS = 360


class SourceItem(BaseModel):
    id: str
    document: str
    doc_uuid: str
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
    id: str
    document_id: str
    document: str
    category: str
    sensitivity: str | None
    page: Optional[int]
    paragraph: Optional[int]
    window: Optional[int]
    text: str
    score: float
    semantic_score: float
    lexical_score: float
    retrieval_query: str


@dataclass
class PlannedQuery:
    text: str
    reason: str


@dataclass
class RetrievalAction:
    action: str
    query: str
    top_k: int
    document_id: Optional[str]
    reason: str


def _normalize_unicode(text: str) -> str:
    return (
        (text or "")
        .replace("\u2022", "- ")
        .replace("\u25cf", "- ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
        .replace("\u200b", "")
    )


def normalize_text(text: str) -> str:
    normalized = _normalize_unicode(text)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_structured_text(text: str) -> str:
    normalized = _normalize_unicode(text).replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[str] = []

    for raw_block in re.split(r"\n{2,}", normalized):
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_block.split("\n")]
        block_text = " ".join(line for line in lines if line)
        if block_text:
            blocks.append(block_text)

    return "\n\n".join(blocks).strip()


def split_paragraphs(text: str) -> list[str]:
    structured = normalize_structured_text(text)
    paragraphs = [normalize_text(paragraph) for paragraph in re.split(r"\n{2,}", structured) if paragraph.strip()]
    if paragraphs:
        return paragraphs

    normalized = normalize_text(text)
    return [normalized] if normalized else []


def sentence_chunks(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def sliding_chunks(
    tokens: list[str],
    size: int = TARGET_CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
):
    index = 0
    while index < len(tokens):
        yield tokens[index : index + size]
        index += size - overlap


def extract_keywords(text: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall((text or "").lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def keyword_overlap(question: str, text: str) -> float:
    question_terms = extract_keywords(question)
    if not question_terms:
        return 0.0

    text_terms = extract_keywords(text)
    if not text_terms:
        return 0.0

    return len(question_terms & text_terms) / len(question_terms)


def keyword_density(question: str, text: str) -> float:
    question_terms = extract_keywords(question)
    if not question_terms:
        return 0.0

    text_terms = [token for token in WORD_PATTERN.findall((text or "").lower()) if len(token) > 2]
    if not text_terms:
        return 0.0

    match_count = sum(1 for token in text_terms if token in question_terms)
    return min((match_count / max(len(text_terms), 1)) * 14, 1.0)


def is_heading_like(text: str) -> bool:
    normalized = normalize_text(text)
    words = normalized.split()
    if not words:
        return True

    if len(normalized) <= 60 and len(words) <= 8:
        return True

    if len(words) <= 10 and normalized.upper() == normalized:
        return True

    return not any(punctuation in normalized for punctuation in ".!?") and len(words) <= 6


def merge_short_paragraphs(paragraphs: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0

    while index < len(paragraphs):
        current = normalize_text(paragraphs[index])
        if not current:
            index += 1
            continue

        while index + 1 < len(paragraphs):
            next_paragraph = normalize_text(paragraphs[index + 1])
            if not next_paragraph:
                index += 1
                continue

            combined = normalize_text(f"{current}\n{next_paragraph}")
            combined_words = len(combined.split())
            if is_heading_like(current):
                current = combined
                index += 1
                break

            if len(current.split()) < SHORT_PARAGRAPH_WORDS and combined_words <= TARGET_CHUNK_TOKENS:
                current = combined
                index += 1
                if len(current.split()) >= TARGET_CHUNK_TOKENS // 2:
                    break
                continue

            break

        merged.append(current)
        index += 1

    return merged


def coerce_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    text_value = str(value).strip()
    if not text_value:
        return None
    if text_value.isdigit():
        return int(text_value)

    match = re.search(r"(\d+)$", text_value)
    return int(match.group(1)) if match else None


def clamp_top_k(value: Any, default: int = DEFAULT_AGENT_TOP_K) -> int:
    if isinstance(value, bool):
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    return max(MIN_AGENT_TOP_K, min(MAX_AGENT_TOP_K, parsed))


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


def build_access_where_filter(
    allowed_categories: list[str],
    allowed_visibility_scopes: list[str],
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    category_filter = build_category_where_filter(allowed_categories)
    visibility_filter = {"visibility_scope": {"$in": sorted({scope.lower() for scope in allowed_visibility_scopes})}}
    filters: list[dict[str, Any]] = [category_filter, visibility_filter]
    if document_ids:
        filters.append({"document_id": {"$in": sorted(set(document_ids))}})
    elif document_id:
        filters.append({"document_id": {"$eq": document_id}})
    return {"$and": filters}


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
        self._document_chunk_cache: dict[str, list[dict[str, Any]]] = {}

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

        return [{"page": 1, "text": normalize_structured_text(combined)}]

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

                sheet_text = normalize_structured_text(f"Sheet: {sheet.title}\n\n" + "\n".join(rows))
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

        normalized = normalize_structured_text(text)
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

        try:
            for page_number, page in enumerate(document, start=1):
                blocks: list[str] = []
                for block in page.get_text("blocks", sort=True):
                    if len(block) < 5:
                        continue

                    block_text = normalize_structured_text(block[4])
                    if block_text:
                        blocks.append(block_text)

                page_text = "\n\n".join(blocks).strip()
                if page_text:
                    pages.append({"page": page_number, "text": page_text})
        finally:
            document.close()

        return pages

    def _chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []

        for page in pages:
            paragraphs = merge_short_paragraphs(split_paragraphs(page["text"]))
            for paragraph_index, paragraph in enumerate(paragraphs):
                tokens = normalize_text(" ".join(sentence_chunks(paragraph))).split()
                if not tokens:
                    continue

                token_windows = [tokens] if len(tokens) <= TARGET_CHUNK_TOKENS else sliding_chunks(tokens)
                for window_index, token_window in enumerate(token_windows):
                    chunk_text = normalize_text(" ".join(token_window))
                    if len(chunk_text) >= 30:
                        chunks.append(
                            {
                                "page": page["page"],
                                "paragraph": paragraph_index,
                                "window": window_index,
                                "text": chunk_text,
                            }
                        )

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
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        self.collection.add(
            ids=[
                f"{document_id}:{chunk['page']}:{chunk['paragraph']}:{chunk['window']}"
                for chunk in chunks
            ],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                build_metadata_payload(
                    {
                        "chunk_id": f"{document_id}:{chunk['page']}:{chunk['paragraph']}:{chunk['window']}",
                        "document_id": document_id,
                        "document": document_name,
                        "category": validated_category,
                        "sensitivity": sensitivity,
                        "visibility_scope": validated_visibility_scope,
                        "page": chunk["page"],
                        "paragraph": chunk["paragraph"],
                        "window": chunk["window"],
                        "char_count": len(chunk["text"]),
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

    @staticmethod
    def _select_top_chunks(
        chunks: list[RetrievedChunk],
        top_k: int,
        max_per_document: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        selected: list[RetrievedChunk] = []
        seen: set[tuple[str, Optional[int], Optional[int], Optional[int], str]] = set()
        per_document_counts: dict[str, int] = {}

        for chunk in chunks:
            fingerprint = (
                chunk.document_id,
                chunk.page,
                chunk.paragraph,
                chunk.window,
                chunk.text[:180],
            )
            if fingerprint in seen:
                continue

            current_count = per_document_counts.get(chunk.document_id, 0)
            if max_per_document is not None and current_count >= max_per_document:
                continue

            selected.append(chunk)
            seen.add(fingerprint)
            per_document_counts[chunk.document_id] = current_count + 1
            if len(selected) >= top_k:
                break

        return selected

    def _rank_chunks(
        self,
        question: str,
        results: dict[str, Any],
        query_text: str,
    ) -> list[RetrievedChunk]:
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        ranked_chunks: list[RetrievedChunk] = []
        for index, (document_text, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
            if not document_text or not metadata:
                continue

            text = normalize_text(document_text)
            if not text:
                continue

            semantic_score = 1.0 / (1.0 + max(float(distance or 0.0), 0.0))
            lexical_score = keyword_overlap(question, text)
            density_score = keyword_density(question, text)
            combined_score = round((semantic_score * 0.64) + (lexical_score * 0.24) + (density_score * 0.12), 4)
            document_id = str(metadata.get("document_id") or metadata.get("doc_uuid") or "unknown")
            page = coerce_optional_int(metadata.get("page"))
            paragraph = coerce_optional_int(metadata.get("paragraph"))
            window = coerce_optional_int(metadata.get("window"))
            chunk_id = str(
                metadata.get("chunk_id")
                or f"{document_id}:{page or 'na'}:{paragraph or 0}:{window or 0}:{index}"
            )

            ranked_chunks.append(
                RetrievedChunk(
                    id=chunk_id,
                    document_id=document_id,
                    document=str(metadata.get("document") or "Unknown document"),
                    category=normalize_category_value(metadata.get("category") or "GENERAL"),
                    sensitivity=metadata.get("sensitivity"),
                    page=page,
                    paragraph=paragraph,
                    window=window,
                    text=text,
                    score=combined_score,
                    semantic_score=semantic_score,
                    lexical_score=lexical_score,
                    retrieval_query=query_text,
                )
            )

        ranked_chunks.sort(
            key=lambda item: (
                item.score,
                item.lexical_score,
                item.semantic_score,
            ),
            reverse=True,
        )
        return ranked_chunks

    def _load_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        if document_id in self._document_chunk_cache:
            return self._document_chunk_cache[document_id]

        results = self.collection.get(
            where={"document_id": {"$eq": document_id}},
            include=["documents", "metadatas"],
        )

        records: list[dict[str, Any]] = []
        for document_text, metadata in zip(results.get("documents") or [], results.get("metadatas") or []):
            if not document_text or not metadata:
                continue

            text = normalize_text(document_text)
            if not text:
                continue

            records.append(
                {
                    "text": text,
                    "page": coerce_optional_int(metadata.get("page")),
                    "paragraph": coerce_optional_int(metadata.get("paragraph")),
                    "window": coerce_optional_int(metadata.get("window")),
                }
            )

        records.sort(
            key=lambda item: (
                item["page"] or 0,
                item["paragraph"] or 0,
                item["window"] or 0,
            )
        )
        self._document_chunk_cache[document_id] = records
        return records

    def _expand_chunk_context(self, question: str, chunk: RetrievedChunk) -> RetrievedChunk:
        if not chunk.document_id or chunk.page is None:
            return chunk

        document_chunks = self._load_document_chunks(chunk.document_id)
        if not document_chunks:
            return chunk

        neighboring_texts: list[str] = []
        total_tokens = 0

        for record in document_chunks:
            if record["page"] != chunk.page:
                continue

            if chunk.paragraph is not None and record["paragraph"] is not None:
                if abs(record["paragraph"] - chunk.paragraph) > 1:
                    continue
                if (
                    record["paragraph"] == chunk.paragraph
                    and chunk.window is not None
                    and record["window"] is not None
                    and abs(record["window"] - chunk.window) > 1
                ):
                    continue
            elif neighboring_texts and total_tokens >= MAX_EXPANDED_CONTEXT_TOKENS:
                break

            record_text = record["text"]
            if not record_text or record_text in neighboring_texts:
                continue

            record_tokens = record_text.split()
            if neighboring_texts and total_tokens + len(record_tokens) > MAX_EXPANDED_CONTEXT_TOKENS:
                break

            neighboring_texts.append(record_text)
            total_tokens += len(record_tokens)

        expanded_text = normalize_text(" ".join(neighboring_texts))
        if not expanded_text:
            return chunk

        expanded_overlap = keyword_overlap(question, expanded_text)
        if len(expanded_text) <= len(chunk.text):
            return chunk

        if (
            expanded_overlap >= chunk.lexical_score
            or len(chunk.text) < 180
            or is_heading_like(chunk.text)
        ):
            density_score = keyword_density(question, expanded_text)
            updated_score = round(
                (chunk.semantic_score * 0.64) + (expanded_overlap * 0.24) + (density_score * 0.12),
                4,
            )
            return replace(
                chunk,
                text=expanded_text,
                lexical_score=expanded_overlap,
                score=updated_score,
            )

        return chunk

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
    def _document_record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
        updated_at = str(record.get("updated_at") or "")
        created_at = str(record.get("created_at") or "")
        return updated_at, created_at

    def _get_active_document_records(self, role: str) -> list[dict[str, Any]]:
        allowed_categories = allowed_categories_for_role(role)
        allowed_visibility_scopes = allowed_visibility_scopes_for_role(role)
        records: list[dict[str, Any]] = []

        for record in list_document_records():
            document_id = str(record.get("document_id") or "").strip()
            if not document_id:
                continue
            if not category_matches_allowed(record.get("category"), allowed_categories):
                continue
            if not visibility_matches_allowed(record.get("visibility_scope"), allowed_visibility_scopes):
                continue
            records.append(record)

        return records

    def _resolve_fixed_document_id(
        self,
        query_text: str,
        role: str,
        requested_document_id: str | None = None,
    ) -> str | None:
        active_records = self._get_active_document_records(role)
        active_ids = {
            str(record.get("document_id") or "").strip()
            for record in active_records
            if str(record.get("document_id") or "").strip()
        }

        if requested_document_id:
            return requested_document_id if requested_document_id in active_ids else None

        normalized_query = normalize_text(query_text).lower()
        if not normalized_query:
            return None

        exact_matches: list[dict[str, Any]] = []
        stem_matches: list[dict[str, Any]] = []

        for record in active_records:
            document_name = str(record.get("document") or "").strip()
            if not document_name:
                continue

            full_name = document_name.lower()
            stem_name = Path(document_name).stem.lower()

            if full_name and full_name in normalized_query:
                exact_matches.append(record)
                continue

            if stem_name and len(stem_name) >= 4 and stem_name in normalized_query:
                stem_matches.append(record)

        matches = exact_matches or stem_matches
        if not matches:
            return None

        matches.sort(key=self._document_record_sort_key, reverse=True)
        resolved_id = str(matches[0].get("document_id") or "").strip()
        return resolved_id or None

    @staticmethod
    def _query_mentions_specific_document(query_text: str) -> bool:
        return bool(FILE_REFERENCE_PATTERN.search(query_text or ""))

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

    @staticmethod
    def _heuristic_top_k(query_text: str, fallback: int = DEFAULT_AGENT_TOP_K) -> int:
        base_top_k = clamp_top_k(fallback, DEFAULT_AGENT_TOP_K)
        lowered = query_text.lower()

        if any(
            marker in lowered
            for marker in ("compare", "difference", "different", "list", "all", "summary", "summarize", "steps")
        ):
            return clamp_top_k(max(base_top_k, 6), base_top_k)

        if len(query_text.split()) <= 6:
            return clamp_top_k(max(MIN_AGENT_TOP_K, base_top_k - 1), base_top_k)

        return base_top_k

    @staticmethod
    def _extract_json_object(payload: str) -> dict[str, Any]:
        text = (payload or "").strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced_match:
            text = fenced_match.group(1)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model output.")

        return json.loads(text[start : end + 1])

    def _parse_retrieval_action(
        self,
        payload: str,
        default_query: str,
        default_top_k: int,
        fixed_document_id: str | None = None,
    ) -> RetrievalAction:
        fallback = RetrievalAction(
            action="search",
            query=default_query,
            top_k=clamp_top_k(default_top_k, DEFAULT_AGENT_TOP_K),
            document_id=fixed_document_id,
            reason="fallback retrieval plan",
        )

        try:
            parsed = self._extract_json_object(payload)
        except (ValueError, json.JSONDecodeError, TypeError):
            return fallback

        action = str(parsed.get("action") or "search").strip().lower()
        if action not in {"search", "finish"}:
            action = "search"

        query = normalize_text(parsed.get("query") or default_query) or default_query
        document_id = fixed_document_id
        if not document_id:
            raw_document_id = str(parsed.get("document_id") or "").strip()
            document_id = raw_document_id or None
            if document_id and document_id.lower() in {"none", "null"}:
                document_id = None

        return RetrievalAction(
            action=action,
            query=query,
            top_k=clamp_top_k(parsed.get("top_k"), default_top_k),
            document_id=document_id,
            reason=normalize_text(parsed.get("reason") or "") or fallback.reason,
        )

    @staticmethod
    def _build_retrieval_observation(
        query_text: str,
        document_id: str | None,
        chunks: list[RetrievedChunk],
    ) -> str:
        if not chunks:
            scoped_document = document_id or "all accessible documents"
            return f'Search(query="{query_text}", document_id="{scoped_document}") returned no matches.'

        document_summaries: dict[str, dict[str, Any]] = {}
        for chunk in chunks:
            summary = document_summaries.setdefault(
                chunk.document_id,
                {"document": chunk.document, "count": 0, "best_score": 0.0},
            )
            summary["count"] += 1
            summary["best_score"] = max(summary["best_score"], chunk.score)

        lines = [
            f'Search(query="{query_text}", document_id="{document_id or "all"}") returned {len(chunks)} chunk(s).',
            "Document coverage: "
            + "; ".join(
                f'{value["document"]} [{doc_id}] x{value["count"]}, best={value["best_score"]:.3f}'
                for doc_id, value in document_summaries.items()
            ),
        ]

        for chunk in chunks[:6]:
            page_label = f"page {chunk.page}" if chunk.page else "page unavailable"
            lines.append(
                f'- {chunk.document} [{chunk.document_id}] | {page_label} | score {chunk.score:.3f} | {chunk.text[:160]}'
            )

        return "\n".join(lines)

    def _plan_retrieval_action(
        self,
        query_text: str,
        chat_history: list[dict[str, str]],
        observations: list[str],
        step: int,
        fixed_document_id: str | None,
        default_top_k: int,
    ) -> RetrievalAction:
        default_query = normalize_text(query_text) or query_text
        observation_block = "\n\n".join(observations[-2:]) if observations else "No retrieval observations yet."

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "You control retrieval for an enterprise RAG system. "
                            "Pick one next action and return JSON only. "
                            "Allowed actions: "
                            "search = call the retrieval tool with a focused query and a top_k between 2 and 8; "
                            "finish = stop retrieving because the evidence is already sufficient. "
                            "Use lower top_k for narrow factual lookups, medium top_k for policy questions, and higher top_k for comparisons, lists, or ambiguous questions. "
                            "If one document clearly dominates, use its exact document_id to focus the next search. "
                            "Never invent a document_id. "
                            'Return JSON with keys: action, query, top_k, document_id, reason.'
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"User question:\n{default_query}\n\n"
                            f"Recent conversation:\n{self._history_to_text(chat_history)}\n\n"
                            f"Current step: {step} of {MAX_AGENT_STEPS}\n"
                            f"Fixed document_id filter: {fixed_document_id or 'none'}\n\n"
                            f"Observations:\n{observation_block}"
                        )
                    ),
                ]
            )
            return self._parse_retrieval_action(
                payload=self._read_llm_text(response.content),
                default_query=default_query,
                default_top_k=default_top_k,
                fixed_document_id=fixed_document_id,
            )
        except Exception:
            return RetrievalAction(
                action="search",
                query=default_query,
                top_k=clamp_top_k(default_top_k, DEFAULT_AGENT_TOP_K),
                document_id=fixed_document_id,
                reason="fallback retrieval plan",
            )

    def _filter_results_by_access(
        self,
        results: dict[str, Any],
        allowed_categories: list[str],
        allowed_visibility_scopes: list[str],
        document_id: str | None = None,
        active_document_ids: set[str] | None = None,
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
            metadata_document_id = str(metadata.get("document_id") or "").strip()
            if document_id and metadata_document_id != document_id:
                continue
            if active_document_ids is not None and metadata_document_id not in active_document_ids:
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

    def _query_enterprise_chunks(
        self,
        query_text: str,
        role: str,
        top_k: int,
        document_id: str | None = None,
        fetch_k: int | None = None,
        max_per_document: int | None = None,
    ) -> list[RetrievedChunk]:
        active_records = self._get_active_document_records(role)
        active_document_ids = {
            str(record.get("document_id") or "").strip()
            for record in active_records
            if str(record.get("document_id") or "").strip()
        }
        if not active_document_ids:
            return []

        if document_id and document_id not in active_document_ids:
            return []

        requested_top_k = clamp_top_k(top_k, DEFAULT_AGENT_TOP_K)
        query_embedding = self.embedder.encode(
            query_text,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        effective_fetch_k = fetch_k or max(requested_top_k * 6, 24)
        filtered_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_fetch_k,
            where=build_access_where_filter(
                allowed_categories_for_role(role),
                allowed_visibility_scopes_for_role(role),
                document_id=document_id,
                document_ids=sorted(active_document_ids) if not document_id else None,
            ),
            include=["documents", "metadatas", "distances"],
        )
        ranked_chunks = self._rank_chunks(query_text, filtered_results, query_text=query_text)
        if ranked_chunks:
            return self._select_top_chunks(
                ranked_chunks,
                top_k=requested_top_k,
                max_per_document=max_per_document,
            )

        if self.collection.count() == 0:
            return []

        compatibility_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_fetch_k,
            include=["documents", "metadatas", "distances"],
        )
        locally_filtered = self._filter_results_by_access(
            compatibility_results,
            allowed_categories=allowed_categories_for_role(role),
            allowed_visibility_scopes=allowed_visibility_scopes_for_role(role),
            document_id=document_id,
            active_document_ids=active_document_ids,
        )
        ranked_chunks = self._rank_chunks(query_text, locally_filtered, query_text=query_text)
        return self._select_top_chunks(
            ranked_chunks,
            top_k=requested_top_k,
            max_per_document=max_per_document,
        )

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

    def delete_document(self, document_id: str) -> bool:
        results = self.collection.get(
            where={"document_id": {"$eq": document_id}},
            include=[],
        )
        ids = results.get("ids") or []
        if ids:
            self.collection.delete(ids=ids)

        self._document_chunk_cache.pop(document_id, None)
        return bool(ids)

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
                id=chunk.source_id,
                document_id=chunk.doc_uuid,
                document=chunk.source_name,
                category="LEGACY",
                sensitivity=None,
                page=chunk.page,
                paragraph=chunk.paragraph,
                window=chunk.window,
                text=normalize_text(chunk.text),
                score=chunk.score,
                semantic_score=chunk.score,
                lexical_score=keyword_overlap(query_text, chunk.text),
                retrieval_query=query_text,
            )
            for chunk in legacy_chunks
            if normalize_text(chunk.text)
        ]

    @staticmethod
    def _merge_ranked_chunks(question: str, chunk_groups: list[list[RetrievedChunk]], top_k: int) -> list[RetrievedChunk]:
        scored: list[RetrievedChunk] = []
        seen: set[tuple[str, Optional[int], Optional[int], Optional[int], str]] = set()

        for chunk_group in chunk_groups:
            for chunk in chunk_group:
                fingerprint = (
                    chunk.document_id,
                    chunk.page,
                    chunk.paragraph,
                    chunk.window,
                    chunk.text[:180],
                )
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                rescored = round((chunk.score * 0.82) + (keyword_overlap(question, chunk.text) * 0.18), 4)
                scored.append(replace(chunk, score=rescored))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _finalize_selected_chunks(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        rescored: list[RetrievedChunk] = []

        for chunk in chunks:
            expanded_chunk = chunk if chunk.category == "LEGACY" else self._expand_chunk_context(question, chunk)
            overlap_score = keyword_overlap(question, expanded_chunk.text)
            density_score = keyword_density(question, expanded_chunk.text)
            updated_score = round(
                (expanded_chunk.semantic_score * 0.60) + (overlap_score * 0.26) + (density_score * 0.14),
                4,
            )
            rescored.append(
                replace(
                    expanded_chunk,
                    lexical_score=overlap_score,
                    score=updated_score,
                )
            )

        rescored.sort(
            key=lambda item: (
                item.score,
                item.lexical_score,
                item.semantic_score,
            ),
            reverse=True,
        )
        return self._select_top_chunks(rescored, top_k=top_k)

    def _run_agentic_enterprise_retrieval(
        self,
        query_text: str,
        role: str,
        chat_history: list[dict[str, str]],
        doc_uuid: str | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        desired_top_k = self._heuristic_top_k(query_text, top_k)
        observations: list[str] = []
        candidate_groups: list[list[RetrievedChunk]] = []

        for step in range(1, MAX_AGENT_STEPS + 1):
            action = self._plan_retrieval_action(
                query_text=query_text,
                chat_history=chat_history,
                observations=observations,
                step=step,
                fixed_document_id=doc_uuid,
                default_top_k=desired_top_k,
            )
            desired_top_k = clamp_top_k(action.top_k, desired_top_k)

            if action.action == "finish" and candidate_groups:
                break

            scoped_document_id = doc_uuid or action.document_id
            max_per_document = None if scoped_document_id else max(2, min(3, desired_top_k // 2 + 1))
            chunks = self._query_enterprise_chunks(
                query_text=action.query or query_text,
                role=role,
                top_k=desired_top_k,
                document_id=scoped_document_id,
                fetch_k=max(desired_top_k * 6, 24),
                max_per_document=max_per_document,
            )
            observations.append(
                self._build_retrieval_observation(
                    query_text=action.query or query_text,
                    document_id=scoped_document_id,
                    chunks=chunks,
                )
            )

            if not chunks:
                continue

            candidate_groups.append(chunks)
            merged_chunks = self._merge_ranked_chunks(
                question=query_text,
                chunk_groups=candidate_groups,
                top_k=desired_top_k,
            )
            if self._is_confident_enough(query_text, merged_chunks):
                return self._finalize_selected_chunks(query_text, merged_chunks, top_k=desired_top_k)

        if candidate_groups:
            merged_chunks = self._merge_ranked_chunks(
                question=query_text,
                chunk_groups=candidate_groups,
                top_k=desired_top_k,
            )
            return self._finalize_selected_chunks(query_text, merged_chunks, top_k=desired_top_k)

        planned_queries = self._plan_queries(query_text, chat_history)
        fallback_groups: list[list[RetrievedChunk]] = []
        for planned_query in planned_queries:
            chunks = self._query_enterprise_chunks(
                query_text=planned_query.text,
                role=role,
                top_k=desired_top_k,
                document_id=doc_uuid,
                fetch_k=max(desired_top_k * 6, 24),
                max_per_document=None if doc_uuid else max(2, min(3, desired_top_k // 2 + 1)),
            )
            if chunks:
                fallback_groups.append(chunks)

        if not fallback_groups:
            return []

        merged_chunks = self._merge_ranked_chunks(
            question=query_text,
            chunk_groups=fallback_groups,
            top_k=desired_top_k,
        )
        return self._finalize_selected_chunks(query_text, merged_chunks, top_k=desired_top_k)

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
        resolved_doc_uuid = self._resolve_fixed_document_id(
            query_text=query_text,
            role=normalized_role,
            requested_document_id=doc_uuid,
        )
        if (doc_uuid and not resolved_doc_uuid) or (
            not doc_uuid and self._query_mentions_specific_document(query_text) and not resolved_doc_uuid
        ):
            return QueryResult(
                answer="No accessible data found for your role",
                explanation="The request explicitly referenced a document that is deleted, unavailable, or outside your access scope.",
                sources=[],
            )
        selected_chunks = self._run_agentic_enterprise_retrieval(
            query_text=query_text,
            role=normalized_role,
            chat_history=normalized_history,
            doc_uuid=resolved_doc_uuid,
            top_k=top_k,
        )

        if not selected_chunks:
            planned_queries = self._plan_queries(query_text, normalized_history)
            legacy_candidates: list[list[RetrievedChunk]] = []
            for planned_query in planned_queries:
                legacy_chunks = self._query_legacy_chunks(
                    query_text=planned_query.text,
                    chat_id=chat_id,
                    doc_uuid=resolved_doc_uuid,
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
                id=chunk.id,
                document=chunk.document,
                doc_uuid=chunk.document_id,
                snippet=chunk.text[:480],
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
