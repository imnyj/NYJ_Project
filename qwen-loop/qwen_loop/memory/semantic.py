"""
Semantic memory: ChromaDB 기반 벡터 검색.
페이퍼 청크, 정의, 인용 정보를 저장해 RAG grounding에 사용.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions


class SemanticMemory:
    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection: str = "papers",
        embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embed_model
        )
        self.coll = self.client.get_or_create_collection(
            name=collection, embedding_function=embedder
        )

    def add(self, texts: list[str], metadatas: list[dict[str, Any]] | None = None) -> list[str]:
        ids = [str(uuid.uuid4()) for _ in texts]
        self.coll.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )
        return ids

    def search(self, query: str, k: int = 5, filter: dict | None = None) -> list[dict]:
        res = self.coll.query(
            query_texts=[query], n_results=k, where=filter,
        )
        out = []
        for i in range(len(res["ids"][0])):
            out.append(
                {
                    "id": res["ids"][0][i],
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "distance": res["distances"][0][i] if "distances" in res else None,
                }
            )
        return out

    def count(self) -> int:
        return self.coll.count()
