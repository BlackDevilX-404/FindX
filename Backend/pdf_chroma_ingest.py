import json
import re
import uuid
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


def split_paragraphs(text):
    return [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 40]


def sentence_chunks(text):
    return re.split(r"(?<=[.!?])\s+", text)


def sliding_chunks(tokens, size=420, overlap=120):
    i = 0
    while i < len(tokens):
        yield tokens[i : i + size]
        i += size - overlap


class ChromaMultimodalDB:
    def __init__(self, chat_id, doc_uuid=None):
        self.data = {}
        self.chat_id = chat_id
        self.doc_uuid = doc_uuid
        self.collection_name = f"chat_{chat_id}"
        self.base_dir = Path(__file__).resolve().parent

        self.client = chromadb.PersistentClient(path="./chroma_db_storage")
        self.collection = self.client.get_or_create_collection(self.collection_name)

        print(f"[Chroma] Using collection: {self.collection_name}")
        print("[Chroma] Loading text embedding model...")
        self.text_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        print("[Chroma] Text embedding model loaded successfully.")

        if self.doc_uuid:
            self.json_path = self.base_dir / "jsons" / f"{self.doc_uuid}.json"
            self.image_dir = self.base_dir / "jsons" / "ExtractedImages" / self.doc_uuid
            if self.json_path.exists():
                print(f"[Chroma] Loading extracted JSON: {self.json_path}")
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                print("[Chroma] Extracted JSON loaded successfully.")
            else:
                print(f"[Chroma] Extracted JSON not found: {self.json_path}")

    def ingest_text(self):
        print(f"[Ingest] Starting text ingestion for doc: {self.doc_uuid}")
        chunk_count = 0

        for page, content in self.data.items():
            raw_text = content.get("text", "")
            images = content.get("images", [])

            for p_id, para in enumerate(split_paragraphs(raw_text)):
                tokens = " ".join(sentence_chunks(para)).split()

                for w_id, token_chunk in enumerate(sliding_chunks(tokens)):
                    chunk_text = " ".join(token_chunk)
                    emb = self.text_model.encode(chunk_text).tolist()
                    cid = f"{self.chat_id}_{uuid.uuid4()}"

                    self.collection.add(
                        ids=[cid],
                        documents=[chunk_text],
                        embeddings=[emb],
                        metadatas=[
                            {
                                "chat_id": self.chat_id,
                                "doc_uuid": self.doc_uuid,
                                "page": page,
                                "paragraph": p_id,
                                "window": w_id,
                                "images": ",".join(images),
                                "type": "text",
                            }
                        ],
                    )
                    chunk_count += 1

        print(f"[Ingest] Text chunks stored successfully. Total chunks: {chunk_count}")

    def ingest_images(self):
        print("[Ingest] Image ingestion skipped. Images are saved to disk but not embedded right now.")

    def ingest_all(self):
        self.ingest_text()
        self.ingest_images()
        print("[Ingest] Ingestion pipeline completed.")

    def query_text(self, query, top_k=3):
        print(f"[Retrieve] Running text query with top_k={top_k}")
        q_emb = self.text_model.encode(query).tolist()
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where={"chat_id": {"$eq": self.chat_id}},
        )
        result = res["documents"][0] if res["documents"] else []
        print(f"[Retrieve] Text query completed. Chunks returned: {len(result)}")
        return result

    def query_grouped(self, question, top_k=3, only_doc=None):
        print(f"[Retrieve] Retrieving grouped chunks with top_k={top_k}")
        q_emb = self.text_model.encode(question).tolist()

        where_filter = {"chat_id": {"$eq": self.chat_id}}
        if only_doc:
            where_filter = {
                "$and": [
                    {"chat_id": {"$eq": self.chat_id}},
                    {"doc_uuid": {"$eq": only_doc}},
                ]
            }

        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas"],
        )

        grouped = {}
        if res["documents"]:
            for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
                doc_id = meta.get("doc_uuid", "unknown")
                grouped.setdefault(doc_id, []).append(doc)

        print(f"[Retrieve] Retrieval completed successfully. Matched documents: {len(grouped)}")
        return grouped
