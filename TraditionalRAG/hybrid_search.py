"""
Hybrid Search - Kết hợp Dense Retrieval (FAISS) và Sparse Retrieval (BM25)
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
from pydantic import ConfigDict
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
from underthesea import word_tokenize
import unicodedata
import re

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid Retriever kết hợp:
    - Dense retrieval: FAISS với semantic embeddings (vector search)
    - Sparse retrieval: BM25 với keyword matching (lexical search)

    Sử dụng Reciprocal Rank Fusion (RRF) để combine results
    """

    def __init__(
        self,
        vectorstore: FAISS,
        documents: List[Document],
        alpha: float = 0.5,
        k: int = 3,
    ):
        """
        Args:
            vectorstore: FAISS vector store cho dense retrieval
            documents: Danh sách tất cả documents để build BM25 index
            alpha: Trọng số cho dense vs sparse (0.5 = cân bằng, >0.5 ưu tiên dense, <0.5 ưu tiên sparse)
            k: Số documents trả về
        """
        self.vectorstore = vectorstore
        self.documents = documents
        self.alpha = alpha
        self.k = k

        # Build BM25 index
        logger.info(f"Đang build BM25 index cho {len(documents)} documents...")
        self._build_bm25_index()
        logger.info("Đã build xong BM25 index")

    def _build_bm25_index(self):
        """
        Build BM25 index từ documents
        """
        # Tokenize documents cho BM25
        tokenized_docs = []
        for doc in self.documents:
            # Simple tokenization (có thể cải thiện với Vietnamese tokenizer)
            tokens = self._tokenize(doc.page_content)
            tokenized_docs.append(tokens)

        # Tạo BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
        self.doc_mapping = {i: doc for i, doc in enumerate(self.documents)}

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text với word segmentation cho Tiếng Việt

        Args:
            text: Văn bản cần tokenize

        Returns:
            List các tokens đã được xử lý
        """
        # Chuẩn hóa Unicode (rất quan trọng cho tiếng việt)
        text = unicodedata.normalize("NFC", text)

        # Word segmentation với underthesea
        segmented_text = word_tokenize(text, format="text")

        # Loại bỏ punctuation nhưng giữ dấu _ để phân biệt từ ghép
        segmented_text = re.sub(r"[^\w\s_]", " ", segmented_text, flags=re.UNICODE)

        # Split thành tokens
        tokens = segmented_text.split()

        # Stopwords tiếng Việt thông dụng
        vietnamese_stopwords = {
            "của",
            "và",
            "các",
            "có",
            "được",
            "cho",
            "từ",
            "với",
            "trong",
            "là",
            "đề",
            "một",
            "này",
            "đó",
            "những",
            "thì",
            "bị",
            "hay",
            "hoặc",
            "vì",
            "nếu",
            "mà",
            "khi",
        }
        # Lọc stopwords và chuyển về lowercase
        filtered_tokens = [token.lower() for token in tokens if token.lower() not in vietnamese_stopwords]
        return filtered_tokens

    def _dense_retrieval(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """
        Dense retrieval sử dụng FAISS (semantic search)
        Returns: List of (document, score) tuples
        """
        try:
            # FAISS similarity search with scores
            results = self.vectorstore.similarity_search_with_score(query, k=k)

            # Convert distance to similarity score (normalize)
            # FAISS trả về L2 distance, chuyển thành similarity
            scored_docs = []
            for doc, distance in results:
                similarity = 1 / (1 + distance)  # Normalize distance to [0, 1]
                scored_docs.append((doc, similarity))

            return scored_docs
        except Exception as e:
            logger.error(f"Lỗi trong dense retrieval: {e}")
            return []

    def _sparse_retrieval(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """
        Sparse retrieval sử dụng BM25 (keyword matching)
        Returns: List of (document, score) tuples
        """
        try:
            # Tokenize query
            query_tokens = self._tokenize(query)

            # Get BM25 scores
            scores = self.bm25.get_scores(query_tokens)

            # Get top-k documents
            top_k_indices = np.argsort(scores)[-k:][::-1]

            # Convert to (document, score) tuples
            scored_docs = []
            for idx in top_k_indices:
                if idx in self.doc_mapping and scores[idx] > 0:
                    doc = self.doc_mapping[idx]
                    score = float(scores[idx])
                    # Normalize BM25 score to [0, 1]
                    normalized_score = min(score / 10.0, 1.0)  # Heuristic normalization
                    scored_docs.append((doc, normalized_score))

            return scored_docs
        except Exception as e:
            logger.error(f"Lỗi trong sparse retrieval: {e}")
            return []

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[Document, float]],
        sparse_results: List[Tuple[Document, float]],
        k: int = 60,
    ) -> List[Tuple[Document, float]]:
        """
        Reciprocal Rank Fusion (RRF) để combine kết quả từ dense và sparse retrieval

        RRF formula: score = sum(1 / (k + rank_i))
        """
        # Create mapping doc_id -> (doc, scores)
        doc_scores = {}

        # Process dense results
        for rank, (doc, score) in enumerate(dense_results, start=1):
            doc_id = id(doc)  # Sử dụng id làm unique identifier
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "rrf_score": 0,
                    "dense_score": 0,
                    "sparse_score": 0,
                }

            rrf_contribution = 1.0 / (k + rank)
            doc_scores[doc_id]["rrf_score"] += self.alpha * rrf_contribution
            doc_scores[doc_id]["dense_score"] = score

        # Process sparse results
        for rank, (doc, score) in enumerate(sparse_results, start=1):
            doc_id = id(doc)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "rrf_score": 0,
                    "dense_score": 0,
                    "sparse_score": 0,
                }

            rrf_contribution = 1.0 / (k + rank)
            doc_scores[doc_id]["rrf_score"] += (1 - self.alpha) * rrf_contribution
            doc_scores[doc_id]["sparse_score"] = score

        # Sort by RRF score
        sorted_docs = sorted(
            doc_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True
        )

        # Return top-k với combined score
        results = []
        for doc_id, scores in sorted_docs[: self.k]:
            doc = scores["doc"]
            # Tạo combined score metadata
            doc.metadata["hybrid_score"] = scores["rrf_score"]
            doc.metadata["dense_score"] = scores["dense_score"]
            doc.metadata["sparse_score"] = scores["sparse_score"]
            results.append((doc, scores["rrf_score"]))

        return results

    def retrieve(self, query: str) -> List[Document]:
        """
        Main retrieval method sử dụng hybrid search

        Returns: List of top-k documents
        """
        logger.info(f"Hybrid search với query: {query[:100]}...")

        # Retrieve from both methods
        # Lấy nhiều hơn k để có đủ documents cho RRF
        fetch_k = self.k * 2

        dense_results = self._dense_retrieval(query, k=fetch_k)
        sparse_results = self._sparse_retrieval(query, k=fetch_k)

        logger.info(
            f"Dense retrieval: {len(dense_results)} docs, Sparse retrieval: {len(sparse_results)} docs"
        )

        # Combine using RRF
        combined_results = self._reciprocal_rank_fusion(dense_results, sparse_results)

        logger.info(f"Hybrid search trả về {len(combined_results)} documents")

        # Return only documents (without scores)
        return [doc for doc, score in combined_results]

    def retrieve_with_scores(self, query: str) -> List[Tuple[Document, float]]:
        """
        Retrieve documents kèm scores
        """
        logger.info(f"Hybrid search với query: {query[:100]}...")

        fetch_k = self.k * 2
        dense_results = self._dense_retrieval(query, k=fetch_k)
        sparse_results = self._sparse_retrieval(query, k=fetch_k)

        combined_results = self._reciprocal_rank_fusion(dense_results, sparse_results)

        logger.info(
            f"Hybrid search trả về {len(combined_results)} documents with scores"
        )
        return combined_results

    def update_documents(self, new_documents: List[Document]):
        """
        Update BM25 index khi có documents mới
        """
        self.documents.extend(new_documents)
        self._build_bm25_index()
        logger.info(f"Đã cập nhật BM25 index với {len(new_documents)} documents mới")

    def set_alpha(self, alpha: float):
        """
        Điều chỉnh trọng số giữa dense và sparse retrieval
        alpha = 1.0: chỉ dùng dense (semantic)
        alpha = 0.0: chỉ dùng sparse (keyword)
        alpha = 0.5: cân bằng
        """
        if not 0 <= alpha <= 1:
            raise ValueError("Alpha phải trong khoảng [0, 1]")
        self.alpha = alpha
        logger.info(f"Đã cập nhật alpha = {alpha}")


class HybridRetrieverWrapper(BaseRetriever):
    """
    Wrapper để HybridRetriever tương thích với LangChain's retriever interface
    Kế thừa từ BaseRetriever để tương thích với ConversationalRetrievalChain
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    hybrid_retriever: HybridRetriever

    def __init__(self, hybrid_retriever: HybridRetriever, **kwargs):
        """Khởi tạo wrapper với HybridRetriever instance"""
        super().__init__(hybrid_retriever=hybrid_retriever, **kwargs)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """
        Required method từ BaseRetriever
        Interface method cho LangChain compatibility
        """
        return self.hybrid_retriever.retrieve(query)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """
        Required async method từ BaseRetriever
        Async version (simplified - calls sync version)
        """
        return self.hybrid_retriever.retrieve(query)
