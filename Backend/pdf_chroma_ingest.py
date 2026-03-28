import os
import json
import re
import uuid
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Optional

import chromadb
from huggingface_hub.utils import disable_progress_bars
from huggingface_hub.utils import logging as hf_logging
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as transformers_logging

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
hf_logging.set_verbosity_error()
transformers_logging.set_verbosity_error()
disable_progress_bars()
transformers_logging.disable_progress_bar()

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
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "pdf",
    "please",
    "rule",
    "rules",
    "say",
    "says",
    "the",
    "tell",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
}


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 40]


def sentence_chunks(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def sliding_chunks(tokens: list[str], size: int = 420, overlap: int = 120):
    i = 0
    while i < len(tokens):
        yield tokens[i : i + size]
        i += size - overlap


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


def sanitize_collection_name(raw_value: str) -> str:
    raw_value = (raw_value or "").strip()
    legacy_name = f"chat_{raw_value}"
    if (
        3 <= len(legacy_name) <= 512
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]", legacy_name)
    ):
        return legacy_name

    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw_value.lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("._-")

    if not cleaned:
        cleaned = "workspace"

    digest = sha1((raw_value or "workspace").encode("utf-8")).hexdigest()[:8]
    prefix = "chat_"
    suffix = f"-{digest}"
    max_clean_length = 512 - len(prefix) - len(suffix)
    cleaned = cleaned[:max_clean_length].rstrip("._-") or "workspace"

    name = f"{prefix}{cleaned}{suffix}"

    if not name[0].isalnum():
        name = f"c{name[1:]}"
    if not name[-1].isalnum():
        name = f"{name[:-1]}0"

    return name


