# -*- coding: utf-8 -*-
"""
Hybrid Entity Matcher
Combines Rule-based matching with Cosine Similarity for better entity matching
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from sentence_transformers import SentenceTransformer
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridEntityMatcher:
    """
    Hybrid approach for entity matching:
    1. Rule-based (exact, keyword, contains) - FAST
    2. Cosine Similarity (semantic) - ACCURATE for edge cases
    """

    def __init__(self, use_semantic: bool = True):
        """
        Initialize hybrid matcher

        Args:
            use_semantic: Whether to use semantic matching (requires embedding model)
        """
        self.use_semantic = use_semantic
        self.embedding_model = None

        # Predefined keywords for different categories
        self.keywords = {
            'error': [
                'thất bại', 'không nhận', 'chưa nhận', 'lỗi', 'từ chối',
                'không thành công', 'bị từ chối', 'không được', 'sai',
                'không hợp lệ', 'hết hạn', 'quá hạn mức'
            ],
            'success': [
                'thành công', 'hoàn tất', 'đã nhận', 'hoàn thành',
                'kích hoạt', 'được duyệt'
            ],
            'money': [
                'tiền', 'số tiền', 'số dư', 'tài khoản', 'hạn mức',
                'phí', 'miễn phí'
            ],
            'action': [
                'nạp', 'rút', 'chuyển', 'liên kết', 'hủy', 'đăng ký',
                'cập nhật', 'kiểm tra', 'tra cứu'
            ],
            'bank': [
                'ngân hàng', 'vietcombank', 'techcombank', 'acb', 'bidv',
                'vietinbank', 'vpbank', 'mbbank', 'sacombank'
            ]
        }

        # Initialize embedding model if needed
        if self.use_semantic:
            self._init_embedding_model()

    def _init_embedding_model(self):
        """Initialize sentence embedding model for semantic matching"""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("✅ Embedding model loaded for hybrid matching")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            logger.warning("Falling back to rule-based matching only")
            self.use_semantic = False

    def calculate_similarity(
        self,
        entity1: str,
        entity2: str,
        entity_type: str = None
    ) -> Tuple[float, str]:
        """
        Calculate similarity between two entities using hybrid approach

        Args:
            entity1: First entity (usually from query)
            entity2: Second entity (usually from FAQ)
            entity_type: Type of entity (Error, Action, etc.) for context

        Returns:
            Tuple of (similarity_score, match_method)
            - similarity_score: 0.0 to 1.0
            - match_method: How the match was found
        """

        # Normalize
        e1_lower = entity1.lower().strip()
        e2_lower = entity2.lower().strip()

        # PRIORITY 1: EXACT MATCH (highest confidence)
        if e1_lower == e2_lower:
            return 1.0, "EXACT"

        # PRIORITY 2: KEYWORD MATCH (high confidence)
        keyword_score, keyword_method = self._keyword_match(e1_lower, e2_lower)
        if keyword_score > 0:
            return keyword_score, keyword_method

        # PRIORITY 3: CONTAINS MATCH (good confidence)
        contains_score, contains_method = self._contains_match(e1_lower, e2_lower)
        if contains_score > 0:
            return contains_score, contains_method

        # PRIORITY 4: SEMANTIC MATCH (semantic understanding)
        if self.use_semantic and self.embedding_model:
            semantic_score, semantic_method = self._semantic_match(entity1, entity2)
            if semantic_score > 0.6:  # Threshold for semantic matching
                return semantic_score, semantic_method

        # NO MATCH
        return 0.0, "NO_MATCH"

    def _keyword_match(self, e1: str, e2: str) -> Tuple[float, str]:
        """
        Check if entities share important keywords
        Returns: (score, method)
        """
        # Check each keyword category
        for category, keywords in self.keywords.items():
            matched_keywords = []

            for kw in keywords:
                # Both entities contain this keyword
                if kw in e1 and kw in e2:
                    matched_keywords.append(kw)

            if matched_keywords:
                # Score based on keyword importance and count
                base_score = 0.85

                # Boost if multiple keywords match
                if len(matched_keywords) > 1:
                    base_score = min(0.95, base_score + 0.05 * len(matched_keywords))

                return base_score, f"KEYWORD_{category.upper()}_{len(matched_keywords)}"

        return 0.0, None

    def _contains_match(self, e1: str, e2: str) -> Tuple[float, str]:
        """
        Check if one entity contains the other
        Returns: (score, method)
        """
        # Full substring match
        if e1 in e2:
            # Calculate overlap ratio
            ratio = len(e1) / len(e2)
            score = 0.7 + (ratio * 0.15)  # 0.7 to 0.85
            return score, "CONTAINS_FULL"

        if e2 in e1:
            ratio = len(e2) / len(e1)
            score = 0.7 + (ratio * 0.15)
            return score, "CONTAINS_FULL"

        # Partial word match (at least 70% words overlap)
        words1 = set(e1.split())
        words2 = set(e2.split())

        if words1 and words2:
            overlap = len(words1 & words2)
            union = len(words1 | words2)

            if overlap > 0:
                jaccard = overlap / union

                if jaccard >= 0.7:  # 70% word overlap
                    score = 0.65 + (jaccard * 0.15)  # 0.65 to 0.8
                    return score, f"WORD_OVERLAP_{jaccard:.2f}"

        return 0.0, None

    def _semantic_match(self, e1: str, e2: str) -> Tuple[float, str]:
        """
        Use cosine similarity with embeddings for semantic matching
        Returns: (score, method)
        """
        try:
            # Generate embeddings
            emb1 = self.embedding_model.encode(e1, convert_to_numpy=True)
            emb2 = self.embedding_model.encode(e2, convert_to_numpy=True)

            # Cosine similarity
            cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

            # Apply thresholds
            if cosine_sim >= 0.85:
                return float(cosine_sim), "SEMANTIC_VERY_HIGH"
            elif cosine_sim >= 0.75:
                return float(cosine_sim), "SEMANTIC_HIGH"
            elif cosine_sim >= 0.65:
                # Reduce score slightly for medium confidence
                return float(cosine_sim * 0.9), "SEMANTIC_MEDIUM"
            elif cosine_sim >= 0.6:
                return float(cosine_sim * 0.85), "SEMANTIC_LOW"
            else:
                return 0.0, None

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
            return 0.0, None

    def match_entity_lists(
        self,
        query_entities: List[str],
        faq_entities: List[str],
        entity_type: str = None
    ) -> Dict:
        """
        Match two lists of entities and return best matches

        Args:
            query_entities: Entities from query
            faq_entities: Entities from FAQ
            entity_type: Type of entities being matched

        Returns:
            Dictionary with matching results
        """
        results = {
            'matches': [],
            'total_score': 0.0,
            'best_score': 0.0,
            'match_count': 0
        }

        if not query_entities or not faq_entities:
            return results

        # Find best match for each query entity
        for qe in query_entities:
            best_score = 0.0
            best_match = None
            best_method = None

            for fe in faq_entities:
                score, method = self.calculate_similarity(qe, fe, entity_type)

                if score > best_score:
                    best_score = score
                    best_match = fe
                    best_method = method

            if best_score > 0.6:  # Threshold
                results['matches'].append({
                    'query_entity': qe,
                    'matched_entity': best_match,
                    'score': best_score,
                    'method': best_method
                })
                results['total_score'] += best_score
                results['match_count'] += 1
                results['best_score'] = max(results['best_score'], best_score)

        # Calculate average score
        if results['match_count'] > 0:
            results['avg_score'] = results['total_score'] / results['match_count']
        else:
            results['avg_score'] = 0.0

        return results

    def get_entity_bonus(
        self,
        query_entities: List[str],
        faq_entities: List[str],
        entity_type: str = None
    ) -> float:
        """
        Calculate bonus score for entity matching (for use in graph scoring)

        Args:
            query_entities: Entities from query
            faq_entities: Entities from FAQ
            entity_type: Type of entities

        Returns:
            Bonus score (0.0 to 4.0+ depending on match quality)
        """
        if not query_entities:
            return 0.0

        if not faq_entities:
            # FAQ has no entities of this type
            # Small penalty or neutral depending on type
            if entity_type in ['Error']:
                return -2.0  # Penalty if query asks about error but FAQ has none
            else:
                return 0.2  # Small tolerant bonus

        # Calculate matches
        match_result = self.match_entity_lists(query_entities, faq_entities, entity_type)

        if match_result['match_count'] == 0:
            # FAQ has entities but none match
            if entity_type in ['Service', 'Bank']:
                return -1.0  # Strong penalty for mismatch
            else:
                return 0.0

        # Calculate bonus based on best match quality
        best_score = match_result['best_score']
        match_count = match_result['match_count']

        # Base bonus from best match
        if best_score >= 0.95:  # Exact or very high similarity
            base_bonus = 4.0
        elif best_score >= 0.85:  # High similarity (keyword match)
            base_bonus = 3.0
        elif best_score >= 0.75:  # Good similarity (contains/semantic high)
            base_bonus = 2.0
        else:  # Medium similarity
            base_bonus = 1.5

        # Boost if multiple entities match
        if match_count > 1:
            base_bonus = min(base_bonus * 1.2, 5.0)

        return base_bonus


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING HYBRID ENTITY MATCHER")
    print("=" * 80)

    # Initialize matcher
    matcher = HybridEntityMatcher(use_semantic=True)

    # Test cases
    test_cases = [
        # (entity1, entity2, expected_score_range, description)
        ("Giao dịch thất bại", "Giao dịch thất bại", (1.0, 1.0), "Exact match"),
        ("Giao dịch thất bại", "Chuyển tiền thất bại", (0.8, 0.9), "Keyword match (thất bại)"),
        ("Giao dịch không thành công", "Giao dịch thất bại", (0.75, 0.95), "Semantic match (synonyms)"),
        ("Không nhận được tiền", "Chưa nhận được tiền từ ngân hàng", (0.7, 0.85), "Contains + keyword"),
        ("Nạp tiền Vinaphone", "Nạp tiền điện thoại Vinaphone", (0.75, 0.9), "Contains match"),
        ("Lỗi đăng nhập", "Giao dịch thất bại", (0.0, 0.3), "No match"),
        ("Chuyển khoản", "Chuyển tiền", (0.7, 0.95), "Synonym (semantic)"),
    ]

    print("\nTest Results:")
    print("-" * 80)

    for i, (e1, e2, (min_score, max_score), desc) in enumerate(test_cases, 1):
        score, method = matcher.calculate_similarity(e1, e2)

        # Check if score in expected range
        status = "✅" if min_score <= score <= max_score else "❌"

        print(f"\n{i}. {desc}")
        print(f"   Entity 1: '{e1}'")
        print(f"   Entity 2: '{e2}'")
        print(f"   Score: {score:.3f} ({method})")
        print(f"   Expected: {min_score:.2f} - {max_score:.2f} {status}")

    # Test list matching
    print("\n" + "=" * 80)
    print("TEST: Entity List Matching")
    print("=" * 80)

    query_entities = ["Giao dịch thất bại", "Không nhận được tiền"]
    faq_entities = ["Chuyển tiền thất bại", "Chưa nhận tiền"]

    result = matcher.match_entity_lists(query_entities, faq_entities, "Error")

    print(f"\nQuery entities: {query_entities}")
    print(f"FAQ entities: {faq_entities}")
    print(f"\nMatches found: {result['match_count']}")
    print(f"Total score: {result['total_score']:.2f}")
    print(f"Average score: {result['avg_score']:.2f}")
    print(f"Best score: {result['best_score']:.2f}")

    print("\nDetailed matches:")
    for match in result['matches']:
        print(f"  '{match['query_entity']}' → '{match['matched_entity']}'")
        print(f"    Score: {match['score']:.3f} ({match['method']})")

    # Test bonus calculation
    print("\n" + "=" * 80)
    print("TEST: Bonus Calculation")
    print("=" * 80)

    bonus = matcher.get_entity_bonus(query_entities, faq_entities, "Error")
    print(f"\nBonus score: {bonus:.2f}")
    print(f"(This would be added to graph_score in Neo4j query)")