def extract_keywords(text: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall((text or "").lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def coerce_page_number(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    text_value = str(value).strip()
    if text_value.isdigit():
        return int(text_value)

    match = re.search(r"(\d+)$", text_value)
    return int(match.group(1)) if match else None


def confidence_label(score: float) -> str:
    percentage = max(0, min(99, round(score * 100)))
    return f"{percentage}%"


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


@dataclass
class RetrievedChunk:
    source_id: str
    doc_uuid: str
    source_name: str
    page: Optional[int]
    paragraph: Optional[int]
    window: Optional[int]
    text: str
    distance: float
    score: float
    confidence: str

    def to_source_payload(self) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "doc": self.source_name,
            "doc_uuid": self.doc_uuid,
            "page": self.page,
            "confidence": self.confidence,
            "text": self.text,
        }


class ChromaMultimodalDB:
    _client = None
    _text_model: Optional[SentenceTransformer] = None
    _json_cache: dict[str, dict[str, Any]] = {}
    _title_cache: dict[str, str] = {}

    def __init__(self, chat_id: str, doc_uuid: Optional[str] = None, source_name: Optional[str] = None):
        self.data: dict[str, Any] = {}
        self.raw_chat_id = str(chat_id)
        self.chat_id = str(chat_id)
        self.doc_uuid = doc_uuid
        self.source_name = source_name
        self.collection_name = sanitize_collection_name(self.chat_id)
        self.base_dir = Path(__file__).resolve().parent
        self.storage_dir = self.base_dir / "chroma_db_storage"

        if ChromaMultimodalDB._client is None:
            ChromaMultimodalDB._client = chromadb.PersistentClient(path=str(self.storage_dir))

        self.client = ChromaMultimodalDB._client
        self.collection = self.client.get_or_create_collection(self.collection_name)

        print(f"[Chroma] Using collection: {self.collection_name}")
        self.text_model = self._get_text_model()

        if self.doc_uuid:
            self.json_path = self.base_dir / "jsons" / f"{self.doc_uuid}.json"
            self.image_dir = self.base_dir / "jsons" / "ExtractedImages" / self.doc_uuid
            if self.json_path.exists():
                print(f"[Chroma] Loading extracted JSON: {self.json_path}")
                with open(self.json_path, "r", encoding="utf-8") as file_handle:
                    self.data = json.load(file_handle)
                self._json_cache[self.doc_uuid] = self.data
                print("[Chroma] Extracted JSON loaded successfully.")
            else:
                print(f"[Chroma] Extracted JSON not found: {self.json_path}")

    @classmethod
    def _get_text_model(cls) -> SentenceTransformer:
        if cls._text_model is None:
            print("[Chroma] Loading text embedding model...")
            cls._text_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
            print("[Chroma] Text embedding model loaded successfully.")
        return cls._text_model

    def _build_where_filter(self, only_doc: Optional[str] = None) -> dict[str, Any]:
        if only_doc:
            return {
                "$and": [
                    {"chat_id": {"$eq": self.chat_id}},
                    {"doc_uuid": {"$eq": only_doc}},
                ]
            }

        return {"chat_id": {"$eq": self.chat_id}}

    def _load_doc_json(self, doc_uuid: str) -> dict[str, Any]:
        if not doc_uuid or doc_uuid == "unknown":
            return {}

        if doc_uuid in self._json_cache:
            return self._json_cache[doc_uuid]

        json_path = self.base_dir / "jsons" / f"{doc_uuid}.json"
        if not json_path.exists():
            self._json_cache[doc_uuid] = {}
            return {}

        with open(json_path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        self._json_cache[doc_uuid] = data
        return data

    def _resolve_page_text(
        self,
        doc_uuid: str,
        page: Optional[int] = None,
        page_label: Optional[str] = None,
    ) -> str:
        data = self._load_doc_json(doc_uuid)
        if not data:
            return ""

        candidate_keys: list[str] = []
        if page_label:
            candidate_keys.append(str(page_label))

        if page is not None:
            candidate_keys.extend([f"page_{page}", str(page)])

        for key in candidate_keys:
            if key in data:
                return normalize_text(data[key].get("text", ""))

        return ""

    def _derive_title_from_json(self, doc_uuid: str) -> str:
        if doc_uuid in self._title_cache:
            return self._title_cache[doc_uuid]

        data = self._load_doc_json(doc_uuid)
        title = ""

        for page_key in sorted(data.keys(), key=coerce_page_number):
            raw_text = str(data.get(page_key, {}).get("text", "") or "")
            for line in raw_text.splitlines():
                normalized_line = normalize_text(line)
                if len(normalized_line.split()) < 3:
                    continue
                if "certificate" in normalized_line.lower():
                    continue
                title = normalized_line[:120]
                break
            if title:
                break

        if not title:
            pdf_path = self.base_dir / "downloads" / f"{doc_uuid}.pdf"
            title = pdf_path.name if pdf_path.exists() else doc_uuid

        self._title_cache[doc_uuid] = title
        return title

    def _resolve_source_name(self, doc_uuid: str, metadata: dict[str, Any]) -> str:
        source_name = str(metadata.get("source_name") or "").strip()
        if source_name and source_name != doc_uuid:
            return source_name
        return self._derive_title_from_json(doc_uuid)

    def _expand_chunk_text(
        self,
        question: str,
        doc_uuid: str,
        page: Optional[int],
        page_label: Optional[str],
        text: str,
    ) -> tuple[str, Optional[int]]:
        best_text = text
        best_page = page

        current_page_text = self._resolve_page_text(doc_uuid, page=page, page_label=page_label)
        if current_page_text:
            if len(current_page_text) > len(best_text) and (
                is_heading_like(best_text) or len(best_text) < 120
            ):
                best_text = current_page_text

        if best_page is None:
            best_page = coerce_page_number(page_label)

        if best_page is None:
            return best_text, best_page

        for offset in (1, -1):
            candidate_page = best_page + offset
            if candidate_page <= 0:
                continue

            candidate_text = self._resolve_page_text(doc_uuid, page=candidate_page)
            if not candidate_text:
                continue

            if is_heading_like(best_text) and len(candidate_text) > len(best_text):
                best_text = candidate_text
                best_page = candidate_page

        return best_text, best_page

    def _delete_existing_doc_chunks(self) -> None:
        if not self.doc_uuid:
            return

        self.collection.delete(where={"doc_uuid": {"$eq": self.doc_uuid}})
        print(f"[Ingest] Cleared existing chunks for doc: {self.doc_uuid}")

    def ingest_text(self) -> None:
        print(f"[Ingest] Starting text ingestion for doc: {self.doc_uuid}")

        if not self.data:
            print("[Ingest] No extracted JSON content found. Skipping text ingestion.")
            return

        self._delete_existing_doc_chunks()

        chunk_texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []
        chunk_count = 0

        resolved_source_name = self.source_name or self.doc_uuid or "Uploaded document"

        for page, content in self.data.items():
            raw_text = content.get("text", "")
            images = content.get("images", [])
            page_number = coerce_page_number(page)
            page_label = str(page)

            for paragraph_index, paragraph in enumerate(split_paragraphs(raw_text)):
                tokens = " ".join(sentence_chunks(paragraph)).split()

                for window_index, token_chunk in enumerate(sliding_chunks(tokens)):
                    chunk_text = normalize_text(" ".join(token_chunk))
                    if not chunk_text:
                        continue

                    chunk_texts.append(chunk_text)
                    ids.append(f"{self.collection_name}-{uuid.uuid4().hex[:12]}")
                    metadatas.append(
                        {
                            "chat_id": self.chat_id,
                            "doc_uuid": self.doc_uuid,
                            "source_name": resolved_source_name,
                            "page": page_number,
                            "page_label": page_label,
                            "paragraph": paragraph_index,
                            "window": window_index,
                            "images": ",".join(images),
                            "type": "text",
                            "char_count": len(chunk_text),
                        }
                    )
                    chunk_count += 1

        if not chunk_texts:
            print("[Ingest] No valid text chunks were produced.")
            return

        embeddings = self.text_model.encode(
            chunk_texts,
            batch_size=24,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        self.collection.add(
            ids=ids,
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(f"[Ingest] Text chunks stored successfully. Total chunks: {chunk_count}")

    def ingest_images(self) -> None:
        print("[Ingest] Image ingestion skipped. Images are saved to disk but not embedded right now.")

    def ingest_all(self) -> None:
        self.ingest_text()
        self.ingest_images()
        print("[Ingest] Ingestion pipeline completed.")

    def query_text(self, query: str, top_k: int = 3) -> list[str]:
        return [chunk.text for chunk in self.query_chunks(query, top_k=top_k)]

    def query_chunks(
        self,
        question: str,
        top_k: int = 4,
        only_doc: Optional[str] = None,
        max_per_doc: int = 2,
        fetch_k: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        print(f"[Retrieve] Retrieving ranked chunks with top_k={top_k}")

        q_emb = self.text_model.encode(question, normalize_embeddings=True).tolist()
        where_filter = self._build_where_filter(only_doc=only_doc)
        n_results = fetch_k or max(top_k * 4, 12)

        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        ranked_candidates: list[RetrievedChunk] = []

        for index, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
            if not document or not metadata:
                continue

            text = normalize_text(document)
            if not text:
                continue

            numeric_distance = float(distance or 0.0)
            semantic_score = 1.0 / (1.0 + max(numeric_distance, 0.0))
            combined_score = round(semantic_score, 4)

            doc_uuid = str(metadata.get("doc_uuid") or "unknown")
            raw_page_value = metadata.get("page_label") or metadata.get("page")
            page = coerce_page_number(raw_page_value)
            paragraph = metadata.get("paragraph")
            window = metadata.get("window")
            source_name = self._resolve_source_name(doc_uuid, metadata)
            expanded_text, expanded_page = self._expand_chunk_text(
                question=question,
                doc_uuid=doc_uuid,
                page=page,
                page_label=str(raw_page_value or "") or None,
                text=text,
            )
            source_id = f"{doc_uuid}:{page or 'na'}:{paragraph or 0}:{window or 0}:{index}"

            ranked_candidates.append(
                RetrievedChunk(
                    source_id=source_id,
                    doc_uuid=doc_uuid,
                    source_name=source_name,
                    page=expanded_page,
                    paragraph=paragraph,
                    window=window,
                    text=expanded_text,
                    distance=numeric_distance,
                    score=combined_score,
                    confidence=confidence_label(combined_score),
                )
            )

        ranked_candidates.sort(key=lambda item: (-item.score, item.distance, item.doc_uuid))

        selected_chunks: list[RetrievedChunk] = []
        seen_keys: set[tuple[str, Optional[int], str]] = set()
        per_document_counts: dict[str, int] = {}

        for chunk in ranked_candidates:
            snippet_key = (chunk.doc_uuid, chunk.page, chunk.text[:180])
            if snippet_key in seen_keys:
                continue

            current_count = per_document_counts.get(chunk.doc_uuid, 0)
            if current_count >= max_per_doc:
                continue

            selected_chunks.append(chunk)
            seen_keys.add(snippet_key)
            per_document_counts[chunk.doc_uuid] = current_count + 1

            if len(selected_chunks) >= top_k:
                break

        print(f"[Retrieve] Retrieval completed successfully. Chunks selected: {len(selected_chunks)}")
        return selected_chunks

    def query_grouped(self, question: str, top_k: int = 3, only_doc: Optional[str] = None) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for chunk in self.query_chunks(question=question, top_k=top_k, only_doc=only_doc):
            grouped.setdefault(chunk.doc_uuid, []).append(chunk.text)

        print(f"[Retrieve] Retrieval completed successfully. Matched documents: {len(grouped)}")
        return grouped
