"""
Neo4j GraphRAG Query Engine for VNPT Money Chatbot
Implements graph traversal and retrieval using Neo4j Cypher queries

ENHANCED VERSION:
- Intent-based answer extraction (FEE, LIMIT, TIME, HOW_TO, TROUBLESHOOT)
- Feature filtering in Cypher queries
- LLM-based answer extraction instead of returning full FAQ
"""

import logging
import re
from typing import List, Dict, Optional
import numpy as np

from neo4j_connector import Neo4jConnector
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# Vietnamese No-Diacritics to Diacritics Mapping
# For handling queries without Vietnamese accents
# =====================================================
VIETNAMESE_NO_DIACRITICS_MAP = {
    # Common words in VNPT Money domain
    'nap': 'nạp', 'tien': 'tiền', 'vi': 'ví', 'vao': 'vào',
    'rut': 'rút', 've': 'về', 'chuyen': 'chuyển', 'den': 'đến',
    'phi': 'phí', 'bao': 'bao', 'nhieu': 'nhiêu', 'lau': 'lâu',
    'ngan': 'ngân', 'hang': 'hàng', 'lien': 'liên', 'ket': 'kết',
    'tai': 'tài', 'khoan': 'khoản', 'mat': 'mật', 'khau': 'khẩu',
    'dang': 'đăng', 'ky': 'ký', 'doi': 'đổi', 'quen': 'quên',
    'han': 'hạn', 'muc': 'mức', 'thoi': 'thời', 'gian': 'gian',
    'giao': 'giao', 'dich': 'dịch', 'that': 'thất', 'bai': 'bại',
    'loi': 'lỗi', 'thanh': 'thanh', 'toan': 'toán', 'hoa': 'hóa',
    'don': 'đơn', 'dien': 'điện', 'nuoc': 'nước', 'internet': 'internet',
    'dinh': 'định', 'danh': 'danh', 'xac': 'xác', 'thuc': 'thực',
    'cccd': 'cccd', 'cmnd': 'cmnd', 'otp': 'otp',
    'huong': 'hướng', 'dan': 'dẫn', 'cach': 'cách', 'lam': 'làm',
    'sao': 'sao', 'the': 'thế', 'nao': 'nào', 'gi': 'gì',
    've': 'vé', 'may': 'máy', 'bay': 'bay', 'tau': 'tàu',
    'mua': 'mua', 'dat': 'đặt', 'dang': 'đăng',
    'so': 'số', 'du': 'dư', 'toi': 'tối', 'da': 'đa', 'thieu': 'thiểu',
    'hotline': 'hotline', 'tong': 'tổng', 'dai': 'đài',
    'khoa': 'khóa', 'mo': 'mở', 'huy': 'hủy',
    'voucher': 'voucher', 'ma': 'mã', 'giam': 'giảm', 'gia': 'giá',
    'khuyen': 'khuyến', 'mai': 'mãi', 'tich': 'tích', 'diem': 'điểm',
    'bao': 'bảo', 'mat': 'mật', 'an': 'an', 'toan': 'toàn',
    'van': 'vân', 'tay': 'tay', 'khuon': 'khuôn', 'mat': 'mặt',
    'sinh': 'sinh', 'trac': 'trắc', 'hoc': 'học',
    'tra': 'tra', 'cuu': 'cứu', 'lich': 'lịch', 'su': 'sử',
    'vnpt': 'vnpt', 'money': 'money', 'app': 'app', 'ung': 'ứng', 'dung': 'dụng',
    'tru': 'trừ', 'cong': 'cộng', 'hoan': 'hoàn',
    'dieu': 'điều', 'kien': 'kiện', 'yeu': 'yêu', 'cau': 'cầu',
    'thu': 'thụ', 'huong': 'hưởng', 'nguoi': 'người', 'nhan': 'nhận',
    'gui': 'gửi', 'nham': 'nhầm', 'hoi': 'hỏi', 'dap': 'đáp',
    'tro': 'trợ', 'giup': 'giúp', 'ho': 'hỗ',
}

def convert_no_diacritics_to_vietnamese(text: str) -> str:
    """
    Convert Vietnamese text without diacritics to text with diacritics.
    Uses word-by-word mapping for common VNPT Money domain terms.

    Example: "cach nap tien vao vi" -> "cách nạp tiền vào ví"
    """
    if not text:
        return text

    # Check if text likely has no diacritics (no Vietnamese characters)
    vietnamese_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
    has_vietnamese = any(c in text.lower() for c in vietnamese_chars)

    if has_vietnamese:
        # Already has Vietnamese diacritics, return as is
        return text

    # Convert word by word
    words = text.lower().split()
    converted_words = []

    for word in words:
        # Clean word (remove punctuation at end)
        clean_word = re.sub(r'[?.!,;:]$', '', word)
        suffix = word[len(clean_word):]  # Keep punctuation

        # Look up in mapping
        if clean_word in VIETNAMESE_NO_DIACRITICS_MAP:
            converted_words.append(VIETNAMESE_NO_DIACRITICS_MAP[clean_word] + suffix)
        else:
            converted_words.append(word)

    return ' '.join(converted_words)


class Neo4jGraphRAGEngine:
    """GraphRAG Engine using Neo4j backend - ENHANCED VERSION"""

    def __init__(self):
        """Initialize GraphRAG Engine with Neo4j"""
        self.connector = Neo4jConnector()
        self.embeddings_model = None
        self._initialize_embeddings()

        # Initialize enhanced entity extractor (with regex & confidence scoring)
        from enhanced_entity_extractor import EnhancedEntityExtractor
        self.entity_extractor = EnhancedEntityExtractor()
        logger.info("Enhanced entity extractor initialized (regex + confidence scoring)")

        # Initialize intent classifier (ENHANCED)
        from intent_classifier import IntentClassifier
        self.intent_classifier = IntentClassifier()
        logger.info("Enhanced intent classifier initialized (FEE, LIMIT, TIME, HOW_TO, TROUBLESHOOT)")

        # Initialize intent-based answer extractor (NEW!)
        from intent_answer_extractor import IntentAnswerExtractor
        self.answer_extractor = IntentAnswerExtractor()
        logger.info("Intent answer extractor initialized (LLM-based)")

        # Initialize focused answer extractor (NEWEST - 3-layer extraction)
        from focused_answer_extractor import FocusedAnswerExtractor
        self.focused_extractor = FocusedAnswerExtractor(neo4j_connector=self.connector)
        logger.info("Focused answer extractor initialized (Entity → Case → LLM)")

        # Initialize step extractor
        from step_tracker import StepExtractor
        self.step_extractor = StepExtractor(neo4j_connector=self.connector)
        logger.info("Step extractor initialized")

        # Hybrid entity matcher disabled (PyTorch dependency removed)
        self.hybrid_matcher = None

        # Query cache
        self.cache = {}

    def _initialize_embeddings(self):
        """Initialize embeddings model for query encoding"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embeddings_model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embeddings model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load embeddings model: {e}")

    def query(self, user_query: str, top_k: int = 5, continuation_context: Optional[Dict] = None,
              follow_up_context: Optional[Dict] = None) -> Dict:
        """
        Main query method - ENTITY-FIRST APPROACH with CONTEXT SUPPORT

        Args:
            user_query: User's question
            top_k: Number of results to return
            continuation_context: Optional conversation context for step continuation
            follow_up_context: Optional follow-up context from Mem0 (NEW!)
                - is_follow_up: bool
                - topic: str (previous topic)
                - faq_id: str (previous FAQ ID to search within)
                - context_needed: str (what user is asking about)
                - memories: list (relevant memories)

        Returns:
            Query result with answers, context, and metadata
        """
        # Check cache (skip if context provided)
        has_context = continuation_context or follow_up_context
        if not has_context and config.CACHE_ENABLED and user_query in self.cache:
            logger.info("Returning cached result")
            return self.cache[user_query]

        # IMPORTANT: Convert no-diacritics Vietnamese to diacritics
        # This allows queries like "cach nap tien vao vi" to work
        original_query = user_query
        user_query = convert_no_diacritics_to_vietnamese(user_query)
        if user_query != original_query:
            logger.info(f"Converted no-diacritics query: '{original_query}' → '{user_query}'")

        logger.info(f"Processing query: {user_query}")

        # NEW: Log follow-up context if provided
        if follow_up_context and follow_up_context.get("is_follow_up"):
            logger.info(f"🔗 FOLLOW-UP DETECTED: topic='{follow_up_context.get('topic')}', "
                       f"faq_id='{follow_up_context.get('faq_id')}', "
                       f"context='{follow_up_context.get('context_needed')}'")

        # Step 0: Classify intent (NEW)
        intent, intent_confidence, intent_details = self.intent_classifier.classify(user_query)
        logger.info(f"Query intent: {intent} (confidence: {intent_confidence:.2%})")

        # Step 1: Extract entities from user query
        query_entities = self._extract_query_entities(user_query)
        logger.info(f"Extracted entities: {query_entities}")

        # Step 1.5: Check if query is out of scope
        if query_entities.get("out_of_scope", False):
            logger.warning(f"Query is out of scope: {user_query}")
            return {
                "status": "out_of_scope",
                "question": "",
                "answer": "Xin lỗi, câu hỏi của bạn không liên quan đến dịch vụ VNPT Money. Tôi chỉ có thể hỗ trợ các câu hỏi về ví điện tử VNPT Money như: nạp tiền, rút tiền, chuyển tiền, liên kết ngân hàng, thanh toán, mua vé máy bay, v.v.\n\nNếu bạn cần hỗ trợ, vui lòng liên hệ Hotline: 1900 8198",
                "confidence": 0,
                "related_entities": {},
                "related_questions": [],
                "all_results": []
            }

        # Step 1.6: Handle step continuation queries (NEW)
        if continuation_context:
            logger.info("🔗 Processing step continuation query")
            return self._handle_step_continuation(user_query, continuation_context, query_entities)

        # Step 1.7: Handle follow-up queries with Mem0 context (NEW!)
        if follow_up_context and follow_up_context.get("is_follow_up"):
            logger.info("🔗 Processing follow-up query with Mem0 context")
            return self._handle_follow_up_query(
                user_query=user_query,
                follow_up_context=follow_up_context,
                query_entities=query_entities,
                intent=intent,
                intent_confidence=intent_confidence,
                top_k=top_k
            )

        # Step 2: Find relevant nodes (GRAPH-ONLY search) with REGEX FALLBACK
        # IMPORTANT: Retrieve MORE candidates (top_k * 3) to ensure procedural FAQs aren't filtered out early
        intermediate_top_k = top_k * 3 if intent == "HOW_TO" else top_k * 2
        relevant_nodes = self._find_relevant_nodes(user_query, query_entities, intermediate_top_k, intent)

        # Step 2.5: REGEX FALLBACK - If no nodes found with LLM entities, try adding regex entities
        if getattr(config, 'USE_REGEX_FALLBACK_ON_EMPTY_RESULTS', False):
            if not relevant_nodes or len(relevant_nodes) == 0:
                logger.warning("⚠️ No nodes found with LLM entities, trying regex fallback...")
                query_entities = self._augment_with_regex_entities(user_query, query_entities)
                logger.info(f"Augmented entities: {query_entities}")

                # Retry search with augmented entities
                relevant_nodes = self._find_relevant_nodes(user_query, query_entities, top_k, intent)

                if relevant_nodes and len(relevant_nodes) > 0:
                    logger.info(f"✅ Regex fallback successful: found {len(relevant_nodes)} nodes")
                else:
                    logger.warning("❌ Regex fallback also returned no results")

        # Step 2.6: INTENT-BASED KEYWORD SEARCH - For specific intents (FEE, LIMIT, TIME),
        # add keyword search results to improve retrieval when entity graph is not sufficient
        specific_intents = ["FEE", "LIMIT", "TIME"]
        if intent in specific_intents:
            keyword_results = self._intent_keyword_search(user_query, intent, top_k)
            if keyword_results:
                logger.info(f"✅ Intent keyword search found {len(keyword_results)} additional results")
                # Merge with existing results, avoiding duplicates
                existing_ids = {n["node_id"] for n in relevant_nodes}
                for kr in keyword_results:
                    if kr["node_id"] not in existing_ids:
                        relevant_nodes.append(kr)
                        existing_ids.add(kr["node_id"])

        # Step 2.7: ALWAYS CHECK FOR EXACT MATCH - Critical for FAQs without entity links
        # This ensures exact question matches are not missed even if entity search succeeds
        exact_match_results = self._find_exact_match_faq(user_query)
        if exact_match_results:
            existing_ids = {n["node_id"] for n in relevant_nodes}
            for emr in exact_match_results:
                if emr["node_id"] not in existing_ids:
                    # Add with HIGH score to ensure it's prioritized
                    emr["score"] = 1.0  # Max score for exact match
                    relevant_nodes.insert(0, emr)  # Insert at beginning
                    logger.info(f"🎯 EXACT MATCH INJECTION: {emr['node_id']} added to results")

        # Step 3: Traverse graph to get context (with early exact match boosting)
        context = self._get_graph_context(relevant_nodes, query_entities, user_query, intent)

        # Step 4: Rank and select best results (with intent-aware ranking)
        results = self._rank_results(context, user_query, intent, query_entities)

        # Step 5: Extract and attach steps if answer contains step-by-step instructions
        if results.get("status") == "success" and results.get("answer"):
            steps = self.step_extractor.extract_from_answer(results["answer"])
            results["steps"] = steps
            results["has_steps"] = len(steps) > 0

        # Cache result
        if config.CACHE_ENABLED:
            self.cache[user_query] = results

        return results

    def _extract_query_entities(self, user_query: str) -> Dict:
        """
        Extract entities from user query using Enhanced pattern-based matching

        Args:
            user_query: User's question

        Returns:
            Dictionary of extracted entities by type
        """
        try:
            # Use enhanced pattern-based extractor (regex + confidence scoring)
            entities, confidence = self.entity_extractor.extract_with_confidence(user_query)

            # Log confidence for monitoring
            logger.info(f"Entity extraction confidence: {confidence:.2%}")
            if confidence < 0.5:
                logger.warning(f"Low confidence extraction ({confidence:.2%}) for query: {user_query}")

            return entities
        except Exception as e:
            logger.error(f"Failed to extract entities from query: {e}")
            return {}

    def _augment_with_regex_entities(self, user_query: str, llm_entities: Dict) -> Dict:
        """
        Augment LLM entities with regex-extracted entities when Neo4j query returns no results

        Strategy:
        - LLM entities are PRIMARY (already used but returned no results)
        - Extract entities using PURE REGEX (no LLM)
        - Add regex entities that LLM missed
        - This helps find results when LLM entities are too semantic/inferred

        Args:
            user_query: User's question
            llm_entities: Entities already extracted by LLM

        Returns:
            Augmented entities dictionary
        """
        try:
            logger.info("🔍 Extracting additional regex entities for fallback...")

            # Temporarily disable LLM to get pure regex extraction
            original_llm_setting = getattr(config, 'USE_LLM_FIRST_STRATEGY', True)
            original_fallback_setting = getattr(config, 'ENABLE_LLM_FALLBACK', True)

            config.USE_LLM_FIRST_STRATEGY = False
            config.ENABLE_LLM_FALLBACK = False

            # Extract with pure regex
            regex_entities, regex_conf = self.entity_extractor.extract_with_confidence(user_query)

            # Restore settings
            config.USE_LLM_FIRST_STRATEGY = original_llm_setting
            config.ENABLE_LLM_FALLBACK = original_fallback_setting

            logger.info(f"Pure regex entities: {regex_entities}")

            # Merge: Start with LLM entities, add regex entities that are missing
            augmented = llm_entities.copy()

            for entity_type, regex_values in regex_entities.items():
                if not regex_values or not isinstance(regex_values, list):
                    continue

                llm_values = llm_entities.get(entity_type, [])

                # Add regex values that LLM didn't find
                for regex_val in regex_values:
                    # Check if this value or similar exists in LLM results
                    exists = any(
                        regex_val.lower() in llm_val.lower() or
                        llm_val.lower() in regex_val.lower()
                        for llm_val in llm_values
                        if isinstance(llm_val, str)
                    )

                    if not exists:
                        if entity_type not in augmented:
                            augmented[entity_type] = []
                        if regex_val not in augmented[entity_type]:
                            augmented[entity_type].append(regex_val)
                            logger.info(f"   ➕ Added from regex: {entity_type}={regex_val}")

            return augmented

        except Exception as e:
            logger.error(f"Failed to augment with regex entities: {e}")
            return llm_entities  # Return original on error

    def _find_relevant_nodes(
        self,
        query: str,
        query_entities: Dict,
        top_k: int,
        intent: str = "GENERAL"
    ) -> List[Dict]:
        """
        Find relevant question nodes using HYBRID search

        Strategy:
        1. HYBRID MODE (if enabled): Entity graph (90%) + Semantic (10%)
        2. GRAPH-ONLY MODE (fallback): Entity-based only if hybrid disabled
        3. KEYWORD FALLBACK: If no entities found

        Args:
            query: User query
            query_entities: Extracted entities from query
            top_k: Number of nodes to return
            intent: Query intent

        Returns:
            List of {node_id, relevance_score, method}
        """
        # Priority 1: ENTITY-BASED GRAPH SEARCH (retrieve more candidates)
        entity_results = self._entity_graph_search(query_entities, top_k * 3)

        # Check if Error entities were extracted but didn't match in graph
        has_error_entities = bool(query_entities.get("Error", []))
        error_entity_fallback = has_error_entities and not entity_results

        if entity_results:
            # CRITICAL: Verify entity results are actually relevant to query
            # This prevents wrong FAQs from being returned when entity graph matches
            # something unrelated (e.g., "liên kết ngân hàng" matching FAQ about "chuyển tiền nhầm")
            entity_results = self._verify_entity_results_relevance(query, entity_results, top_k)

            if not entity_results:
                # Entity results were filtered out - fallback to keyword search
                logger.warning("⚠️ Entity results filtered as irrelevant, falling back to keyword search")
                keyword_results = self._keyword_search(query, top_k)
                return keyword_results

            # Check if hybrid mode is enabled
            if config.ENABLE_HYBRID_MODE and self.embeddings_model:
                logger.info(f"HYBRID MODE: Found {len(entity_results)} results via graph traversal")

                # PRIORITIZE graph search if Error entities detected (graph is more precise for errors)
                semantic_weight = config.HYBRID_WEIGHT_SEMANTIC
                if has_error_entities:
                    semantic_weight = 0.2  # Use 20% semantic, 80% graph for Error queries
                    logger.info(f"⚠️  Error entity detected → Prioritizing graph search (80% graph / 20% semantic)")
                else:
                    logger.info(f"Running semantic search with weight: {semantic_weight}")

                # Also run semantic search
                semantic_results = self._semantic_search(query, top_k * 3)

                if semantic_results:
                    logger.info(f"Found {len(semantic_results)} semantic results")

                    # Aggregate scores with adjusted weights
                    all_results = entity_results + semantic_results
                    aggregated = self._aggregate_scores(
                        all_results,
                        has_entities=True,
                        override_semantic_weight=semantic_weight if has_error_entities else None
                    )

                    # Sort by aggregated score and return top_k
                    aggregated.sort(key=lambda x: x["score"], reverse=True)
                    return aggregated[:top_k]
                else:
                    logger.info("No semantic results found, using entity results only")
                    return entity_results[:top_k]
            else:
                logger.info(f"GRAPH-ONLY MODE: Found {len(entity_results)} results via graph traversal")
                logger.info("Skipping semantic search (hybrid mode disabled or no embeddings model)")
                return entity_results[:top_k]

        # Fallback: If Error entity extracted but NO graph results -> use PURE SEMANTIC
        if error_entity_fallback:
            logger.warning(f"Error entity detected but not found in graph → Using PURE SEMANTIC search")
            return self._semantic_search(query, top_k)

        # Fallback: If NO entities extracted -> check if out of scope first
        logger.warning("No entities found in query - checking if out of scope")

        # Check if query contains any VNPT Money related keywords
        vnpt_keywords = [
            'vnpt', 'ví', 'tiền', 'chuyển', 'nạp', 'rút', 'thanh toán', 'liên kết',
            'ngân hàng', 'giao dịch', 'tài khoản', 'định danh', 'mật khẩu', 'otp',
            'mobile money', 'phí', 'hạn mức', 'lỗi', 'thất bại', 'hotline', 'hỗ trợ',
            'đăng ký', 'hủy', 'khóa', 'mở khóa', 'ứng dụng', 'app', 'pay', 'money',
            'điện thoại', 'số dư', 'biểu phí', 'khuyến mãi', 'voucher', 'mã giảm giá'
        ]

        query_lower = query.lower()
        has_vnpt_keyword = any(kw in query_lower for kw in vnpt_keywords)

        if not has_vnpt_keyword:
            # Query is likely out of scope
            logger.warning(f"Query appears to be out of scope: {query}")
            return []  # Return empty to trigger no_results handling

        # Use keyword search if query has VNPT-related keywords
        keyword_results = self._keyword_search(query, top_k)

        return keyword_results

    def _verify_entity_results_relevance(
        self,
        query: str,
        entity_results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Verify that entity graph results are actually relevant to the query.

        This prevents the common issue where entity graph returns wrong FAQs because
        entities match something unrelated. For example:
        - Query: "Cách liên kết ngân hàng?"
        - Wrong match: FAQ about "chuyển tiền nhầm" (because both contain "ngân hàng")

        Strategy:
        1. Get FAQ questions for top entity results
        2. Calculate keyword overlap between query and FAQ question
        3. Filter out FAQs with very low relevance

        Args:
            query: Original user query
            entity_results: Results from entity graph search
            top_k: Number of results to verify

        Returns:
            Filtered list of relevant entity results
        """
        if not entity_results:
            return []

        query_lower = query.lower()

        # Extract key terms from query (excluding stopwords)
        stopwords = {'tôi', 'bạn', 'là', 'có', 'thể', 'được', 'để', 'và', 'hoặc', 'hay',
                    'này', 'đó', 'như', 'thế', 'nào', 'gì', 'sao', 'làm', 'muốn', 'cần',
                    'của', 'cho', 'với', 'từ', 'đến', 'trong', 'bao', 'nhiêu', 'ở', 'đâu',
                    'mà', 'khi', 'nếu', 'thì', 'vì', 'do', 'bởi', 'nhưng', 'còn', 'vẫn'}

        query_terms = set(w for w in query_lower.split() if w not in stopwords and len(w) > 1)

        # Important compound terms to check - MORE SPECIFIC patterns
        # Only use MULTI-WORD patterns to avoid false positives
        important_terms = []
        compound_patterns = [
            'liên kết ngân hàng', 'liên kết tài khoản', 'liên kết bank',
            'nạp tiền vào ví', 'nạp tiền từ',
            'rút tiền về', 'rút tiền từ ví',
            'chuyển tiền đến', 'chuyển tiền cho', 'chuyển tiền qua',
            'đăng ký tài khoản', 'đăng ký ví', 'tạo tài khoản',
            'đổi mật khẩu', 'thay đổi mật khẩu', 'quên mật khẩu', 'lấy lại mật khẩu',
            'vé máy bay', 'mua vé', 'đặt vé',
            'thanh toán hóa đơn', 'thanh toán tiền điện', 'thanh toán tiền nước',
            'định danh tài khoản', 'xác thực định danh',
            'khóa tài khoản', 'mở khóa tài khoản'
        ]
        for term in compound_patterns:
            if term in query_lower:
                important_terms.append(term)

        # Get FAQ questions for verification
        faq_ids = [r["node_id"] for r in entity_results[:top_k * 2]]
        if not faq_ids:
            return entity_results

        cypher = """
        MATCH (f:FAQ)
        WHERE f.id IN $faq_ids
        RETURN f.id as id, f.question as question
        """
        faq_data = self.connector.execute_query(cypher, {"faq_ids": faq_ids})
        faq_questions = {f["id"]: f["question"] for f in faq_data}

        # Verify each result
        verified_results = []
        for result in entity_results:
            faq_id = result["node_id"]
            faq_question = faq_questions.get(faq_id, "")
            faq_question_lower = faq_question.lower()

            # Check 1: Important compound terms match
            compound_match = False
            for term in important_terms:
                if term in faq_question_lower:
                    compound_match = True
                    break

            # Check 2: Keyword overlap ratio
            faq_terms = set(w for w in faq_question_lower.split() if w not in stopwords and len(w) > 1)
            overlap = len(query_terms & faq_terms)
            overlap_ratio = overlap / len(query_terms) if query_terms else 0

            # Check 3: Similarity using SequenceMatcher
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, query_lower, faq_question_lower).ratio()

            # Decision: Keep if compound match OR high overlap OR high similarity
            is_relevant = compound_match or overlap_ratio >= 0.3 or similarity >= 0.4

            if is_relevant:
                verified_results.append(result)
                logger.debug(f"✅ Verified: {faq_question[:50]}... (overlap={overlap_ratio:.2f}, sim={similarity:.2f})")
            else:
                logger.info(f"❌ Filtered out irrelevant: {faq_question[:50]}... (overlap={overlap_ratio:.2f}, sim={similarity:.2f})")

        # If we filtered out too many, trigger keyword fallback
        # Threshold: If less than 30% of checked results are relevant, use keyword search instead
        checked_count = min(len(entity_results), top_k * 2)  # We check up to top_k * 2 results
        relevance_ratio = len(verified_results) / checked_count if checked_count > 0 else 0

        if relevance_ratio < 0.3:
            logger.warning(f"⚠️ Entity results mostly irrelevant ({len(verified_results)}/{checked_count} passed, ratio={relevance_ratio:.2%})")
            return []  # Return empty to trigger keyword fallback

        logger.info(f"✅ Entity relevance check: {len(verified_results)}/{checked_count} passed (ratio={relevance_ratio:.2%})")
        return verified_results

    def _entity_graph_search(self, query_entities: Dict, top_k: int) -> List[Dict]:
        """
        ENTITY-BASED GRAPH SEARCH - Core GraphRAG method

        Searches Neo4j graph by traversing relationships from extracted entities
        This is MORE PRECISE than keyword/semantic because it uses structured graph data

        Args:
            query_entities: Extracted entities from user query
            top_k: Number of results to return

        Returns:
            List of {node_id, score, method}
        """
        if not query_entities:
            return []

        # Build entity lists for different types (EXPANDED to include ALL entity types)
        topics = query_entities.get("Topic", [])
        services = query_entities.get("Service", [])
        banks = query_entities.get("Bank", [])
        errors = query_entities.get("Error", [])
        actions = query_entities.get("Action", [])
        features = query_entities.get("Feature", [])
        requirements = query_entities.get("Requirement", [])
        timeframes = query_entities.get("TimeFrame", [])
        statuses = query_entities.get("Status", [])
        documents = query_entities.get("Document", [])
        account_types = query_entities.get("AccountType", [])
        ui_elements = query_entities.get("UIElement", [])
        contact_channels = query_entities.get("ContactChannel", [])
        fees = query_entities.get("Fee", [])
        limits = query_entities.get("Limit", [])

        # Combine all entity names for matching
        all_entities = (topics + services + banks + errors + actions + features +
                       requirements + timeframes + statuses + documents + account_types +
                       ui_elements + contact_channels + fees + limits)

        if not all_entities:
            return []

        logger.info(f"Searching graph with entities: {all_entities}")
        if services:
            logger.info(f"  → Service entities (will boost exact matches): {services}")
        if banks:
            logger.info(f"  → Bank entities (will boost exact matches): {banks}")

        # Cypher query to find FAQs via GRAPH TRAVERSAL with ENTITY-SPECIFIC FILTERING
        cypher = """
        // Find FAQs connected to extracted entities (EXACT match prioritized, then SMART PARTIAL)
        MATCH (f:FAQ)-[r]->(e)
        WHERE
            // Priority 1: EXACT match (case-insensitive)
            toLower(e.name) IN [entity IN $entity_names | toLower(entity)]
            // Priority 2: Word boundary match to prevent false positives
            OR ANY(entity IN $entity_names WHERE
                size(entity) >= 3 AND (
                    // Full phrase match
                    toLower(e.name) CONTAINS ' ' + toLower(entity) + ' ' OR
                    // Starts with phrase
                    toLower(e.name) STARTS WITH toLower(entity) + ' ' OR
                    // Ends with phrase
                    toLower(e.name) ENDS WITH ' ' + toLower(entity) OR
                    // Query entity contains DB entity as full word
                    toLower(entity) CONTAINS ' ' + toLower(e.name) + ' ' OR
                    toLower(entity) STARTS WITH toLower(e.name) + ' ' OR
                    toLower(entity) ENDS WITH ' ' + toLower(e.name)
                )
            )

        // Count entity matches and relationship types
        WITH f,
             count(DISTINCT e) as entity_matches,
             collect(DISTINCT type(r)) as rel_types,
             collect(DISTINCT labels(e)[0]) as entity_types,
             collect(DISTINCT e.name) as matched_entities

        // Calculate exact match bonus (boost when entity name matches EXACTLY)
        WITH f,
             entity_matches,
             rel_types,
             entity_types,
             matched_entities,
             // Count exact matches vs partial matches
             size([e_name IN matched_entities WHERE e_name IN $entity_names]) as exact_matches

        // ENTITY-SPECIFIC FILTERING: Check ALL 15 entity type matches
        OPTIONAL MATCH (f)-[:MENTIONS_SERVICE]->(s:Service)
        OPTIONAL MATCH (f)-[:MENTIONS_BANK]->(b:Bank)
        OPTIONAL MATCH (f)-[:DESCRIBES_ERROR]->(err:Error)
        OPTIONAL MATCH (f)-[:SUGGESTS_ACTION]->(act:Action)
        OPTIONAL MATCH (f)-[:USES_FEATURE]->(feat:Feature)
        OPTIONAL MATCH (f)-[:HAS_FEE]->(fee:Fee)
        OPTIONAL MATCH (f)-[:HAS_LIMIT]->(lim:Limit)
        OPTIONAL MATCH (f)-[:HAS_STATUS]->(stat:Status)
        OPTIONAL MATCH (f)-[:REQUIRES]->(req:Requirement)
        OPTIONAL MATCH (f)-[:ABOUT]->(topic:Topic)
        OPTIONAL MATCH (f)-[:HAS_TIMEFRAME]->(tf:TimeFrame)
        OPTIONAL MATCH (f)-[:REQUIRES_DOCUMENT]->(doc:Document)
        OPTIONAL MATCH (f)-[:AFFECTS_ACCOUNT]->(acc:AccountType)
        OPTIONAL MATCH (f)-[:NAVIGATES_TO]->(ui:UIElement)
        OPTIONAL MATCH (f)-[:CONTACTS]->(contact:ContactChannel)

        WITH f, entity_matches, rel_types, entity_types, matched_entities, exact_matches,
             collect(DISTINCT s.name) as faq_services,
             collect(DISTINCT b.name) as faq_banks,
             collect(DISTINCT err.name) as faq_errors,
             collect(DISTINCT act.name) as faq_actions,
             collect(DISTINCT feat.name) as faq_features,
             collect(DISTINCT fee.name) as faq_fees,
             collect(DISTINCT lim.name) as faq_limits,
             collect(DISTINCT stat.name) as faq_statuses,
             collect(DISTINCT req.name) as faq_requirements,
             collect(DISTINCT topic.name) as faq_topics,
             collect(DISTINCT tf.name) as faq_timeframes,
             collect(DISTINCT doc.name) as faq_documents,
             collect(DISTINCT acc.name) as faq_account_types,
             collect(DISTINCT ui.name) as faq_ui_elements,
             collect(DISTINCT contact.name) as faq_contact_channels

        // Calculate ALL entity match bonuses (ALL 15 types!)
        WITH f, entity_matches, rel_types, entity_types, matched_entities, exact_matches,
             faq_services, faq_banks, faq_errors, faq_actions, faq_features,
             faq_fees, faq_limits, faq_statuses, faq_requirements,
             faq_topics, faq_timeframes, faq_documents, faq_account_types,
             faq_ui_elements, faq_contact_channels,
             // BOOST if FAQ has the EXACT Service entity from query
             CASE
               WHEN size($query_services) > 0 AND
                    ANY(qs IN $query_services WHERE qs IN faq_services)
               THEN 2.0  // VERY HIGH BOOST for exact service match (beats exact match penalty)
               WHEN size($query_services) > 0 AND size(faq_services) > 0
               THEN -1.0  // STRONG PENALTY if FAQ has different service
               ELSE 0.3  // SMALL BOOST if FAQ has no service (tolerant to missing data)
             END as service_match_bonus,
             // BOOST if FAQ has the EXACT Bank entity from query
             CASE
               WHEN size($query_banks) > 0 AND
                    ANY(qb IN $query_banks WHERE qb IN faq_banks)
               THEN 1.5  // HIGH BOOST for exact bank match
               WHEN size($query_banks) > 0 AND size(faq_banks) > 0
               THEN -0.8  // PENALTY if FAQ has different bank
               ELSE 0.2  // SMALL BOOST if FAQ has no bank (tolerant to missing data)
             END as bank_match_bonus,
             // PENALTY if FAQ has Error but query does NOT have Error
             CASE
               WHEN size(faq_errors) > 0 AND size($query_errors) = 0
               THEN -2.0  // STRONG PENALTY: FAQ is about errors but query is NOT

               // EXACT MATCH: Query error exactly matches FAQ error
               WHEN size($query_errors) > 0 AND
                    ANY(qe IN $query_errors WHERE qe IN faq_errors)
               THEN 4.0  // STRONG BOOST: Exact error match

               // FUZZY MATCH: Check if main keywords of query error appear in FAQ error
               // Split "giao dịch thất bại" → check if FAQ error contains both "giao dịch" and "thất bại"
               WHEN size($query_errors) > 0 AND
                    ANY(qe IN $query_errors
                        WHERE ANY(fe IN faq_errors
                                  WHERE (toLower(fe) CONTAINS toLower(qe)
                                     OR toLower(qe) CONTAINS toLower(fe)
                                     // Keyword-based fuzzy matching for multi-word errors
                                     OR (toLower(fe) CONTAINS 'thất bại' AND toLower(qe) CONTAINS 'thất bại')
                                     OR (toLower(fe) CONTAINS 'chưa nhận' AND toLower(qe) CONTAINS 'chưa nhận')
                                     OR (toLower(fe) CONTAINS 'không nhận' AND toLower(qe) CONTAINS 'không nhận'))))
               THEN 3.0  // GOOD BOOST: Partial error match (fuzzy)

               ELSE 0.0
             END as error_match_bonus,
             // NEW: BOOST for Action match (IMPORTANT!)
             CASE
               WHEN size($query_actions) > 0 AND
                    ANY(qa IN $query_actions WHERE qa IN faq_actions)
               THEN 1.8  // STRONG BOOST for action match
               ELSE 0.0
             END as action_match_bonus,
             // NEW: BOOST for Fee match (IMPORTANT!)
             CASE
               WHEN size($query_fees) > 0 AND size(faq_fees) > 0
               THEN 2.0  // VERY STRONG BOOST for fee-related queries
               ELSE 0.0
             END as fee_match_bonus,
             // NEW: BOOST for Status match
             CASE
               WHEN size($query_statuses) > 0 AND
                    ANY(qs IN $query_statuses WHERE qs IN faq_statuses)
               THEN 1.5  // STRONG BOOST for status match
               ELSE 0.0
             END as status_match_bonus,
             // NEW: BOOST for Limit match
             CASE
               WHEN size($query_limits) > 0 AND size(faq_limits) > 0
               THEN 1.5  // STRONG BOOST for limit-related queries
               ELSE 0.0
             END as limit_match_bonus,
             // NEW: BOOST for Feature match (CRITICAL FIX!)
             CASE
               WHEN size($query_features) > 0 AND
                    ANY(qf IN $query_features WHERE
                        ANY(ff IN faq_features WHERE
                            toLower(ff) CONTAINS toLower(qf) OR
                            toLower(qf) CONTAINS toLower(ff)))
               THEN 2.5  // VERY STRONG BOOST for feature match (e.g., "liên kết ngân hàng")
               WHEN size($query_features) > 0 AND size(faq_features) > 0
               THEN -0.5  // Small penalty if FAQ has different feature
               ELSE 0.0
             END as feature_match_bonus,
             // NEW: BOOST for Topic match (CRITICAL FIX!)
             CASE
               WHEN size($query_topics) > 0 AND
                    ANY(qt IN $query_topics WHERE
                        ANY(ft IN faq_topics WHERE
                            toLower(ft) CONTAINS toLower(qt) OR
                            toLower(qt) CONTAINS toLower(ft)))
               THEN 2.0  // STRONG BOOST for topic match
               ELSE 0.0
             END as topic_match_bonus

        // Calculate graph-based score with entity-specific boosting (EXPANDED!)
        WITH f,
             entity_matches,
             rel_types,
             entity_types,
             matched_entities,
             exact_matches,
             service_match_bonus,
             bank_match_bonus,
             error_match_bonus,
             action_match_bonus,
             fee_match_bonus,
             status_match_bonus,
             limit_match_bonus,
             feature_match_bonus,
             topic_match_bonus,
             // Bonus for specific relationship types (REDUCED ERROR BOOST)
             CASE
               WHEN 'DESCRIBES_ERROR' IN rel_types THEN 1.5  // REDUCED from 3.0 (let error_match_bonus handle it)
               WHEN 'ABOUT' IN rel_types THEN 1.5
               WHEN 'MENTIONS_BANK' IN rel_types THEN 1.5
               WHEN 'MENTIONS_SERVICE' IN rel_types THEN 1.5
               WHEN 'SUGGESTS_ACTION' IN rel_types THEN 1.2
               WHEN 'USES_FEATURE' IN rel_types THEN 1.3  // NEW: Boost for feature relationships
               ELSE 1.0
             END as rel_weight,
             // Exact match bonus
             exact_matches * 0.5 as exact_match_bonus

        RETURN f.id as id,
               (entity_matches * rel_weight + exact_match_bonus + service_match_bonus + bank_match_bonus +
                error_match_bonus + action_match_bonus + fee_match_bonus + status_match_bonus + limit_match_bonus +
                feature_match_bonus + topic_match_bonus) as graph_score,
               entity_matches,
               rel_types,
               entity_types,
               matched_entities,
               service_match_bonus,
               bank_match_bonus,
               error_match_bonus,
               action_match_bonus,
               fee_match_bonus,
               status_match_bonus,
               limit_match_bonus,
               feature_match_bonus,
               topic_match_bonus
        ORDER BY graph_score DESC
        LIMIT $top_k
        """

        results = self.connector.execute_query(
            cypher,
            {
                "entity_names": all_entities,
                "query_services": services,
                "query_banks": banks,
                "query_errors": errors,
                "query_actions": actions,
                "query_fees": fees,
                "query_statuses": statuses,
                "query_limits": limits,
                "query_features": features,
                "query_topics": topics,
                "top_k": top_k
            }
        )

        if not results:
            logger.warning(f"No graph results found for entities: {all_entities}")
            return []

        # Recalculate bonuses with hybrid matcher (if enabled)
        if config.USE_HYBRID_ENTITY_MATCHING and self.hybrid_matcher:
            results = self._recalculate_bonuses_with_hybrid(
                results=results,
                query_entities=query_entities,
                services=services,
                banks=banks,
                errors=errors,
                actions=actions,
                features=features,
                fees=fees,
                statuses=statuses,
                limits=limits
            )

        # Normalize scores
        max_score = max([r["graph_score"] for r in results]) if results else 1.0

        # Log entity-specific boosts for monitoring (EXPANDED!)
        for r in results[:5]:  # Log top 5
            if (r.get("service_match_bonus", 0) != 0 or r.get("bank_match_bonus", 0) != 0 or
                r.get("error_match_bonus", 0) != 0 or r.get("action_match_bonus", 0) != 0 or
                r.get("fee_match_bonus", 0) != 0 or r.get("status_match_bonus", 0) != 0 or
                r.get("limit_match_bonus", 0) != 0):
                logger.info(f"  FAQ {r['id']}: service={r.get('service_match_bonus', 0):.2f}, "
                          f"bank={r.get('bank_match_bonus', 0):.2f}, "
                          f"error={r.get('error_match_bonus', 0):.2f}, "
                          f"action={r.get('action_match_bonus', 0):.2f}, "
                          f"fee={r.get('fee_match_bonus', 0):.2f}, "
                          f"status={r.get('status_match_bonus', 0):.2f}, "
                          f"limit={r.get('limit_match_bonus', 0):.2f}, "
                          f"total={r['graph_score']:.2f}")

        return [
            {
                "node_id": r["id"],
                "score": float(r["graph_score"]) / max_score,
                "method": "entity_graph",
                "entity_matches": r["entity_matches"],
                "rel_types": r["rel_types"],
                "service_boost": r.get("service_match_bonus", 0),
                "bank_boost": r.get("bank_match_bonus", 0),
                "error_boost": r.get("error_match_bonus", 0),
                "action_boost": r.get("action_match_bonus", 0),
                "fee_boost": r.get("fee_match_bonus", 0),
                "status_boost": r.get("status_match_bonus", 0),
                "limit_boost": r.get("limit_match_bonus", 0)
            }
            for r in results
        ]

    def _recalculate_bonuses_with_hybrid(
        self,
        results: List[Dict],
        query_entities: Dict,
        services: List[str],
        banks: List[str],
        errors: List[str],
        actions: List[str],
        features: List[str],
        fees: List[str],
        statuses: List[str],
        limits: List[str]
    ) -> List[Dict]:
        """
        Recalculate entity match bonuses using hybrid matcher (rule-based + semantic)

        This replaces the Cypher-based bonus calculations with Python-based hybrid matching
        for better synonym and semantic understanding.

        Args:
            results: Results from Cypher query (with Cypher-calculated bonuses)
            query_entities: Original query entities
            services, banks, errors, etc.: Entity lists from query

        Returns:
            Results with hybrid-calculated bonuses and updated scores
        """
        if not self.hybrid_matcher or not results:
            return results

        logger.info("🎯 Recalculating entity bonuses with hybrid matcher")

        # For each FAQ result, get its entities and recalculate bonuses
        for r in results:
            faq_id = r.get("id")

            # Query Neo4j to get FAQ's entities (ALL 15 types!)
            cypher = """
            MATCH (f:FAQ {id: $faq_id})
            OPTIONAL MATCH (f)-[:MENTIONS_SERVICE]->(s:Service)
            OPTIONAL MATCH (f)-[:MENTIONS_BANK]->(b:Bank)
            OPTIONAL MATCH (f)-[:DESCRIBES_ERROR]->(err:Error)
            OPTIONAL MATCH (f)-[:SUGGESTS_ACTION]->(act:Action)
            OPTIONAL MATCH (f)-[:USES_FEATURE]->(feat:Feature)
            OPTIONAL MATCH (f)-[:HAS_FEE]->(fee:Fee)
            OPTIONAL MATCH (f)-[:HAS_STATUS]->(stat:Status)
            OPTIONAL MATCH (f)-[:HAS_LIMIT]->(lim:Limit)
            OPTIONAL MATCH (f)-[:ABOUT]->(topic:Topic)
            OPTIONAL MATCH (f)-[:REQUIRES]->(req:Requirement)
            OPTIONAL MATCH (f)-[:HAS_TIMEFRAME]->(tf:TimeFrame)
            OPTIONAL MATCH (f)-[:REQUIRES_DOCUMENT]->(doc:Document)
            OPTIONAL MATCH (f)-[:AFFECTS_ACCOUNT]->(acc:AccountType)
            OPTIONAL MATCH (f)-[:NAVIGATES_TO]->(ui:UIElement)
            OPTIONAL MATCH (f)-[:CONTACTS]->(contact:ContactChannel)
            RETURN
                collect(DISTINCT s.name) as faq_services,
                collect(DISTINCT b.name) as faq_banks,
                collect(DISTINCT err.name) as faq_errors,
                collect(DISTINCT act.name) as faq_actions,
                collect(DISTINCT feat.name) as faq_features,
                collect(DISTINCT fee.name) as faq_fees,
                collect(DISTINCT stat.name) as faq_statuses,
                collect(DISTINCT lim.name) as faq_limits,
                collect(DISTINCT topic.name) as faq_topics,
                collect(DISTINCT req.name) as faq_requirements,
                collect(DISTINCT tf.name) as faq_timeframes,
                collect(DISTINCT doc.name) as faq_documents,
                collect(DISTINCT acc.name) as faq_account_types,
                collect(DISTINCT ui.name) as faq_ui_elements,
                collect(DISTINCT contact.name) as faq_contact_channels
            """

            faq_entities_result = self.connector.execute_query(cypher, {"faq_id": faq_id})

            if not faq_entities_result:
                continue

            faq_entities = faq_entities_result[0]

            # Calculate hybrid bonuses
            service_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=services,
                faq_entities=faq_entities["faq_services"],
                entity_type="Service"
            ) if services or faq_entities["faq_services"] else 0.0

            bank_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=banks,
                faq_entities=faq_entities["faq_banks"],
                entity_type="Bank"
            ) if banks or faq_entities["faq_banks"] else 0.0

            error_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=errors,
                faq_entities=faq_entities["faq_errors"],
                entity_type="Error"
            ) if errors or faq_entities["faq_errors"] else 0.0

            action_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=actions,
                faq_entities=faq_entities["faq_actions"],
                entity_type="Action"
            ) if actions or faq_entities["faq_actions"] else 0.0

            feature_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=features,
                faq_entities=faq_entities["faq_features"],
                entity_type="Feature"
            ) if features or faq_entities["faq_features"] else 0.0

            fee_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=fees,
                faq_entities=faq_entities["faq_fees"],
                entity_type="Fee"
            ) if fees or faq_entities["faq_fees"] else 0.0

            status_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=statuses,
                faq_entities=faq_entities["faq_statuses"],
                entity_type="Status"
            ) if statuses or faq_entities["faq_statuses"] else 0.0

            limit_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=limits,
                faq_entities=faq_entities["faq_limits"],
                entity_type="Limit"
            ) if limits or faq_entities["faq_limits"] else 0.0

            # NEW: Calculate bonuses for 7 additional entity types
            topic_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("Topic", []),
                faq_entities=faq_entities["faq_topics"],
                entity_type="Topic"
            ) if query_entities.get("Topic") or faq_entities["faq_topics"] else 0.0

            requirement_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("Requirement", []),
                faq_entities=faq_entities["faq_requirements"],
                entity_type="Requirement"
            ) if query_entities.get("Requirement") or faq_entities["faq_requirements"] else 0.0

            timeframe_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("TimeFrame", []),
                faq_entities=faq_entities["faq_timeframes"],
                entity_type="TimeFrame"
            ) if query_entities.get("TimeFrame") or faq_entities["faq_timeframes"] else 0.0

            document_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("Document", []),
                faq_entities=faq_entities["faq_documents"],
                entity_type="Document"
            ) if query_entities.get("Document") or faq_entities["faq_documents"] else 0.0

            account_type_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("AccountType", []),
                faq_entities=faq_entities["faq_account_types"],
                entity_type="AccountType"
            ) if query_entities.get("AccountType") or faq_entities["faq_account_types"] else 0.0

            ui_element_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("UIElement", []),
                faq_entities=faq_entities["faq_ui_elements"],
                entity_type="UIElement"
            ) if query_entities.get("UIElement") or faq_entities["faq_ui_elements"] else 0.0

            contact_channel_bonus = self.hybrid_matcher.get_entity_bonus(
                query_entities=query_entities.get("ContactChannel", []),
                faq_entities=faq_entities["faq_contact_channels"],
                entity_type="ContactChannel"
            ) if query_entities.get("ContactChannel") or faq_entities["faq_contact_channels"] else 0.0

            # Get base components from Cypher result
            entity_matches = r.get("entity_matches", 0)
            rel_types = r.get("rel_types", [])
            exact_matches = r.get("exact_matches", 0) if "exact_matches" in r else 0

            # Calculate rel_weight (same logic as Cypher)
            rel_weight = 1.0
            if 'DESCRIBES_ERROR' in rel_types:
                rel_weight = 1.5
            elif 'ABOUT' in rel_types or 'MENTIONS_BANK' in rel_types or 'MENTIONS_SERVICE' in rel_types:
                rel_weight = 1.5
            elif 'SUGGESTS_ACTION' in rel_types:
                rel_weight = 1.2

            exact_match_bonus = exact_matches * 0.5

            # Recalculate graph_score with HYBRID bonuses (ALL 15 entity types!)
            old_graph_score = r.get("graph_score", 0)
            new_graph_score = (
                entity_matches * rel_weight +
                exact_match_bonus +
                service_bonus +
                bank_bonus +
                error_bonus +
                action_bonus +
                feature_bonus +
                fee_bonus +
                status_bonus +
                limit_bonus +
                topic_bonus +
                requirement_bonus +
                timeframe_bonus +
                document_bonus +
                account_type_bonus +
                ui_element_bonus +
                contact_channel_bonus
            )

            # Update result with ALL 15 entity bonuses
            r["graph_score"] = new_graph_score
            r["service_match_bonus"] = service_bonus
            r["bank_match_bonus"] = bank_bonus
            r["error_match_bonus"] = error_bonus
            r["action_match_bonus"] = action_bonus
            r["feature_match_bonus"] = feature_bonus
            r["fee_match_bonus"] = fee_bonus
            r["status_match_bonus"] = status_bonus
            r["limit_match_bonus"] = limit_bonus
            r["topic_match_bonus"] = topic_bonus
            r["requirement_match_bonus"] = requirement_bonus
            r["timeframe_match_bonus"] = timeframe_bonus
            r["document_match_bonus"] = document_bonus
            r["account_type_match_bonus"] = account_type_bonus
            r["ui_element_match_bonus"] = ui_element_bonus
            r["contact_channel_match_bonus"] = contact_channel_bonus

            # Log significant changes (show ALL bonuses > 0)
            if abs(new_graph_score - old_graph_score) > 0.5:
                logger.info(f"  📊 FAQ {faq_id}: Cypher={old_graph_score:.2f} → Hybrid={new_graph_score:.2f} "
                          f"(Δ={new_graph_score - old_graph_score:+.2f})")

                # Build bonus list dynamically (only show non-zero bonuses)
                all_bonuses = [
                    ("service", service_bonus),
                    ("bank", bank_bonus),
                    ("error", error_bonus),
                    ("action", action_bonus),
                    ("feature", feature_bonus),
                    ("fee", fee_bonus),
                    ("status", status_bonus),
                    ("limit", limit_bonus),
                    ("topic", topic_bonus),
                    ("requirement", requirement_bonus),
                    ("timeframe", timeframe_bonus),
                    ("document", document_bonus),
                    ("account_type", account_type_bonus),
                    ("ui_element", ui_element_bonus),
                    ("contact", contact_channel_bonus)
                ]

                bonus_parts = [f"{name}={value:.1f}" for name, value in all_bonuses if value > 0]
                if bonus_parts:
                    logger.info(f"     Bonuses: {', '.join(bonus_parts)}")

        # Re-sort by new graph_score
        results.sort(key=lambda x: x.get("graph_score", 0), reverse=True)

        return results

    def _semantic_search(self, query: str, top_k: int) -> List[Dict]:
        """Search using semantic similarity (cosine similarity with embeddings)"""
        if not self.embeddings_model:
            return []

        # Encode query
        query_embedding = self.embeddings_model.encode(query).tolist()

        # Get all FAQ nodes with embeddings
        cypher = """
        MATCH (f:FAQ)
        WHERE f.embedding IS NOT NULL
        RETURN f.id as id, f.question as text, f.embedding as embedding
        """

        questions = self.connector.execute_query(cypher)

        # Compute similarities
        results = []
        for q in questions:
            emb = np.array(q["embedding"])
            query_emb = np.array(query_embedding)

            # Cosine similarity
            similarity = np.dot(emb, query_emb) / (np.linalg.norm(emb) * np.linalg.norm(query_emb))

            results.append({
                "node_id": q["id"],
                "score": float(similarity),
                "method": "semantic"
            })

        # Sort and return top-k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


    def _keyword_search(self, query: str, top_k: int) -> List[Dict]:
        """
        Enhanced keyword search with EXACT MATCH priority
        1. First, check for exact/near-exact question matches
        2. Then, search by keywords
        """
        import re
        from difflib import SequenceMatcher

        query_lower = query.lower().strip()

        # STEP 1: Check for exact/near-exact matches first (PRIORITY)
        exact_match_cypher = """
        MATCH (f:FAQ)
        RETURN f.id as id, f.question as question
        """
        all_faqs = self.connector.execute_query(exact_match_cypher)

        exact_matches = []
        for faq in all_faqs:
            faq_question = faq["question"].lower().strip()
            similarity = SequenceMatcher(None, query_lower, faq_question).ratio()

            if similarity > 0.85:  # 85%+ match = exact
                exact_matches.append({
                    "node_id": faq["id"],
                    "score": similarity,
                    "method": "exact_match"
                })
                logger.info(f"🎯 EXACT MATCH ({similarity:.0%}): {faq['question'][:60]}...")

        if exact_matches:
            # Sort by similarity and return
            exact_matches.sort(key=lambda x: x["score"], reverse=True)
            return exact_matches[:top_k]

        # STEP 2: Keyword-based search
        # Extract meaningful keywords (remove stopwords)
        stopwords = {'tôi', 'bạn', 'là', 'có', 'thể', 'được', 'để', 'và', 'hoặc', 'hay',
                     'này', 'đó', 'như', 'thế', 'nào', 'gì', 'sao', 'làm', 'muốn', 'cần',
                     'của', 'cho', 'với', 'từ', 'đến', 'trong', 'ngoài', 'trên', 'dưới',
                     'khi', 'nếu', 'thì', 'mà', 'vì', 'do', 'bởi', 'nhưng', 'còn', 'vẫn',
                     'đang', 'sẽ', 'đã', 'rồi', 'chưa', 'không', 'có thể', 'phải', 'những'}

        words = re.findall(r'[\w]+', query_lower)
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        # Important compound terms
        important_compounds = [
            'gói cước', 'data 3g', 'data 4g', '3g/4g', 'mobile money', 'vnpt money',
            'vnpt pay', 'rút tiền', 'nạp tiền', 'chuyển tiền', 'liên kết', 'ngân hàng',
            'biểu phí', 'hạn mức', 'thời gian', 'hotline', 'tổng đài', 'nhà mạng'
        ]
        compound_terms = [term for term in important_compounds if term in query_lower]

        all_keywords = list(set(keywords + compound_terms))

        if not all_keywords:
            cypher = """
            MATCH (f:FAQ)
            WHERE toLower(f.question) CONTAINS toLower($query)
               OR toLower(f.answer) CONTAINS toLower($query)
            RETURN f.id as id, 1 as match_count
            ORDER BY match_count DESC
            LIMIT $top_k
            """
            results = self.connector.execute_query(cypher, {"query": query, "top_k": top_k})
        else:
            keyword_conditions = " OR ".join([
                f"(toLower(f.question) CONTAINS '{kw}' OR toLower(f.answer) CONTAINS '{kw}')"
                for kw in all_keywords
            ])

            cypher = f"""
            MATCH (f:FAQ)
            WHERE {keyword_conditions}
            WITH f,
                 size([kw IN $keywords WHERE toLower(f.question) CONTAINS kw]) * 2 +
                 size([kw IN $keywords WHERE toLower(f.answer) CONTAINS kw]) as match_count
            WHERE match_count > 0
            RETURN f.id as id, match_count
            ORDER BY match_count DESC
            LIMIT $top_k
            """

            results = self.connector.execute_query(
                cypher,
                {"keywords": all_keywords, "top_k": top_k}
            )

            logger.info(f"Keyword search with terms {all_keywords}: found {len(results)} results")

        max_score = max([r["match_count"] for r in results]) if results else 1
        return [
            {
                "node_id": r["id"],
                "score": r["match_count"] / max_score,
                "method": "keyword"
            }
            for r in results
        ]

    def _find_exact_match_faq(self, query: str, threshold: float = 0.85) -> List[Dict]:
        """
        Find FAQs that exactly or nearly match the query question.
        This is critical for FAQs without entity links.

        Args:
            query: User query
            threshold: Minimum similarity ratio (default 0.85 = 85%)

        Returns:
            List of exact match results with high scores
        """
        from difflib import SequenceMatcher

        query_lower = query.lower().strip()

        # Get all FAQ questions
        cypher = "MATCH (f:FAQ) RETURN f.id as id, f.question as question"
        all_faqs = self.connector.execute_query(cypher)

        exact_matches = []
        for faq in all_faqs:
            if not faq.get("question"):
                continue

            faq_question = faq["question"].lower().strip()
            similarity = SequenceMatcher(None, query_lower, faq_question).ratio()

            if similarity >= threshold:
                exact_matches.append({
                    "node_id": faq["id"],
                    "score": similarity,
                    "method": "exact_match",
                    "similarity": similarity
                })
                logger.info(f"🎯 EXACT MATCH FOUND ({similarity:.0%}): {faq['question'][:60]}...")

        # Sort by similarity (highest first)
        exact_matches.sort(key=lambda x: x["similarity"], reverse=True)
        return exact_matches

    def _intent_keyword_search(self, query: str, intent: str, top_k: int) -> List[Dict]:
        """
        Intent-based keyword search for specific intents (FEE, LIMIT, TIME)

        Uses intent-specific keywords to find FAQs that may be missed by entity graph search.
        This is particularly useful when:
        - The query doesn't contain entities that match Neo4j nodes
        - The FAQ question/answer contains relevant information but isn't linked properly

        Args:
            query: User query
            intent: Classified intent (FEE, LIMIT, TIME)
            top_k: Number of results to return

        Returns:
            List of {node_id, score, method}
        """
        # Define intent-specific keywords for search
        intent_keywords = {
            "FEE": ["phí", "miễn phí", "chi phí", "mất phí", "biểu phí", "chính sách phí"],
            "LIMIT": ["hạn mức", "tối đa", "tối thiểu", "giới hạn", "số tiền tối đa", "vượt quá"],
            "TIME": ["bao lâu", "thời gian", "ngày làm việc", "hoàn tiền", "ngay lập tức", "khi nào"]
        }

        keywords = intent_keywords.get(intent, [])
        if not keywords:
            return []

        # Build Cypher query with OR conditions for all keywords
        keyword_conditions = " OR ".join([
            f"(toLower(f.question) CONTAINS '{kw}' OR toLower(f.answer) CONTAINS '{kw}')"
            for kw in keywords
        ])

        cypher = f"""
        MATCH (f:FAQ)
        WHERE {keyword_conditions}
        WITH f,
             // Score based on how many keywords match in question (higher priority)
             size([kw IN $keywords WHERE toLower(f.question) CONTAINS kw]) * 2 +
             // Score based on how many keywords match in answer
             size([kw IN $keywords WHERE toLower(f.answer) CONTAINS kw]) as keyword_score
        RETURN f.id as id, keyword_score
        ORDER BY keyword_score DESC
        LIMIT $top_k
        """

        results = self.connector.execute_query(
            cypher,
            {"keywords": keywords, "top_k": top_k}
        )

        if not results:
            return []

        # Normalize scores
        max_score = max([r["keyword_score"] for r in results]) if results else 1
        return [
            {
                "node_id": r["id"],
                "score": float(r["keyword_score"]) / max_score * 0.8,  # Scale down to not override entity results
                "method": f"intent_keyword_{intent.lower()}"
            }
            for r in results
        ]

    def _aggregate_scores(self, results: List[Dict], has_entities: bool = False, override_semantic_weight: float = None) -> List[Dict]:
        """
        Aggregate scores from different search methods

        HYBRID MODE WEIGHTING (when has_entities=True):
        - Entity graph: config.HYBRID_WEIGHT_ENTITY_GRAPH (default: 0.9)
        - Semantic: config.HYBRID_WEIGHT_SEMANTIC (default: 0.1)
        - Keyword: config.HYBRID_WEIGHT_KEYWORD (default: 0.0)

        FALLBACK WEIGHTING (when has_entities=False):
        - Semantic: 0.6, Keyword: 0.4

        Args:
            results: List of search results
            has_entities: Whether entities were found in query
            override_semantic_weight: Optional override for semantic weight (for Error queries)
        """
        # Group by node_id
        node_scores = {}

        for result in results:
            node_id = result["node_id"]
            method = result["method"]
            score = result["score"]

            if node_id not in node_scores:
                node_scores[node_id] = {"scores": {}, "node_id": node_id, "methods": []}

            node_scores[node_id]["scores"][method] = score
            node_scores[node_id]["methods"].append(method)

        # ADAPTIVE WEIGHTS based on whether entities were found
        if has_entities:
            # HYBRID MODE: Use configurable weights (with optional override)
            semantic_weight = override_semantic_weight if override_semantic_weight else config.HYBRID_WEIGHT_SEMANTIC
            graph_weight = 1.0 - semantic_weight if override_semantic_weight else config.HYBRID_WEIGHT_ENTITY_GRAPH

            weights = {
                "entity_graph": graph_weight,
                "semantic": semantic_weight,
                "keyword": config.HYBRID_WEIGHT_KEYWORD
            }
            logger.info(f"Using HYBRID weighting (graph: {weights['entity_graph']}, "
                       f"semantic: {weights['semantic']}, keyword: {weights['keyword']})")
        else:
            # NO ENTITIES: Fallback to semantic + keyword
            weights = {
                "semantic": 0.6,
                "keyword": 0.4,
                "entity_graph": 0.0
            }
            logger.info("Using SEMANTIC-FIRST weighting (semantic: 0.6, keyword: 0.4)")

        aggregated = []
        for node_id, data in node_scores.items():
            # Calculate weighted score
            weighted_score = 0.0
            total_weight = 0.0

            for method, weight in weights.items():
                if method in data["scores"] and weight > 0:
                    weighted_score += data["scores"][method] * weight
                    total_weight += weight

            # Normalize by total weight used (in case some methods are missing)
            if total_weight > 0:
                final_score = weighted_score / total_weight
            else:
                final_score = 0.0

            aggregated.append({
                "node_id": node_id,
                "score": final_score,
                "component_scores": data["scores"],  # Keep for logging
                "methods": list(set(data["methods"]))
            })

        return aggregated

    def _get_graph_context(
        self,
        relevant_nodes: List[Dict],
        query_entities: Dict,
        user_query: str = "",
        intent: str = ""
    ) -> List[Dict]:
        """
        Get context by traversing the graph from relevant nodes
        Applies EARLY exact match boosting before final ranking

        Args:
            relevant_nodes: List of {node_id, score}
            query_entities: Entities from query
            user_query: Original user query for exact match detection
            intent: Query intent (TROUBLESHOOT, HOW_TO, etc.)

        Returns:
            List of context items
        """
        context = []
        query_lower = user_query.lower() if user_query else ""

        for node in relevant_nodes:
            node_id = node["node_id"]
            relevance_score = node["score"]

            # Log component scores if available (for hybrid mode monitoring)
            if "component_scores" in node:
                logger.debug(f"FAQ {node_id} - Component scores: {node['component_scores']}, "
                           f"Final: {relevance_score:.3f}, Methods: {node.get('methods', [])}")

            # Get FAQ, answer, and related info using Cypher
            # UPDATED: Retrieve ALL entity types with ENRICHED PROPERTIES for comprehensive context
            cypher = """
            MATCH (f:FAQ {id: $node_id})
            OPTIONAL MATCH (f)-[:MENTIONS_SERVICE]->(s:Service)
            OPTIONAL MATCH (f)-[:MENTIONS_BANK]->(b:Bank)
            OPTIONAL MATCH (f)-[:DESCRIBES_ERROR]->(e:Error)
            OPTIONAL MATCH (f)-[:SUGGESTS_ACTION]->(act:Action)
            OPTIONAL MATCH (f)-[:USES_FEATURE]->(feat:Feature)
            OPTIONAL MATCH (f)-[:HAS_FEE]->(fee:Fee)
            OPTIONAL MATCH (f)-[:HAS_LIMIT]->(lim:Limit)
            OPTIONAL MATCH (f)-[:HAS_STATUS]->(stat:Status)
            OPTIONAL MATCH (f)-[:HAS_TIMEFRAME]->(tf:TimeFrame)
            OPTIONAL MATCH (f)-[:REQUIRES]->(req:Requirement)
            OPTIONAL MATCH (f)-[:REQUIRES_DOCUMENT]->(doc:Document)
            OPTIONAL MATCH (f)-[:AFFECTS_ACCOUNT]->(acc:AccountType)
            OPTIONAL MATCH (f)-[:NAVIGATES_TO]->(ui:UIElement)
            OPTIONAL MATCH (f)-[:CONTACTS]->(contact:ContactChannel)
            OPTIONAL MATCH (f)-[:SIMILAR_TO]-(similar:FAQ)
            OPTIONAL MATCH (f)-[:ABOUT]->(t:Topic)
            OPTIONAL MATCH (f)-[:HAS_LINK]->(link:UsefulLink)
            RETURN f,
                   collect(DISTINCT s.name) as services,
                   collect(DISTINCT b.name) as banks,
                   collect(DISTINCT {name: e.name, solution: e.solution}) as errors,
                   collect(DISTINCT act.name) as actions,
                   collect(DISTINCT feat.name) as features,
                   collect(DISTINCT fee.name) as fees,
                   collect(DISTINCT lim.name) as limits,
                   collect(DISTINCT stat.name) as statuses,
                   collect(DISTINCT tf.name) as timeframes,
                   collect(DISTINCT {name: req.name, description: req.description}) as requirements,
                   collect(DISTINCT {name: doc.name, description: doc.description}) as documents,
                   collect(DISTINCT acc.name) as account_types,
                   collect(DISTINCT ui.name) as ui_elements,
                   collect(DISTINCT {name: contact.name, phone: contact.phone, description: contact.description}) as contact_channels,
                   collect(DISTINCT {question: similar.question, id: similar.id}) as related_questions,
                   collect(DISTINCT t.name) as topics,
                   collect(DISTINCT {name: link.name, url: link.url, description: link.description}) as useful_links
            """

            result = self.connector.execute_query(cypher, {"node_id": node_id})

            # Separate query for Case nodes and their Steps
            case_cypher = """
            MATCH (f:FAQ {id: $node_id})-[:HAS_CASE]->(case:Case)
            OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
            RETURN case.case_id as case_id,
                   case.name as case_name,
                   case.description as case_description,
                   case.case_type as case_type,
                   case.method as case_method,
                   case.keywords as keywords,
                   case.status_values as status_values,
                   collect({number: step.number, text: step.text}) as steps
            ORDER BY case.case_id
            """

            case_results = self.connector.execute_query(case_cypher, {"node_id": node_id})

            if not result:
                continue

            data = result[0]
            faq = data.get("f", {})

            # EARLY EXACT MATCH BOOST (before final ranking)
            # This ensures exact matches stay in top_k even after aggregation
            question_text = faq.get("question", "")
            exact_match_score = 0.0  # Track exact match for later use
            if query_lower and question_text:
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(None, query_lower, question_text.lower()).ratio()
                exact_match_score = similarity  # Store for later use

                if similarity > 0.9:  # 90%+ exact match
                    # MAJOR BOOST - multiply score to ensure it stays in top_k
                    relevance_score = min(relevance_score * 2.5, 1.0)
                    logger.info(f"🎯 EARLY EXACT MATCH BOOST ({similarity:.2%}): {question_text[:80]}...")
                elif similarity > 0.75:  # 75-90% high similarity
                    relevance_score = min(relevance_score * 1.5, 1.0)
                    logger.info(f"✓ EARLY HIGH SIMILARITY ({similarity:.2%}): {question_text[:80]}...")

            # Get alternative actions
            alternative_actions = self._get_alternative_actions(data.get("actions", []))

            # NEW: Select appropriate Case based on query
            selected_case = None
            case_steps = []

            if case_results:  # Check if FAQ has Case nodes
                # Match Case based on EXTRACTED ENTITIES (Feature) + query keywords
                query_lower = user_query.lower()

                # Extract Feature entities for case matching (FIXED: Use correct key 'Feature')
                extracted_features = query_entities.get('Feature', []) if query_entities else []
                logger.info(f"📋 Extracted features for case matching: {extracted_features}")

                # Scoring for each case
                case_scores = []
                for case in case_results:
                    score = 0
                    case_name = (case.get('case_name') or '').lower()
                    case_desc = (case.get('case_description') or '').lower()
                    case_method = (case.get('case_method') or '').lower()

                    # Get new Case fields from Neo4j
                    case_keywords = case.get('keywords', [])
                    case_status_values = case.get('status_values', [])

                    # PRIORITY 1: Match with extracted Feature entities (HIGHER SCORE)
                    for feature in extracted_features:
                        feature_lower = feature.lower()

                        # Match "Chuyển khoản ngân hàng" (CHECK THIS FIRST - more specific)
                        if 'chuyển khoản' in feature_lower and 'ngân hàng' in feature_lower:
                            if 'chuyển khoản' in case_name or 'chuyển khoản' in case_desc or 'qr' in case_name:
                                score += 20  # Higher score for exact match
                                logger.info(f"  ✅ Feature match 'Chuyển khoản ngân hàng': {case_name}")

                        # Match "liên kết ngân hàng" or "ngân hàng liên kết"
                        elif 'liên kết' in feature_lower and 'ngân hàng' in feature_lower:
                            if 'liên kết' in case_name or 'liên kết' in case_desc or 'bank_linked' in case_method:
                                score += 20  # Same as chuyển khoản
                                logger.info(f"  ✅ Feature match 'liên kết ngân hàng': {case_name}")

                        # Match "QR code" or "mã QR"
                        elif 'qr' in feature_lower:
                            if 'qr' in case_name or 'qr' in case_desc or 'chuyển khoản' in case_name:
                                score += 15
                                logger.info(f"  ✅ Feature match 'QR': {case_name}")

                    # PRIORITY 2: Status-based matching (NEW - using status_values field)
                    extracted_status = query_entities.get('Status', []) if query_entities else []

                    if extracted_status and case_status_values:
                        for status in extracted_status:
                            status_lower = status.lower()

                            # Match "đã nhận tiền" (HIGHEST PRIORITY - conditional)
                            if 'đã nhận tiền' in status_lower or 'đã nhận được tiền' in status_lower:
                                if 'đã nhận tiền' in case_status_values:
                                    score += 25  # Higher than regular status
                                    logger.info(f"  ✅ Conditional match 'đã nhận tiền': {case_name}")

                            # Match "chưa nhận tiền" (HIGHEST PRIORITY - conditional)
                            elif 'chưa nhận tiền' in status_lower or 'chưa nhận được tiền' in status_lower:
                                if 'chưa nhận tiền' in case_status_values:
                                    score += 25  # Higher than regular status
                                    logger.info(f"  ✅ Conditional match 'chưa nhận tiền': {case_name}")

                            # Match "thành công"
                            elif 'thành công' in status_lower:
                                if 'thành công' in case_status_values:
                                    score += 20
                                    logger.info(f"  ✅ Status match 'thành công': {case_name}")

                            # Match "thất bại" or "không thành công"
                            elif any(word in status_lower for word in ['thất bại', 'không thành công', 'lỗi']):
                                if 'thất bại' in case_status_values:
                                    score += 20
                                    logger.info(f"  ✅ Status match 'thất bại': {case_name}")

                            # Match "đang xử lý"
                            elif 'đang xử lý' in status_lower or 'chờ xử lý' in status_lower:
                                if 'đang xử lý' in case_status_values:
                                    score += 20
                                    logger.info(f"  ✅ Status match 'đang xử lý': {case_name}")

                    # PRIORITY 3: Keyword-based matching (NEW - using keywords field)
                    # Use keywords to differentiate cases when Feature match is ambiguous
                    if case_keywords:
                        keyword_matches = 0
                        for keyword in case_keywords:
                            if isinstance(keyword, str) and keyword in query_lower:
                                keyword_matches += 1
                                logger.info(f"  ⚡ Keyword match '{keyword}': {case_name}")

                        # Bonus for multiple keyword matches (indicates better fit)
                        if keyword_matches > 0:
                            score += keyword_matches * 3  # 3 points per matched keyword

                    # PRIORITY 4: Fallback to old keyword matching
                    if score == 0:  # Only if nothing else matched
                        if 'liên kết' in query_lower or 'liên kết trực tiếp' in query_lower:
                            if 'liên kết' in case_name or 'liên kết' in case_desc or 'bank_linked' in case_method:
                                score += 10

                        if 'chuyển khoản' in query_lower or 'qr' in query_lower or 'mã qr' in query_lower:
                            if 'chuyển khoản' in case_name or 'chuyển khoản' in case_desc or 'qr' in case_method:
                                score += 10

                    # Default: first case gets small bonus
                    if case == case_results[0]:
                        score += 1

                    case_scores.append((case, score))

                # Log all case scores for debugging
                logger.info(f"📊 Case Scores:")
                for case, score in sorted(case_scores, key=lambda x: x[1], reverse=True):
                    case_name = case.get('case_name', 'Unknown')
                    logger.info(f"   {case_name}: {score} points")

                # Select case with highest score
                best_case, best_score = max(case_scores, key=lambda x: x[1])

                # Build selected_case dict
                selected_case = {
                    'case_id': best_case.get('case_id'),
                    'name': best_case.get('case_name'),
                    'description': best_case.get('case_description'),
                    'case_type': best_case.get('case_type'),
                    'method': best_case.get('case_method')
                }

                # Extract and sort steps
                raw_steps = best_case.get('steps', [])
                valid_steps = [s for s in raw_steps if s.get('text')]
                case_steps = sorted(valid_steps, key=lambda x: x.get('number', 0))

                logger.info(f"✅ Selected Case: {selected_case.get('name')} ({len(case_steps)} steps, score: {best_score})")

            # NEW: Build answer from Case steps if available
            # SPECIAL CASE: For TROUBLESHOOT with multiple cases, return FULL FAQ
            # because user needs to know ALL possible cases/scenarios
            full_answer = faq.get("answer", "")
            num_cases = len(case_results) if case_results else 0

            # Check if full_answer contains step-by-step instructions
            has_step_instructions = bool(re.search(r'Bước\s*\d+', full_answer, re.IGNORECASE))

            # Intents that need FULL FAQ when multiple cases exist
            full_info_intents = {"TROUBLESHOOT", "WHY", "HOW_TO"}

            # INFO_REQUEST with step instructions should also return full FAQ
            # Because user is asking HOW TO do something (e.g., "vào mục nào?")
            if intent in full_info_intents and num_cases > 1:
                # TROUBLESHOOT/WHY/HOW_TO with multiple cases → return FULL FAQ answer
                case_based_answer = full_answer
                logger.info(f"📝 Answer path: Using FULL FAQ for {intent} (has {num_cases} cases)")
            elif has_step_instructions and intent in {"INFO_REQUEST", "HOW_TO"}:
                # FAQ has step-by-step instructions → return FULL answer
                # This handles cases like "thanh toán hóa đơn viễn thông thì vào mục nào?"
                case_based_answer = full_answer
                logger.info(f"📝 Answer path: Using FULL FAQ for {intent} (has step instructions)")
            elif case_steps and selected_case:
                # Use Case steps instead of full FAQ answer
                steps_text = "\n".join([
                    f'Bước {step["number"]}: {step["text"]}'
                    for step in case_steps
                ])
                case_name = selected_case.get('name', '')
                case_based_answer = f"{case_name}:\n\n{steps_text}"
                logger.info(f"📝 Answer path: Using Step nodes from Case")
            elif selected_case and selected_case.get('description'):
                # CRITICAL FIX: Case description is usually just a title/summary
                # We should use the FULL FAQ answer instead when no Step nodes exist
                case_desc = selected_case.get('description', '')

                # Check if description is too short to be useful (likely just a title)
                # A proper answer should have at least 100 chars with steps/details
                if len(case_desc) < 100 or not any(
                    indicator in case_desc.lower()
                    for indicator in ['bước', '1.', '2.', '-', '•', 'chọn', 'nhấn', 'vào']
                ):
                    # Description is just a title - use FULL FAQ answer
                    case_based_answer = full_answer
                    logger.info(f"📝 Answer path: Case description too short ({len(case_desc)} chars), using FULL FAQ answer")
                    logger.info(f"   Short description was: {case_desc[:100]}...")
                else:
                    # Description has actual steps/content
                    case_based_answer = case_desc
                    logger.info(f"📝 Answer path: Using Case description (has content)")
                    logger.info(f"   Description preview: {case_desc[:200]}...")
            else:
                # NO Case nodes - but check if we have Feature entities to filter answer
                full_answer = faq.get("answer", "")
                extracted_features = query_entities.get('Feature', []) if query_entities else []

                if extracted_features and full_answer:
                    # Try to extract the matching case section from the answer
                    case_based_answer = self._extract_matching_case_from_answer(
                        full_answer, extracted_features, user_query
                    )
                    if case_based_answer and case_based_answer != full_answer:
                        logger.info(f"📝 Answer path: Extracted matching case from multi-case answer")
                    else:
                        logger.info(f"📝 Answer path: Using full FAQ answer (no case match)")
                        case_based_answer = full_answer
                else:
                    logger.info(f"📝 Answer path: Using full FAQ answer (no features)")
                    case_based_answer = full_answer

            context_item = {
                "question_id": node_id,
                "question": question_text,
                "answer": case_based_answer,  # Use Case-based answer if available
                "relevance_score": relevance_score,
                "related_entities": {
                    # Core entities
                    "services": [s for s in data.get("services", []) if s],
                    "banks": [b for b in data.get("banks", []) if b],
                    # ENRICHED: Error now includes solution
                    "errors": [e for e in data.get("errors", []) if e and e.get("name")],
                    "actions": [a for a in data.get("actions", []) if a],
                    "features": [f for f in data.get("features", []) if f],
                    "topics": [t for t in data.get("topics", []) if t],
                    # NEW: Additional entity types for comprehensive context
                    "fees": [f for f in data.get("fees", []) if f],
                    "limits": [l for l in data.get("limits", []) if l],
                    "statuses": [s for s in data.get("statuses", []) if s],
                    "timeframes": [t for t in data.get("timeframes", []) if t],
                    # ENRICHED: Requirement now includes description
                    "requirements": [r for r in data.get("requirements", []) if r and r.get("name")],
                    # ENRICHED: Document now includes description
                    "documents": [d for d in data.get("documents", []) if d and d.get("name")],
                    "account_types": [a for a in data.get("account_types", []) if a],
                    "ui_elements": [u for u in data.get("ui_elements", []) if u],
                    # ENRICHED: ContactChannel now includes phone and description
                    "contact_channels": [c for c in data.get("contact_channels", []) if c and c.get("name")],
                    # NEW: UsefulLink with url
                    "useful_links": [l for l in data.get("useful_links", []) if l and l.get("url")],
                },
                "related_questions": [
                    {"question": rq["question"]}
                    for rq in data.get("related_questions", [])
                    if rq.get("question")
                ][:3],
                "alternative_actions": alternative_actions,
                # NEW: Add Case info
                "selected_case": selected_case.get('name') if selected_case else None,
                "case_steps": case_steps,
                # CRITICAL: Track exact match score to skip focused extraction for exact matches
                "exact_match_score": exact_match_score
            }

            context.append(context_item)

        return context

    def _extract_matching_case_from_answer(self, answer: str, features: List[str], query: str) -> str:
        """
        Extract the matching case section from a multi-case answer.

        When variant FAQs don't have Case nodes, this parses the answer to find
        the case that matches the Feature entities.

        Format expected:
        - Case 1 name:
          Steps...
        - Case 2 name:
          Steps...
        """
        # Split answer into case sections (starts with "- ")
        lines = answer.split('\n')
        cases = []
        current_case = []
        current_case_name = None

        # First, check if this is a simple bullet list (not multi-case answer)
        # Bullet lists have:
        # 1. Intro text before the first "- " item
        # 2. Each "- " item is short (no sub-content, no nested steps)
        has_intro_text = False
        bullet_items = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('- '):
                bullet_items.append(stripped)
            elif stripped and not bullet_items:
                # Text before any bullet = intro text
                has_intro_text = True

        # If has intro text and bullet items are short (simple list), return full answer
        if has_intro_text and bullet_items:
            # Check if bullet items are short (no numbered steps, no nested content)
            avg_bullet_len = sum(len(b) for b in bullet_items) / len(bullet_items) if bullet_items else 0
            has_no_steps = not any(any(step in b for step in ['1.', '2.', '3.', 'Bước']) for b in bullet_items)

            if avg_bullet_len < 150 and has_no_steps:
                # This is a simple bullet list, not multi-case - return full answer
                logger.debug(f"  📋 Detected simple bullet list (avg_len={avg_bullet_len:.0f}), returning full answer")
                return answer

        for line in lines:
            # Check if line starts a new case (e.g., "- Nạp tiền từ ngân hàng liên kết:")
            if line.strip().startswith('- '):
                # Save previous case
                if current_case and current_case_name:
                    cases.append((current_case_name, '\n'.join(current_case)))
                # Start new case
                current_case_name = line.strip()[2:]  # Remove "- " prefix
                current_case = [line]
            else:
                # Continue current case
                if current_case is not None:
                    current_case.append(line)

        # Save last case
        if current_case and current_case_name:
            cases.append((current_case_name, '\n'.join(current_case)))

        # No cases found, return full answer
        if not cases:
            return answer

        # Match case name with Feature entities
        query_lower = query.lower()
        for feature in features:
            feature_lower = feature.lower()

            # Check each case name
            for case_name, case_content in cases:
                case_name_lower = case_name.lower()

                # Match "Chuyển khoản ngân hàng"
                if 'chuyển khoản' in feature_lower:
                    if 'chuyển khoản' in case_name_lower:
                        logger.info(f"  📌 Matched case by feature 'chuyển khoản': {case_name[:50]}...")
                        return case_content

                # Match "liên kết ngân hàng" or "tài khoản liên kết"
                elif 'liên kết' in feature_lower:
                    if 'liên kết' in case_name_lower:
                        logger.info(f"  📌 Matched case by feature 'liên kết': {case_name[:50]}...")
                        return case_content

                # Match "QR"
                elif 'qr' in feature_lower:
                    if 'qr' in case_name_lower:
                        logger.info(f"  📌 Matched case by feature 'QR': {case_name[:50]}...")
                        return case_content

        # No feature match - try status/conditional matching (NEW)
        for case_name, case_content in cases:
            case_content_lower = case_content.lower()

            # Match status-based cases
            if 'thành công' in query_lower and 'không thành công' not in query_lower:
                if 'thành công' in case_content_lower and 'không thành công' not in case_content_lower:
                    logger.info(f"  📌 Matched case by status 'thành công': {case_name[:50]}...")
                    return case_content

            if 'thất bại' in query_lower or 'không thành công' in query_lower:
                if 'thất bại' in case_content_lower or 'không thành công' in case_content_lower:
                    logger.info(f"  📌 Matched case by status 'thất bại': {case_name[:50]}...")
                    return case_content

            if 'đang xử lý' in query_lower:
                if 'đang xử lý' in case_content_lower:
                    logger.info(f"  📌 Matched case by status 'đang xử lý': {case_name[:50]}...")
                    return case_content

        # Match conditional cases ("đã nhận" vs "chưa nhận" tiền) (NEW)
        if 'đã nhận được tiền' in query_lower or 'đã nhận tiền' in query_lower:
            for case_name, case_content in cases:
                if 'đã nhận được tiền' in case_content.lower() or 'đã nhận tiền' in case_content.lower():
                    logger.info(f"  📌 Matched case by condition 'đã nhận tiền': {case_name[:50]}...")
                    return case_content

        elif 'chưa nhận được tiền' in query_lower or 'chưa nhận tiền' in query_lower:
            for case_name, case_content in cases:
                if 'chưa nhận được tiền' in case_content.lower() or 'chưa nhận tiền' in case_content.lower():
                    logger.info(f"  📌 Matched case by condition 'chưa nhận tiền': {case_name[:50]}...")
                    return case_content

        # Fallback to keyword matching in query
        for case_name, case_content in cases:
            case_name_lower = case_name.lower()

            if 'chuyển khoản' in query_lower and 'chuyển khoản' in case_name_lower:
                logger.info(f"  📌 Matched case by query keyword 'chuyển khoản': {case_name[:50]}...")
                return case_content

            if 'liên kết' in query_lower and 'liên kết' in case_name_lower:
                logger.info(f"  📌 Matched case by query keyword 'liên kết': {case_name[:50]}...")
                return case_content

        # No match - return full answer
        return answer

    def _get_alternative_actions(self, actions: List[str]) -> List[Dict]:
        """Get alternative actions for given actions"""
        if not actions:
            return []

        cypher = """
        MATCH (a:Action)-[r:ALTERNATIVE_TO]->(alt:Action)
        WHERE a.name IN $actions
        RETURN alt.name as action, r.reason as reason
        """

        results = self.connector.execute_query(cypher, {"actions": actions})

        return [
            {"action": r["action"], "reason": r.get("reason", "")}
            for r in results
        ]

    def _rank_results(self, context: List[Dict], query: str, intent: str = "GENERAL", query_entities: Dict = None) -> Dict:
        """
        Rank and format results with INTENT-AWARE and ERROR-AWARE scoring

        Args:
            context: List of candidate results
            query: User query
            intent: Classified intent
            query_entities: Extracted entities including errors
        """
        if query_entities is None:
            query_entities = {}

        # STEP 1: Apply intent-based, topic-based, and error-based boosting
        query_lower = query.lower()
        has_errors = bool(query_entities.get("Error", []))
        query_topics = query_entities.get("Topic", [])

        for result in context:
            answer_lower = result.get("answer", "").lower()
            question_lower = result.get("question", "").lower()
            faq_topics = result.get("related_entities", {}).get("topics", [])

            # Base score
            base_score = result.get("relevance_score", 0.5)

            # BOOST 0: EXACT QUESTION MATCHING (Highest priority)
            from difflib import SequenceMatcher
            exact_match_boost = 0.0
            similarity = SequenceMatcher(None, query_lower, question_lower).ratio()

            if similarity > 0.95:  # 95%+ similarity - NEAR PERFECT MATCH
                exact_match_boost = 5.0  # DOMINANT boost - this FAQ is almost certainly correct
                logger.info(f"🎯 NEAR-PERFECT match ({similarity:.2%}): {result.get('question', '')[:80]}")
            elif similarity > 0.9:  # 90%+ similarity
                exact_match_boost = 2.0  # STRONG boost for exact match
                logger.info(f"Exact match found ({similarity:.2%}): {result.get('question', '')[:80]}")
            elif similarity > 0.75:  # 75-90% similarity
                exact_match_boost = 0.5  # MODERATE boost for very similar
                logger.info(f"High similarity ({similarity:.2%}): {result.get('question', '')[:80]}")

            # CRITICAL PENALTY: Check for missing CRITICAL keywords that change meaning
            # e.g., "hủy liên kết" vs "liên kết" are semantically opposite!
            critical_action_keywords = [
                ("hủy", ["hủy", "gỡ bỏ", "xóa"]),  # query_keyword -> possible FAQ matches
                ("gỡ bỏ", ["hủy", "gỡ bỏ", "xóa"]),
                ("thêm", ["thêm", "tạo", "đăng ký"]),
                ("tạo", ["thêm", "tạo", "đăng ký"]),
                ("đổi", ["đổi", "thay đổi", "cập nhật"]),
                ("mở khóa", ["mở khóa", "unlock"]),
                ("khóa", ["khóa", "lock"]),
            ]

            for query_kw, faq_matches in critical_action_keywords:
                if query_kw in query_lower:
                    # Query has this critical keyword - check if FAQ has it
                    if not any(faq_match in question_lower for faq_match in faq_matches):
                        # FAQ is MISSING the critical keyword - heavy penalty
                        # This prevents "hủy liên kết" matching "liên kết"
                        exact_match_boost -= 3.0  # Significant penalty
                        logger.info(f"⚠️ CRITICAL KEYWORD MISSING: Query has '{query_kw}' but FAQ doesn't - penalty applied")
                        break

            # BOOST 0.5: TOPIC MATCHING (NEW - prevents wrong topic results)
            topic_boost = 0.0
            if query_topics:
                for q_topic in query_topics:
                    q_topic_lower = q_topic.lower()
                    # Exact topic match
                    if any(q_topic_lower == faq_topic.lower() for faq_topic in faq_topics):
                        topic_boost += 0.5  # STRONG boost for exact topic match
                        logger.info(f"✓ TOPIC boost: Exact match '{q_topic}' in FAQ")
                        break
                    # Check if topic keyword appears in question
                    elif q_topic_lower in question_lower:
                        topic_boost += 0.3  # MODERATE boost if topic in question
                        logger.info(f"✓ TOPIC boost: Found '{q_topic}' in question text")
                        break

                # PENALTY if query has specific topic but FAQ has DIFFERENT topic
                if faq_topics and topic_boost == 0.0:
                    # Check if FAQ topic is contradictory (e.g., "Mở khóa" vs "Hủy")
                    contradictory_topics = {
                        "mở khóa": ["hủy", "khóa tài khoản", "đổi mật khẩu"],
                        "khóa": ["mở khóa", "đổi mật khẩu"],
                        "hủy": ["mở khóa", "tạo", "đăng ký", "đổi mật khẩu"],
                        "tạo": ["hủy", "xóa"],
                        "đăng ký": ["hủy", "xóa"],
                        "đổi mật khẩu": ["mở khóa", "khóa", "hủy", "quên mật khẩu"],
                        "quên mật khẩu": ["đổi mật khẩu"]
                    }
                    for q_topic in query_topics:
                        q_topic_lower = q_topic.lower()
                        for q_key, contradictory_list in contradictory_topics.items():
                            if q_key in q_topic_lower:
                                for faq_topic in faq_topics:
                                    if any(contra in faq_topic.lower() for contra in contradictory_list):
                                        topic_boost -= 0.8  # HEAVY PENALTY for contradictory topic
                                        logger.info(f"⚠️ TOPIC penalty: FAQ about '{faq_topic}' contradicts query topic '{q_topic}'")
                                        break

            # BOOST 1: Intent-specific boosting
            intent_boost = 0.0

            if intent == "TROUBLESHOOT":
                # Boost answers containing troubleshooting keywords
                troubleshoot_keywords = [
                    "kiểm tra trạng thái", "trạng thái giao dịch",
                    "chưa nhận được", "phải làm", "hãy làm theo",
                    "sao kê", "liên hệ", "hỗ trợ", "khắc phục"
                ]
                for keyword in troubleshoot_keywords:
                    if keyword in answer_lower or keyword in question_lower:
                        intent_boost += 0.15

                # MAJOR BOOST if question mentions problem
                if "chưa" in question_lower or "không" in question_lower or "lỗi" in question_lower:
                    intent_boost += 0.3

            elif intent == "FEE":
                # BOOST for FAQs about fees/costs
                fee_keywords = [
                    "phí", "miễn phí", "chi phí", "mất phí", "có phí", "không phí",
                    "biểu phí", "bảng phí", "phí dịch vụ", "chính sách phí"
                ]
                for keyword in fee_keywords:
                    if keyword in question_lower:
                        intent_boost += 0.5  # STRONG boost for fee in question
                        logger.info(f"✓ FEE boost: Found '{keyword}' in question")
                        break
                    elif keyword in answer_lower:
                        intent_boost += 0.25  # Moderate boost for fee in answer
                        logger.info(f"✓ FEE boost: Found '{keyword}' in answer")
                        break

            elif intent == "LIMIT":
                # BOOST for FAQs about limits
                limit_keywords = [
                    "hạn mức", "tối đa", "tối thiểu", "giới hạn", "limit",
                    "số tiền tối đa", "số lượng tối đa", "vượt quá", "quá hạn mức"
                ]
                for keyword in limit_keywords:
                    if keyword in question_lower:
                        intent_boost += 0.5  # STRONG boost for limit in question
                        logger.info(f"✓ LIMIT boost: Found '{keyword}' in question")
                        break
                    elif keyword in answer_lower:
                        intent_boost += 0.25  # Moderate boost for limit in answer
                        logger.info(f"✓ LIMIT boost: Found '{keyword}' in answer")
                        break

            elif intent == "TIME":
                # BOOST for FAQs about time/duration
                time_keywords = [
                    "bao lâu", "thời gian", "ngay lập tức", "real-time",
                    "ngày làm việc", "trong vòng", "sau khi", "mấy ngày",
                    "khi nào", "hoàn tiền", "hoàn trả"
                ]
                for keyword in time_keywords:
                    if keyword in question_lower:
                        intent_boost += 0.5  # STRONG boost for time in question
                        logger.info(f"✓ TIME boost: Found '{keyword}' in question")
                        break
                    elif keyword in answer_lower:
                        intent_boost += 0.25  # Moderate boost for time in answer
                        logger.info(f"✓ TIME boost: Found '{keyword}' in answer")
                        break

            elif intent == "HOW_TO":
                # CRITICAL: Check for troubleshooting signals FIRST (in QUESTION - highest priority)
                import re
                troubleshoot_signals_question = [
                    "bị lỗi", "báo lỗi", "gặp lỗi", "lỗi", "thất bại", "không thành công",
                    "chưa nhận được", "bị trừ", "tại sao", "sao lại", "giao dịch thất bại",
                    "không được", "không thể", "bị từ chối"
                ]
                # Also check for "báo" + error message patterns
                error_message_patterns = [
                    r'báo\s+"[^"]*(?:lỗi|không\s+hợp\s+lệ|thất\s+bại)',  # "báo "lỗi..." or "báo "không hợp lệ..."
                    r'báo\s+lỗi',  # "báo lỗi"
                    r'báo\s+không',  # "báo không..."
                ]

                is_troubleshoot_faq = False
                # Check text signals
                for signal in troubleshoot_signals_question:
                    if signal in question_lower:
                        is_troubleshoot_faq = True
                        logger.info(f"⚠️ HOW_TO STRONG penalty: Question contains troubleshooting signal '{signal}'")
                        break

                # Check regex patterns for error messages
                if not is_troubleshoot_faq:
                    for pattern in error_message_patterns:
                        if re.search(pattern, question_lower):
                            is_troubleshoot_faq = True
                            logger.info(f"⚠️ HOW_TO STRONG penalty: Question contains error message pattern")
                            break

                # If question is about troubleshooting, apply HEAVY penalty immediately
                if is_troubleshoot_faq:
                    intent_boost -= 1.5  # VERY HEAVY penalty for troubleshooting FAQs in HOW_TO queries (increased from 1.2)
                else:
                    # Only then check for instructional content

                    # CRITICAL: Detect procedural content with numbered steps (HIGHEST priority)
                    # Look for patterns like "Bước 1:", "Step 1:", "1.", "2)", etc.
                    step_patterns = [
                        r'bước\s+\d+[:\.\)]',  # "Bước 1:", "Bước 2."
                        r'step\s+\d+[:\.\)]',   # "Step 1:", "Step 2)"
                        r'^\d+[\.\)]',          # "1.", "2)" at start of line
                    ]
                    has_steps = False
                    for pattern in step_patterns:
                        if re.search(pattern, answer_lower, re.MULTILINE | re.IGNORECASE):
                            has_steps = True
                            break

                    if has_steps:
                        intent_boost += 2.5  # EXTREME boost for step-by-step instructions to overcome aggregation filtering
                        logger.info(f"✓ HOW_TO PROCEDURAL boost: FAQ contains numbered steps")

                    # STRONG BOOST for instructional signals (but lower priority than procedural)
                    how_to_signals = [
                        "làm thế nào", "như thế nào", "cách", "hướng dẫn",
                        "bước", "step", "để thực hiện", "quy trình", "thủ tục"
                    ]
                    for signal in how_to_signals:
                        if signal in question_lower or signal in answer_lower:
                            intent_boost += 0.3  # Moderate boost for how-to keywords
                            logger.info(f"✓ HOW_TO boost: Found '{signal}' in instructional FAQ")
                            break

            # BOOST 2: Error-specific boosting
            error_boost = 0.0
            if has_errors:
                detected_errors = query_entities.get("Error", [])
                for error in detected_errors:
                    error_lower = error.lower()
                    # Check if answer addresses this specific error
                    if error_lower in answer_lower or error_lower in question_lower:
                        error_boost += 0.25

            # BOOST 3: Keyword overlap with query (for better matching)
            keyword_boost = 0.0
            query_keywords = set(query_lower.split())
            answer_keywords = set(answer_lower.split())
            overlap = len(query_keywords & answer_keywords)
            keyword_boost = min(overlap * 0.02, 0.2)  # Cap at 0.2

            # Calculate final score (EXACT MATCH gets highest priority)
            # RE-ENABLED intent_boost for FEE, LIMIT, TIME intents
            final_score = base_score + exact_match_boost + topic_boost + intent_boost + error_boost + keyword_boost

            # Update result
            result["relevance_score"] = final_score
            result["score_breakdown"] = {
                "base": base_score,
                "exact_match_boost": exact_match_boost,
                "topic_boost": topic_boost,
                "intent_boost": intent_boost,
                "error_boost": error_boost,
                "keyword_boost": keyword_boost,
                "final": final_score
            }

        # Sort by final relevance score
        context.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Format response
        if not context:
            return {
                "status": "no_results",
                "message": "Xin lỗi, tôi không tìm thấy thông tin phù hợp với câu hỏi của bạn.",
                "results": []
            }

        # Get top result
        top_result = context[0]

        # Log top 3 results for monitoring
        logger.info(f"\n{'='*60}")
        logger.info(f"TOP 3 RESULTS:")
        for i, result in enumerate(context[:3], 1):
            logger.info(f"{i}. FAQ: {result['question'][:60]}...")
            logger.info(f"   Score: {result['relevance_score']:.3f}")
            if "score_breakdown" in result:
                breakdown = result["score_breakdown"]
                logger.info(f"   Breakdown - Base: {breakdown.get('base', 0):.3f}, "
                          f"Exact: {breakdown.get('exact_match_boost', 0):.3f}, "
                          f"Topic: {breakdown.get('topic_boost', 0):.3f}, "
                          f"Intent: {breakdown.get('intent_boost', 0):.3f}")
        logger.info(f"{'='*60}\n")

        # Build response (answer already formatted with Case if available)
        case_info = {}
        if top_result.get("selected_case"):
            case_info = {
                "case_name": top_result.get("selected_case"),
                "step_count": len(top_result.get("case_steps", []))
            }
            logger.info(f"Using Case-based answer: {case_info['case_name']}")

        # ENHANCED: Use 3-Layer Focused Answer Extraction
        # Priority: Entity Direct → Case-Based → LLM → FAQ
        final_answer = top_result["answer"]
        extraction_info = None

        # Check if we should use focused extraction
        use_focused_extraction = getattr(config, 'USE_FOCUSED_EXTRACTION', True)

        # ============================================================
        # CRITICAL FIX: SKIP FOCUSED EXTRACTION FOR HIGH EXACT MATCHES
        # ============================================================
        # If the FAQ question is an exact or near-exact match (>90% similarity),
        # the original answer is already correct - DON'T modify it!
        # This prevents LLM from "summarizing" and changing format/content
        is_exact_match = top_result.get("exact_match_score", 0) >= 0.90
        if is_exact_match:
            logger.info(f"🎯 EXACT MATCH DETECTED ({top_result.get('exact_match_score', 0):.0%}) - SKIPPING focused extraction to preserve original answer")
            use_focused_extraction = False

        # CRITICAL: For specific intents (FEE, LIMIT, TIME), extract ONLY if not exact match
        specific_intents = ["FEE", "LIMIT", "TIME"]
        general_intents = ["TROUBLESHOOT", "HOW_TO", "COMPARISON"]

        should_extract = False
        if use_focused_extraction:
            if intent in specific_intents:
                # Extract for specific intents (user wants specific info) - but only if NOT exact match
                should_extract = True
                logger.info(f"Specific intent ({intent}) - will use focused extraction")
            elif intent in general_intents and len(final_answer) > 300:
                # Extract for general intents only if answer is long AND not exact match
                should_extract = True
                logger.info(f"Long answer ({len(final_answer)} chars) for {intent} - will use focused extraction")

        if should_extract:
            logger.info(f"🎯 Using FOCUSED EXTRACTION for intent: {intent}")
            try:
                # Merge query entities with graph entities for comprehensive context
                merged_entities = {**query_entities} if query_entities else {}
                graph_entities = top_result.get("related_entities", {})
                if graph_entities:
                    # Add graph entities (fees, limits, timeframes, etc.)
                    for key, value in graph_entities.items():
                        if value:  # Only add non-empty
                            merged_entities[key] = value

                # Use 3-Layer Focused Extractor (Entity → Case → LLM)
                focused_result = self.focused_extractor.extract_focused_answer(
                    user_query=query,
                    faq_answer=final_answer,
                    faq_question=top_result["question"],
                    intent=intent,
                    entities=merged_entities,
                    graph_entities=graph_entities
                )

                # Check if extraction improved the answer
                if focused_result.confidence >= 0.6:
                    # Only use extracted answer if it's substantially shorter
                    reduction_ratio = focused_result.answer_length / focused_result.original_length

                    # TROUBLESHOOT và HOW_TO không cần giảm kích thước - giữ đầy đủ thông tin
                    full_info_intents = {"TROUBLESHOOT", "HOW_TO"}
                    is_full_info_extraction = (
                        focused_result.source.value == "llm_extracted" and
                        "llm_extraction_full" in str(focused_result.extracted_info.get("method", ""))
                    )

                    if (reduction_ratio < 0.8 or
                        focused_result.source.value in ["entity_direct", "case_matched"] or
                        intent in full_info_intents or
                        is_full_info_extraction):
                        final_answer = focused_result.answer
                        extraction_info = {
                            "extraction_type": focused_result.source.value,
                            "confidence": focused_result.confidence,
                            "filter_applied": focused_result.filter_applied,
                            "reduction": f"{(1-reduction_ratio)*100:.0f}%"
                        }
                        logger.info(f"✅ Focused extraction successful: {focused_result.source.value}")
                        logger.info(f"   Original: {focused_result.original_length} chars → Focused: {focused_result.answer_length} chars ({extraction_info['reduction']} reduction)")
                    else:
                        logger.info(f"Focused extraction didn't reduce answer enough ({reduction_ratio:.0%}), using original")
                else:
                    logger.info(f"Focused extraction low confidence: {focused_result.confidence:.2%}")

            except Exception as e:
                logger.error(f"Focused extraction failed: {e}, using original answer")

        # CRITICAL: Check if FAQ actually answers the SPECIFIC question
        # If user asks about specific entity (e.g., "Vietcombank") but FAQ doesn't mention it,
        # return "không biết" instead of generic answer
        specific_entity_check = self._check_specific_entity_relevance(
            query=query,
            query_entities=query_entities,
            faq_question=top_result["question"],
            faq_answer=final_answer,
            intent=intent
        )

        if not specific_entity_check["is_relevant"]:
            logger.warning(f"❌ FAQ doesn't answer specific question: {specific_entity_check['reason']}")
            return {
                "status": "no_specific_answer",
                "question": top_result["question"],
                "answer": specific_entity_check["fallback_message"],
                "confidence": 0.3,  # Low confidence to indicate uncertainty
                "intent": intent,
                "faq_id": top_result.get("node_id"),  # Include FAQ ID for context tracking
                "missing_entity": specific_entity_check.get("missing_entity"),
                "related_entities": top_result["related_entities"],
                "alternative_actions": top_result["alternative_actions"],
                "related_questions": top_result["related_questions"][:3],
                "all_results": context[:config.TOP_K_RETRIEVAL],
            }

        response = {
            "status": "success",
            "question": top_result["question"],
            "answer": final_answer,
            "original_answer": top_result["answer"] if extraction_info else None,  # Keep original for reference
            "confidence": top_result["relevance_score"],
            "intent": intent,
            "faq_id": top_result.get("node_id"),  # CRITICAL: Include FAQ ID for Mem0 follow-up tracking
            "related_entities": top_result["related_entities"],
            "alternative_actions": top_result["alternative_actions"],
            "related_questions": top_result["related_questions"][:3],
            "all_results": context[:config.TOP_K_RETRIEVAL],
            # NEW: Add case info and extraction info
            "case_info": case_info if case_info else None,
            "extraction_info": extraction_info
        }

        return response

    def _check_specific_entity_relevance(
        self,
        query: str,
        query_entities: Dict,
        faq_question: str,
        faq_answer: str,
        intent: str
    ) -> Dict:
        """
        Check if the FAQ actually answers the SPECIFIC question asked.

        CRITICAL: If user asks about a specific entity (e.g., "Vietcombank", "VPBank")
        but the FAQ doesn't mention that entity, return "không biết" instead of generic answer.

        This prevents the chatbot from answering with unrelated information when
        the specific data doesn't exist in the database.

        Args:
            query: User's question
            query_entities: Entities extracted from query
            faq_question: The matched FAQ question
            faq_answer: The FAQ answer (or extracted answer)
            intent: Query intent

        Returns:
            {
                "is_relevant": True/False,
                "reason": str,  # Why it's not relevant
                "missing_entity": str,  # The specific entity that's missing
                "fallback_message": str  # Message to show user
            }
        """
        query_lower = query.lower()
        faq_question_lower = faq_question.lower()
        faq_answer_lower = faq_answer.lower()
        combined_faq = faq_question_lower + " " + faq_answer_lower

        # =====================================================
        # CHECK 1: Specific Bank Names
        # =====================================================
        # List of specific bank names that user might ask about
        specific_banks = [
            "vietcombank", "vcb", "vietinbank", "viettinbank", "ctg",
            "techcombank", "tcb", "bidv", "agribank", "vpbank", "vp bank",
            "mbbank", "mb bank", "acb", "sacombank", "shb", "seabank",
            "tpbank", "tp bank", "oceanbank", "lienvietpostbank", "lpb",
            "vib", "hdbank", "hd bank", "eximbank", "msb", "maritime",
            "pvcombank", "baovietbank", "namabank", "ncb", "abbank",
            "bac a bank", "baca bank", "kienlongbank", "dongabank",
            "scb", "gpbank", "vietabank", "vietbank", "publicbank"
        ]

        # Check if query mentions a specific bank
        query_banks = query_entities.get("Bank", [])
        mentioned_bank = None

        # Also check via text matching for banks not extracted by entity extractor
        for bank in specific_banks:
            if bank in query_lower:
                mentioned_bank = bank
                break

        # If entity extractor found banks, use those
        if query_banks:
            for bank in query_banks:
                bank_lower = bank.lower()
                # Check if this specific bank is mentioned in FAQ
                if bank_lower not in combined_faq:
                    # Check common aliases
                    aliases = {
                        "vietcombank": ["vcb", "vietcombank"],
                        "vcb": ["vcb", "vietcombank"],
                        "vietinbank": ["viettinbank", "vietinbank", "ctg"],
                        "techcombank": ["techcombank", "tcb"],
                        "vpbank": ["vpbank", "vp bank", "vp"],
                        "mbbank": ["mbbank", "mb bank", "mb"],
                    }
                    bank_aliases = aliases.get(bank_lower, [bank_lower])
                    bank_found = any(alias in combined_faq for alias in bank_aliases)

                    if not bank_found:
                        logger.info(f"⚠️ Specific bank '{bank}' NOT found in FAQ")
                        return {
                            "is_relevant": False,
                            "reason": f"FAQ doesn't mention specific bank: {bank}",
                            "missing_entity": bank,
                            "fallback_message": f"Xin lỗi, tôi không có thông tin cụ thể về {bank}. "
                                              f"Bạn có thể liên hệ Hotline 1900 8198 hoặc truy cập "
                                              f"https://vnptpay.vn/web/trogiup/bieuphi_mm để xem biểu phí chi tiết."
                        }

        # Also check mentioned_bank from text matching
        if mentioned_bank and mentioned_bank not in combined_faq:
            # Check aliases
            aliases = {
                "vietcombank": ["vcb", "vietcombank"],
                "vcb": ["vcb", "vietcombank"],
                "vietinbank": ["viettinbank", "vietinbank", "ctg"],
                "techcombank": ["techcombank", "tcb"],
                "vpbank": ["vpbank", "vp bank", "vp"],
                "mbbank": ["mbbank", "mb bank", "mb"],
            }
            bank_aliases = aliases.get(mentioned_bank, [mentioned_bank])
            bank_found = any(alias in combined_faq for alias in bank_aliases)

            if not bank_found:
                logger.info(f"⚠️ Specific bank '{mentioned_bank}' NOT found in FAQ")
                return {
                    "is_relevant": False,
                    "reason": f"FAQ doesn't mention specific bank: {mentioned_bank}",
                    "missing_entity": mentioned_bank,
                    "fallback_message": f"Xin lỗi, tôi không có thông tin cụ thể về {mentioned_bank}. "
                                      f"Bạn có thể liên hệ Hotline 1900 8198 hoặc truy cập "
                                      f"https://vnptpay.vn/web/trogiup/bieuphi_mm để xem biểu phí chi tiết."
                }

        # =====================================================
        # CHECK 2: Specific Amount/Number Questions
        # =====================================================
        # If user asks for specific amount (e.g., "1 triệu", "500k") but FAQ is generic
        import re
        amount_patterns = [
            r'(\d+)\s*(triệu|tr|nghìn|ngàn|k|đồng|vnd)',  # "1 triệu", "500k"
            r'(bao nhiêu|mức|số tiền)\s+(\d+)',  # "bao nhiêu 1000000"
        ]

        has_specific_amount = False
        for pattern in amount_patterns:
            if re.search(pattern, query_lower):
                has_specific_amount = True
                break

        # For FEE/LIMIT intents, if user asks with specific amount but FAQ gives general link
        if intent in ["FEE", "LIMIT"] and has_specific_amount:
            # Check if FAQ actually contains specific numbers/amounts
            has_faq_amounts = bool(re.search(r'\d+[.,]?\d*\s*(đồng|vnd|%|triệu|nghìn)', faq_answer_lower))
            if not has_faq_amounts and "biểu phí" in faq_answer_lower:
                # FAQ just redirects to fee page, doesn't have specific info
                logger.info(f"⚠️ User asked for specific amount but FAQ only provides general link")
                # Allow this case - it's acceptable to provide a link
                pass

        # =====================================================
        # CHECK 3: Very low similarity between query and FAQ question
        # =====================================================
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, query_lower, faq_question_lower).ratio()

        # If similarity is extremely low AND FAQ doesn't contain key query terms
        if similarity < 0.25:
            # Extract key terms from query (excluding stopwords)
            stopwords = {'tôi', 'bạn', 'là', 'có', 'thể', 'được', 'để', 'và', 'hoặc', 'hay',
                        'này', 'đó', 'như', 'thế', 'nào', 'gì', 'sao', 'làm', 'muốn', 'cần',
                        'của', 'cho', 'với', 'từ', 'đến', 'trong', 'bao', 'nhiêu', 'ở', 'đâu'}
            query_terms = [w for w in query_lower.split() if w not in stopwords and len(w) > 2]

            # Check how many query terms appear in FAQ
            terms_found = sum(1 for term in query_terms if term in combined_faq)
            term_coverage = terms_found / len(query_terms) if query_terms else 1.0

            if term_coverage < 0.3:
                logger.info(f"⚠️ Very low relevance: similarity={similarity:.2%}, term_coverage={term_coverage:.2%}")
                return {
                    "is_relevant": False,
                    "reason": f"FAQ has very low relevance to query (similarity: {similarity:.0%})",
                    "missing_entity": None,
                    "fallback_message": "Xin lỗi, tôi không tìm thấy thông tin chính xác cho câu hỏi của bạn. "
                                      "Bạn có thể liên hệ Hotline 1900 8198 để được hỗ trợ trực tiếp."
                }

        # All checks passed - FAQ is relevant
        return {
            "is_relevant": True,
            "reason": "FAQ is relevant to query"
        }

    def _query_steps_by_faq_id(
        self,
        faq_id: str,
        from_step: int = 1,
        only_next_step: bool = True,
        topic: Optional[str] = None
    ):
        """
        Query Step nodes from Neo4j graph using FAQ ID (MOST ACCURATE)

        Args:
            faq_id: The FAQ question_id from previous context
            from_step: Get steps from this number onwards
            only_next_step: If True, only return the immediate next step (default: True)
                           If False, return all remaining steps

        Returns:
            {
                "faq_question": str,
                "process_name": str,
                "process_id": str,
                "steps": [{"number": 1, "text": "..."}, ...],
                "total_steps": int
            } or None
        """
        try:
            # Build WHERE clause based on only_next_step
            if only_next_step:
                where_clause = "WHERE s.number = $from_step"
                logger.info(f"   Query mode: SINGLE STEP (step {from_step})")
            else:
                where_clause = "WHERE s.number >= $from_step"
                logger.info(f"   Query mode: ALL REMAINING STEPS (from step {from_step})")

            # CRITICAL: Query BOTH the requested steps AND the total count
            # CRITICAL FIX: Use faq_id (not question_id) to match Neo4j schema
            cypher = f"""
            MATCH (faq:FAQ {{id: $faq_id}})-[:DESCRIBES_PROCESS]->(p:Process)
            MATCH (p)-[:HAS_STEP]->(all_s:Step)
            WITH faq, p, count(all_s) as total_count
            MATCH (p)-[:HAS_STEP]->(s:Step)
            {where_clause}
            RETURN faq.question as faq_question,
                   faq.answer as faq_answer,
                   p.name as process_name,
                   p.id as process_id,
                   s.number as step_num,
                   s.text as step_text,
                   total_count as total_steps_in_process
            ORDER BY s.number
            """
            params = {"faq_id": faq_id, "from_step": from_step}

            results = self.connector.execute_query(cypher, params)

            if not results:
                logger.warning(f"No steps found for FAQ ID: {faq_id}")

                # FALLBACK 1: Try to get total count for this FAQ_ID
                # CRITICAL FIX: Use faq_id (not question_id) to match Neo4j schema
                count_cypher = """
                MATCH (faq:FAQ {id: $faq_id})-[:DESCRIBES_PROCESS]->(p:Process)
                MATCH (p)-[:HAS_STEP]->(s:Step)
                RETURN count(s) as total_count
                """
                count_result = self.connector.execute_query(count_cypher, {"faq_id": faq_id})
                if count_result and count_result[0]['total_count'] > 0:
                    # Process exists but requested step doesn't exist (beyond last step)
                    logger.info(f"✅ Process has {count_result[0]['total_count']} steps total, step {from_step} not found (user completed all)")
                    return {
                        "steps": [],
                        "total_steps": 0,  # No more steps to show
                        "total_steps_in_process": count_result[0]['total_count']  # But process has this many total
                    }

                # FALLBACK 2: FAQ_ID not in graph (question_id is None)
                # Try to infer process from FAQ_ID pattern or topic
                logger.warning(f"FAQ_ID '{faq_id}' not found in graph, trying pattern-based fallback")
                return self._query_steps_by_faq_id_fallback(faq_id, from_step, only_next_step, topic)

            # Build result
            first_row = results[0]
            total_steps_in_process = first_row['total_steps_in_process']

            result = {
                "faq_question": first_row['faq_question'],
                "faq_answer": first_row['faq_answer'],
                "process_name": first_row['process_name'],
                "process_id": first_row['process_id'],
                "steps": [],
                "direction_score": 10,  # Perfect match since we're using exact FAQ ID
                "total_steps_in_process": total_steps_in_process  # CRITICAL: Total steps in the whole process
            }

            for row in results:
                result["steps"].append({
                    "number": row['step_num'],
                    "text": row['step_text']
                })

            result["total_steps"] = len(result["steps"])  # Number of steps returned in this query

            logger.info(f"📊 Query by FAQ ID SUCCESS: Found {result['total_steps']} steps")
            logger.info(f"   FAQ: {result['faq_question'][:60]}...")

            return result

        except Exception as e:
            logger.error(f"Failed to query steps by FAQ ID: {e}")
            return None

    def _query_steps_by_faq_id_fallback(
        self,
        faq_id: str,
        from_step: int = 1,
        only_next_step: bool = True,
        topic: Optional[str] = None
    ):
        """
        Fallback method when FAQ_ID is not found in graph (question_id is None).
        Infer process type and keywords from FAQ_ID pattern OR topic.

        Args:
            faq_id: The FAQ ID (e.g., "FAQ_RUT_TIEN", "FAQ_129")
            from_step: Get steps from this number onwards
            only_next_step: If True, only return the immediate next step
            topic: Topic from context (e.g., "rút tiền", "nạp tiền")

        Returns:
            Same format as _query_steps_by_faq_id or None
        """
        try:
            # Map topics/keywords to process name with MORE SPECIFIC keywords
            # Format: topic -> (process_name, [required_keywords], [optional_keywords])
            topic_to_process = {
                # More specific patterns first (will be checked in order)
                "hủy nạp tiền": ("cancel_deposit", ["hủy", "nạp tiền"], ["tự động", "dịch vụ"]),
                "hủy dịch vụ": ("cancel_deposit", ["hủy", "dịch vụ"], ["nạp tiền", "tự động"]),
                "mua vé máy bay": ("buy_ticket_flight", ["mua vé", "máy bay"], []),
                "mua vé tàu": ("buy_ticket_train", ["mua vé", "tàu"], []),
                "mua vé vui chơi": ("buy_ticket_entertainment", ["mua vé", "vui chơi"], []),
                "nạp tiền điện thoại": ("recharge_phone", ["nạp tiền", "điện thoại"], []),
                "nạp tiền từ ngân hàng": ("deposit_bank", ["nạp tiền", "ngân hàng"], []),
                "rút tiền về ngân hàng": ("withdrawal", ["rút tiền", "ngân hàng"], ["ví", "vnpt pay", "mobile money"]),
                "chuyển tiền đến ngân hàng": ("transfer", ["chuyển tiền", "ngân hàng"], []),
                "thanh toán hóa đơn": ("payment_bill", ["thanh toán", "hóa đơn"], ["viễn thông"]),

                # Generic patterns last (fallback)
                "rút tiền": ("withdrawal", ["rút tiền"], ["ví", "ngân hàng"]),
                "withdrawal": ("withdrawal", ["rút tiền"], ["ví", "ngân hàng"]),
                "nạp tiền": ("deposit", ["nạp tiền"], ["ngân hàng"]),
                "deposit": ("deposit", ["nạp tiền"], ["ngân hàng"]),
                "chuyển tiền": ("transfer", ["chuyển tiền"], ["ngân hàng"]),
                "transfer": ("transfer", ["chuyển tiền"], ["ngân hàng"]),
                "thanh toán": ("payment", ["thanh toán"], []),
                "payment": ("payment", ["thanh toán"], []),
                "mua vé": ("buy_ticket", ["mua vé"], []),
                "buy_ticket": ("buy_ticket", ["mua vé"], []),
            }

            # Extract process info from FAQ_ID pattern (old method)
            faq_patterns = {
                "FAQ_RUT_TIEN": ("withdrawal", ["rút tiền", "ví", "ngân hàng"]),
                "FAQ_NAP_TIEN": ("deposit", ["nạp tiền", "ngân hàng"]),
                "FAQ_CHUYEN_TIEN": ("transfer", ["chuyển tiền", "ngân hàng"]),
                "FAQ_THANH_TOAN": ("payment", ["thanh toán"]),
                "FAQ_MUA_VE": ("buy_ticket", ["mua vé"]),
            }

            process_name = None
            required_keywords = []
            optional_keywords = []

            # Try to infer from FAQ_ID pattern first
            for pattern, (proc_name, kws) in faq_patterns.items():
                if pattern in faq_id.upper():
                    process_name = proc_name
                    required_keywords = kws
                    optional_keywords = []
                    logger.info(f"🔍 Fallback: Inferred '{process_name}' from FAQ_ID pattern '{faq_id}'")
                    break

            # If not found, try to infer from topic (with new 3-tuple format)
            if not process_name and topic:
                topic_lower = topic.lower().strip()
                # Check in order (specific patterns first)
                for topic_key, pattern_info in topic_to_process.items():
                    if len(pattern_info) == 3:
                        proc_name, req_kws, opt_kws = pattern_info
                    else:
                        # Old format compatibility
                        proc_name, req_kws = pattern_info
                        opt_kws = []

                    if topic_key in topic_lower or topic_lower in topic_key:
                        process_name = proc_name
                        required_keywords = req_kws
                        optional_keywords = opt_kws
                        logger.info(f"🔍 Fallback: Inferred '{process_name}' from topic '{topic}'")
                        logger.info(f"   Required keywords: {required_keywords}")
                        if optional_keywords:
                            logger.info(f"   Optional keywords: {optional_keywords}")
                        break

            if not process_name:
                logger.warning(f"Cannot infer process from FAQ_ID '{faq_id}' or topic '{topic}'")
                return None

            logger.info(f"🔍 Fallback: Inferred process '{process_name}' from FAQ_ID '{faq_id}'")

            # Build WHERE clause with REQUIRED keywords (ALL must match)
            # and OPTIONAL keywords (at least one should match for better ranking)
            required_conditions = " AND ".join([f"toLower(faq.question) CONTAINS '{kw}'" for kw in required_keywords])

            # For optional keywords, we'll use them in ORDER BY for ranking
            # FAQs with more optional keywords will be ranked higher

            # Build WHERE clause for steps
            if only_next_step:
                step_where = "WHERE s.number = $from_step"
            else:
                step_where = "WHERE s.number >= $from_step"

            # Build optional keyword scoring for ranking
            # FAQs matching more optional keywords rank higher
            if optional_keywords:
                optional_score_expr = " + ".join([
                    f"CASE WHEN toLower(faq.question) CONTAINS '{kw}' THEN 1 ELSE 0 END"
                    for kw in optional_keywords
                ])
                order_by = f"ORDER BY ({optional_score_expr}) DESC, total_count DESC"
            else:
                # If no optional keywords, just prioritize more steps
                order_by = "ORDER BY total_count DESC"

            # Query by process name + REQUIRED keywords
            # IMPORTANT: Prioritize FAQs with more optional keywords, then more steps
            cypher = f"""
            MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {{name: $process_name}})
            WHERE {required_conditions}
            MATCH (p)-[:HAS_STEP]->(all_s:Step)
            WITH faq, p, count(all_s) as total_count
            {order_by}
            LIMIT 1
            MATCH (p)-[:HAS_STEP]->(s:Step)
            {step_where}
            RETURN faq.question as faq_question,
                   faq.answer as faq_answer,
                   p.name as process_name,
                   p.id as process_id,
                   s.number as step_num,
                   s.text as step_text,
                   total_count as total_steps_in_process
            ORDER BY s.number
            """

            params = {
                "process_name": process_name,
                "from_step": from_step
            }

            results = self.connector.execute_query(cypher, params)

            if not results:
                logger.warning(f"Fallback query found no results for process '{process_name}'")

                # Try to get total count even if step not found
                # IMPORTANT: Prioritize FAQs with more optional keywords, then more steps
                count_cypher = f"""
                MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {{name: $process_name}})
                WHERE {required_conditions}
                MATCH (p)-[:HAS_STEP]->(s:Step)
                WITH p, count(s) as step_count
                {order_by.replace("total_count", "step_count")}
                LIMIT 1
                RETURN step_count as total_count
                """

                count_result = self.connector.execute_query(count_cypher, {"process_name": process_name})
                if count_result and count_result[0]['total_count'] > 0:
                    logger.info(f"✅ Fallback: Process has {count_result[0]['total_count']} steps total, step {from_step} not found")
                    return {
                        "steps": [],
                        "total_steps": 0,
                        "total_steps_in_process": count_result[0]['total_count']
                    }
                return None

            # Build result
            first_row = results[0]
            total_steps_in_process = first_row['total_steps_in_process']

            result = {
                "faq_question": first_row['faq_question'],
                "faq_answer": first_row['faq_answer'],
                "process_name": first_row['process_name'],
                "process_id": first_row['process_id'],
                "steps": [],
                "direction_score": 8,  # Lower than exact FAQ_ID match
                "total_steps_in_process": total_steps_in_process
            }

            for row in results:
                result["steps"].append({
                    "number": row['step_num'],
                    "text": row['step_text']
                })

            result["total_steps"] = len(result["steps"])

            logger.info(f"✅ Fallback query SUCCESS: Found {result['total_steps']} steps")
            logger.info(f"   Total steps in process: {total_steps_in_process}")
            logger.info(f"   FAQ: {result['faq_question'][:60]}...")

            return result

        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return None

    def _query_steps_from_graph(
        self,
        base_query: str,
        from_step: int = 1,
        only_next_step: bool = True
    ):
        """
        Query Step nodes from Neo4j graph (GRAPH-BASED, not regex)

        Args:
            base_query: Base query without "sau khi..." part
            from_step: Get steps from this number onwards (e.g., 2 means steps 2,3,4,5...)
            only_next_step: If True, only return the immediate next step (default: True)
                           If False, return all remaining steps

        Returns:
            {
                "faq_question": str,
                "process_name": str,
                "process_id": str,
                "steps": [{"number": 1, "text": "..."}, ...],
                "total_steps": int
            } or None
        """
        try:
            query_lower = base_query.lower()

            # Extract action phrases for better matching (2-word phrases like "rút tiền")
            import re
            action_patterns = [
                r'(rút\s+tiền)',
                r'(nạp\s+tiền)',
                r'(chuyển\s+tiền)',
                r'(mua\s+vé)',
                r'(thanh\s+toán)',
                r'(liên\s+kết)',
            ]

            main_phrase = None
            for pattern in action_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    main_phrase = match.group(1)
                    break

            if main_phrase:
                # Use EXACT phrase matching for better accuracy
                keyword_conditions = f"toLower(faq.question) CONTAINS '{main_phrase}'"
                logger.info(f"   Using phrase match: '{main_phrase}'")
            else:
                # Fallback: use individual keywords
                keywords = [w for w in query_lower.split() if len(w) > 2][:5]
                if not keywords:
                    logger.warning("No valid keywords in base query")
                    return None
                keyword_conditions = " OR ".join([f"toLower(faq.question) CONTAINS '{kw}'" for kw in keywords])
                logger.info(f"   Using keyword match: {keywords}")

            # Detect direction from query
            from_wallet = any(x in query_lower for x in ['từ ví', 'từ vnpt', 'từ mobile money', 'từ tài khoản'])
            to_bank = any(x in query_lower for x in ['đến ngân hàng', 'sang ngân hàng', 'về ngân hàng', 'đến bank', 'sang bank'])
            from_bank = any(x in query_lower for x in ['từ ngân hàng', 'từ bank'])
            to_wallet = any(x in query_lower for x in ['vào ví', 'vào vnpt', 'vào mobile money', 'vào tài khoản'])

            logger.info(f"   Direction detection: from_wallet={from_wallet}, to_bank={to_bank}, from_bank={from_bank}, to_wallet={to_wallet}")

            # Build step filter based on only_next_step
            if only_next_step:
                step_filter = "WHERE s.number = $from_step"
                logger.info(f"   Query mode: SINGLE STEP (step {from_step})")
            else:
                step_filter = "WHERE s.number >= $from_step"
                logger.info(f"   Query mode: ALL REMAINING STEPS (from step {from_step})")

            cypher = f"""
            MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
            WHERE {keyword_conditions}
            MATCH (p)-[:HAS_STEP]->(s:Step)
            {step_filter}
            RETURN faq.question as faq_question,
                   faq.answer as faq_answer,
                   p.name as process_name,
                   p.id as process_id,
                   s.number as step_num,
                   s.text as step_text,
                   toLower(faq.question) as faq_lower
            ORDER BY p.id, s.number
            LIMIT 50
            """
            params = {"from_step": from_step}

            results = self.connector.execute_query(cypher, params)

            if not results:
                logger.warning(f"No steps found in graph")
                return None

            # Group by process with direction matching
            processes = {}
            for row in results:
                process_id = row['process_id']
                faq_lower = row['faq_lower']

                # Calculate direction match score
                direction_score = 0
                faq_from_wallet = any(x in faq_lower for x in ['từ ví', 'từ vnpt', 'từ mobile money', 'từ tài khoản mobile'])
                faq_to_bank = any(x in faq_lower for x in ['đến ngân hàng', 'sang ngân hàng', 'về ngân hàng', 'đến bank', 'sang bank'])
                faq_from_bank = any(x in faq_lower for x in ['từ ngân hàng', 'từ bank'])
                faq_to_wallet = any(x in faq_lower for x in ['vào ví', 'vào vnpt', 'vào mobile money', 'vào tài khoản'])

                # Perfect match: same direction as query
                if from_wallet and to_bank and faq_from_wallet and faq_to_bank:
                    direction_score = 10  # PERFECT: ví → bank
                elif from_bank and to_wallet and faq_from_bank and faq_to_wallet:
                    direction_score = 10  # PERFECT: bank → ví
                # Wrong direction: opposite of query
                elif from_wallet and to_bank and faq_from_bank and faq_to_wallet:
                    direction_score = -10  # WRONG: query wants ví→bank but FAQ is bank→ví
                elif from_bank and to_wallet and faq_from_wallet and faq_to_bank:
                    direction_score = -10  # WRONG: query wants bank→ví but FAQ is ví→bank
                # Partial match
                elif (from_wallet and faq_from_wallet) or (to_bank and faq_to_bank):
                    direction_score = 5  # OK: some direction match

                if process_id not in processes:
                    processes[process_id] = {
                        "faq_question": row['faq_question'],
                        "faq_answer": row['faq_answer'],
                        "process_name": row['process_name'],
                        "process_id": process_id,
                        "steps": [],
                        "direction_score": direction_score
                    }

                processes[process_id]["steps"].append({
                    "number": row['step_num'],
                    "text": row['step_text']
                })

            # Sort processes by direction score (highest first)
            sorted_processes = sorted(processes.values(), key=lambda x: x["direction_score"], reverse=True)

            # Return best matching process
            best_process = sorted_processes[0]
            best_process["total_steps"] = len(best_process["steps"])

            logger.info(f"📊 Graph query SUCCESS: Found {best_process['total_steps']} steps")
            logger.info(f"   FAQ: {best_process['faq_question'][:60]}...")
            logger.info(f"   Direction score: {best_process['direction_score']}")

            return best_process

        except Exception as e:
            logger.error(f"Failed to query steps from graph: {e}")
            return None

    def _handle_follow_up_query(
        self,
        user_query: str,
        follow_up_context: Dict,
        query_entities: Dict,
        intent: str,
        intent_confidence: float,
        top_k: int = 5
    ) -> Dict:
        """
        Handle follow-up queries using Mem0 context

        This method prioritizes searching within the previous FAQ's context
        to find the specific case/information the user is asking about.

        Args:
            user_query: User's current query
            follow_up_context: Context from Mem0 including:
                - topic: Previous conversation topic
                - faq_id: Previous FAQ ID to search within
                - context_needed: What user is asking about
                - memories: Relevant memories from Mem0
            query_entities: Extracted entities from current query
            intent: Classified intent
            intent_confidence: Intent classification confidence
            top_k: Number of results to return

        Returns:
            Query result with contextual answer
        """
        topic = follow_up_context.get("topic", "")
        faq_id = follow_up_context.get("faq_id")
        context_needed = follow_up_context.get("context_needed", "")
        memories = follow_up_context.get("memories", [])

        logger.info(f"🔗 Follow-up handling: topic='{topic}', faq_id='{faq_id}'")
        logger.info(f"   Context needed: {context_needed}")

        # Strategy 1: If we have FAQ ID, search within that FAQ's cases
        if faq_id:
            logger.info(f"📍 Searching within FAQ {faq_id} for follow-up context")
            faq_result = self._search_within_faq(
                faq_id=faq_id,
                search_terms=[user_query, context_needed],
                intent=intent,
                query_entities=query_entities
            )

            if faq_result and faq_result.get("status") == "success":
                logger.info(f"✅ Found answer within FAQ {faq_id}")
                faq_result["is_follow_up"] = True
                faq_result["follow_up_topic"] = topic
                faq_result["follow_up_faq_id"] = faq_id
                return faq_result

        # Strategy 2: Search with topic context if FAQ search failed
        if topic:
            logger.info(f"📍 Searching with topic context: '{topic}'")

            # Augment entities with topic
            enhanced_entities = query_entities.copy()
            if "Topic" not in enhanced_entities or not enhanced_entities["Topic"]:
                enhanced_entities["Topic"] = [topic]
            elif topic not in enhanced_entities.get("Topic", []):
                enhanced_entities["Topic"].append(topic)

            # Search with enhanced entities
            relevant_nodes = self._find_relevant_nodes(
                query=user_query,
                query_entities=enhanced_entities,
                top_k=top_k * 2,
                intent=intent
            )

            if relevant_nodes:
                # Get context and rank
                context = self._get_graph_context(relevant_nodes, enhanced_entities, user_query, intent)
                results = self._rank_results(context, user_query, intent, enhanced_entities)

                if results.get("status") == "success":
                    results["is_follow_up"] = True
                    results["follow_up_topic"] = topic

                    # Add steps if present
                    if results.get("answer"):
                        steps = self.step_extractor.extract_from_answer(results["answer"])
                        results["steps"] = steps
                        results["has_steps"] = len(steps) > 0

                    return results

        # Strategy 3: Fall back to normal query (no context found)
        logger.warning("⚠️ Follow-up context search failed, falling back to normal query")

        # Normal search
        relevant_nodes = self._find_relevant_nodes(user_query, query_entities, top_k * 2, intent)

        if not relevant_nodes:
            return {
                "status": "no_results",
                "question": user_query,
                "answer": "Xin lỗi, tôi không tìm thấy thông tin phù hợp. Bạn có thể mô tả chi tiết hơn không?",
                "confidence": 0,
                "related_entities": {},
                "related_questions": [],
                "all_results": [],
                "is_follow_up": True,
                "follow_up_topic": topic
            }

        context = self._get_graph_context(relevant_nodes, query_entities, user_query, intent)
        results = self._rank_results(context, user_query, intent, query_entities)

        results["is_follow_up"] = True
        results["follow_up_topic"] = topic

        return results

    def _search_within_faq(
        self,
        faq_id: str,
        search_terms: List[str],
        intent: str,
        query_entities: Dict
    ) -> Optional[Dict]:
        """
        Search within a specific FAQ for relevant cases/information

        Args:
            faq_id: FAQ ID to search within
            search_terms: Terms to search for
            intent: User's intent
            query_entities: Extracted entities

        Returns:
            Search result or None
        """
        try:
            # Query the FAQ and its cases
            cypher = """
            MATCH (f:FAQ {id: $faq_id})
            OPTIONAL MATCH (f)-[:HAS_CASE]->(c:Case)
            OPTIONAL MATCH (c)-[:HAS_STEP]->(s:Step)
            RETURN f,
                   collect(DISTINCT {
                       case_id: c.id,
                       description: c.description,
                       condition: c.condition,
                       steps: collect(DISTINCT {step_num: s.step_number, content: s.content})
                   }) as cases
            """

            result = self.connector.query(cypher, {"faq_id": faq_id})

            if not result:
                return None

            record = result[0]
            faq_node = record["f"]
            cases = record["cases"]

            if not faq_node:
                return None

            faq_question = faq_node.get("question", "")
            faq_answer = faq_node.get("answer", "")

            logger.info(f"   Found FAQ with {len(cases)} cases")

            # Search for matching case based on search terms
            best_case = None
            best_score = 0
            search_lower = " ".join(search_terms).lower()

            # Extract key terms for matching
            status_terms = []
            if "đang xử lý" in search_lower or "dang xu ly" in search_lower:
                status_terms.append("đang xử lý")
                status_terms.append("chưa hoàn thành")
            if "thành công" in search_lower or "thanh cong" in search_lower:
                status_terms.append("thành công")
                status_terms.append("hoàn tất")
            if "thất bại" in search_lower or "that bai" in search_lower:
                status_terms.append("thất bại")
                status_terms.append("không thành công")

            # Also check for time-related follow-ups
            if "thời gian" in search_lower or "bao lâu" in search_lower:
                status_terms.append("ngày")
                status_terms.append("giờ")
                status_terms.append("thời gian")

            for case in cases:
                if not case.get("description"):
                    continue

                case_desc = case.get("description", "").lower()
                case_condition = (case.get("condition") or "").lower()

                score = 0

                # Check status term matches
                for term in status_terms:
                    if term in case_desc or term in case_condition:
                        score += 10
                        logger.info(f"   ✅ Case match on '{term}': {case_desc[:50]}...")

                # Check general search term overlap
                search_words = set(search_lower.split())
                case_words = set(case_desc.split())
                overlap = len(search_words & case_words)
                score += overlap * 2

                if score > best_score:
                    best_score = score
                    best_case = case

            if best_case and best_score > 5:
                logger.info(f"   ✅ Best matching case (score={best_score}): {best_case.get('description', '')[:50]}...")

                # Build answer from case
                case_answer = best_case.get("description", "")

                # Add steps if available
                steps = best_case.get("steps", [])
                if steps:
                    valid_steps = [s for s in steps if s.get("content")]
                    if valid_steps:
                        valid_steps.sort(key=lambda x: x.get("step_num", 0))
                        step_text = "\n".join([f"{s['step_num']}. {s['content']}" for s in valid_steps])
                        case_answer += f"\n\nCác bước thực hiện:\n{step_text}"

                return {
                    "status": "success",
                    "question": faq_question,
                    "answer": case_answer,
                    "confidence": min(best_score / 20, 1.0),
                    "faq_id": faq_id,
                    "case_id": best_case.get("case_id"),
                    "related_entities": query_entities,
                    "related_questions": [],
                    "all_results": [],
                    "intent": intent
                }

            # No matching case found, but we have the FAQ - use focused extraction
            if faq_answer and len(faq_answer) > 100:
                logger.info("   No specific case matched, using focused extraction on FAQ")

                # Use focused extractor to get relevant part
                if config.USE_FOCUSED_EXTRACTION:
                    focused_result = self.focused_extractor.extract(
                        faq_content=faq_answer,
                        user_query=" ".join(search_terms),
                        intent=intent,
                        entities=query_entities
                    )

                    if focused_result.get("success"):
                        return {
                            "status": "success",
                            "question": faq_question,
                            "answer": focused_result.get("answer", faq_answer),
                            "confidence": focused_result.get("confidence", 0.7),
                            "faq_id": faq_id,
                            "related_entities": query_entities,
                            "related_questions": [],
                            "all_results": [],
                            "intent": intent,
                            "extraction_method": focused_result.get("method")
                        }

            return None

        except Exception as e:
            logger.error(f"Error searching within FAQ {faq_id}: {e}")
            return None

    def _handle_step_continuation(
        self,
        user_query: str,
        continuation_context: Dict,
        query_entities: Dict
    ) -> Dict:
        """
        Handle step continuation queries using GRAPH NODES (minimal regex)

        Args:
            user_query: User's query
            continuation_context: Context from ConversationContextManager
            query_entities: Extracted entities

        Returns:
            Response with next steps
        """
        from step_tracker import StepTracker

        # Get context info
        completed_step = continuation_context.get("completed_step", 1)
        next_step = continuation_context.get("next_step", 2)
        all_steps = continuation_context.get("all_steps", [])
        previous_answer = continuation_context.get("previous_answer", "")
        topic = continuation_context.get("topic")
        last_faq_id = continuation_context.get("last_faq_id")  # CRITICAL: Get FAQ ID from context

        logger.info(f"   Continuation: completed_step={completed_step}, next_step={next_step}")
        if last_faq_id:
            logger.info(f"   Last FAQ ID from context: {last_faq_id}")

        # CRITICAL: Check if all steps are completed BEFORE querying graph
        # Check if continuation context indicates all steps completed
        if continuation_context.get("all_steps_completed", False):
            logger.info(f"✅ All action steps completed! (next step is a completion/result step)")
            return {
                "status": "success",
                "question": f"Hoàn thành tất cả các bước {topic if topic else 'thực hiện'}",
                "answer": f"""✅ Hiện tại tất cả các bước đã hoàn thành!

Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận.

Nếu giao dịch chưa thành công hoặc bạn cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn""",
                "confidence": 1.0,
                "related_entities": continuation_context.get("entities", {}),
                "alternative_actions": [],
                "related_questions": [],
                "all_results": [],
                "is_continuation": True,
                "is_completed": True,
                "completed_step": completed_step,
                "next_steps": [],
                "total_steps": completed_step
            }

        # Get total steps from cached context
        total_steps_in_process = 0
        if all_steps:
            total_steps_in_process = len(all_steps)

        # Check if user completed ALL steps (fallback for old behavior)
        if total_steps_in_process > 0 and completed_step >= total_steps_in_process:
            logger.info(f"✅ All steps completed! (completed_step={completed_step}, total={total_steps_in_process})")
            return {
                "status": "success",
                "question": f"Hoàn thành tất cả các bước {topic if topic else 'thực hiện'}",
                "answer": f"""✅ Bạn đã hoàn thành tất cả {total_steps_in_process} bước!

Nếu bạn vẫn gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn""",
                "confidence": 1.0,
                "related_entities": continuation_context.get("entities", {}),
                "alternative_actions": [],
                "related_questions": [],
                "all_results": [],
                "is_continuation": True,
                "is_completed": True,
                "completed_step": completed_step,
                "next_steps": [],
                "total_steps": total_steps_in_process
            }

        # CRITICAL FIX: ALWAYS try graph query first if FAQ ID is available
        # Graph data is more accurate than regex-extracted cached steps
        graph_result = None
        if last_faq_id:
            logger.info("🔍 PRIORITY: Querying Step nodes from graph using FAQ ID...")
            logger.info(f"   Using FAQ ID for accurate retrieval: {last_faq_id}")
            # Only get the NEXT step, not all remaining steps
            graph_result = self._query_steps_by_faq_id(last_faq_id, from_step=next_step, only_next_step=True, topic=topic)

            # PRIORITY 2: Fallback to keyword-based query if FAQ ID not available or failed
            if not graph_result:
                logger.info("   Falling back to keyword-based query...")
                # Extract base query (minimal regex - only to remove continuation phrase)
                import re
                base_query = re.sub(r'sau\s+khi\s+.*$', '', user_query, flags=re.IGNORECASE).strip()
                logger.info(f"   Base query: {base_query[:60]}...")

                # GRAPH QUERY: Get steps directly from Step nodes (only next step)
                graph_result = self._query_steps_from_graph(base_query, from_step=next_step, only_next_step=True)

            # CRITICAL: Check if we're beyond the last step
            # Use total_steps_in_process from graph (most accurate)
            if graph_result:
                total_from_graph = graph_result.get('total_steps_in_process', 0)
                if total_from_graph > 0:
                    logger.info(f"📊 Graph reports total steps in process: {total_from_graph}")
                    # Check if user completed all steps
                    if completed_step >= total_from_graph:
                        logger.info(f"✅ User completed all {total_from_graph} steps (completed_step={completed_step})")
                        return {
                            "status": "success",
                            "question": f"Hoàn thành tất cả các bước {topic if topic else 'thực hiện'}",
                            "answer": """✅ Hiện tại tất cả các bước đã hoàn thành!

Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận.

Nếu giao dịch chưa thành công hoặc bạn cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn""",
                            "confidence": 1.0,
                            "related_entities": continuation_context.get("entities", {}),
                            "alternative_actions": [],
                            "related_questions": [],
                            "all_results": [{
                                "question_id": last_faq_id,
                                "question": graph_result.get('faq_question', '')
                            }],
                            "is_continuation": True,
                            "is_completed": True,
                            "completed_step": completed_step,
                            "next_steps": [],
                            "total_steps": total_from_graph
                        }

            # Fallback: Check if graph query returned NO steps (meaning we're beyond the last step)
            if graph_result and graph_result.get('total_steps', 0) == 0:
                logger.info(f"✅ No more steps in graph (user completed all steps)")
                return {
                    "status": "success",
                    "question": f"Hoàn thành tất cả các bước {topic if topic else 'thực hiện'}",
                    "answer": """✅ Hiện tại tất cả các bước đã hoàn thành!

Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận.

Nếu giao dịch chưa thành công hoặc bạn cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn""",
                    "confidence": 1.0,
                    "related_entities": continuation_context.get("entities", {}),
                    "alternative_actions": [],
                    "related_questions": [],
                    "all_results": [{
                        "question_id": last_faq_id,
                        "question": graph_result.get('faq_question', '')
                    }],
                    "is_continuation": True,
                    "is_completed": True,
                    "completed_step": completed_step,
                    "next_steps": [],
                    "total_steps": 0
                }

            if graph_result:
                # SUCCESS: Found steps in graph!
                logger.info(f"✅ Graph query SUCCESS!")
                logger.info(f"   Process: {graph_result['process_name']}")
                logger.info(f"   Total steps returned: {graph_result['total_steps']}")

                # Build continuation response - KEEP original step numbers (NO renumbering)
                steps_text = []
                steps_metadata = []

                for step in graph_result['steps']:
                    # Keep original step number
                    step_num = step['number']
                    steps_text.append(f"Bước {step_num}: {step['text']}")
                    steps_metadata.append({
                        "number": step_num,
                        "text": step['text']
                    })

                continuation_answer = "\n".join(steps_text)

                # CRITICAL FIX: Preserve topic and entities from context for next turn
                # Without this, the topic is lost and subsequent "tiếp tục" queries fail
                preserved_entities = continuation_context.get("entities", {})
                if continuation_context.get("topic") and "topics" not in preserved_entities:
                    preserved_entities["topics"] = [continuation_context["topic"]]

                logger.info(f"🔄 Returning continuation response with next_steps: {steps_metadata}")

                return {
                    "status": "success",
                    "question": graph_result['faq_question'],
                    "answer": continuation_answer,
                    "confidence": 0.95,  # High confidence - direct graph match
                    "related_entities": preserved_entities,  # PRESERVE context!
                    "alternative_actions": [],
                    "related_questions": [],
                    "all_results": [{
                        "question_id": last_faq_id,  # PRESERVE FAQ ID for next continuation
                        "question": graph_result['faq_question']
                    }],
                    "is_continuation": True,
                    "is_from_graph": True,  # Mark as graph-based
                    "completed_step": completed_step,
                    "next_steps": steps_metadata,  # Keep original numbering
                    "total_steps": len(steps_metadata),
                    "source": "neo4j_step_nodes"  # For tracking
                }

        # FALLBACK: Graph query failed or no FAQ ID - use cached steps from context
        logger.warning("⚠️  Graph query failed or unavailable, using cached steps from context")

        # Initialize step tracker with cached steps or previous answer
        tracker = StepTracker()
        if all_steps:
            # Use cached steps from context
            logger.info(f"   Using {len(all_steps)} cached steps from context")
            tracker.current_steps = all_steps
        else:
            # Extract steps from previous answer
            logger.info("   Extracting steps from previous answer")
            tracker.extract_steps(previous_answer)

        # Check if user asking for next step when all steps completed
        if tracker.has_steps():
            total_cached_steps = tracker.get_total_steps()
            if next_step > total_cached_steps:
                logger.info(f"✅ All cached steps completed! (next_step={next_step}, total={total_cached_steps})")
                return {
                    "status": "success",
                    "question": f"Hoàn thành tất cả các bước {topic if topic else 'thực hiện'}",
                    "answer": f"""✅ Bạn đã hoàn thành tất cả {total_cached_steps} bước!

Nếu bạn vẫn gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn""",
                    "confidence": 1.0,
                    "related_entities": continuation_context.get("entities", {}),
                    "alternative_actions": [],
                    "related_questions": [],
                    "all_results": [],
                    "is_continuation": True,
                    "is_completed": True,
                    "completed_step": completed_step,
                    "next_steps": [],
                    "total_steps": total_cached_steps
                }

        # If still no steps, do a regular FAQ search WITH TOPIC CONTEXT
        if not tracker.has_steps():
            logger.warning("⚠️  No cached steps available, falling back to FAQ search")
            import re
            base_query = re.sub(r'sau\s+khi\s+.*$', '', user_query, flags=re.IGNORECASE).strip()

            # CRITICAL: Add topic to query to avoid getting wrong FAQ
            if topic:
                base_query = f"{topic} {base_query}"
                logger.info(f"   Added topic to query: '{base_query}'")

            relevant_nodes = self._find_relevant_nodes(base_query, query_entities, 5, "HOW_TO")
            context = self._get_graph_context(relevant_nodes, query_entities, base_query, "HOW_TO")
            return self._rank_results(context, base_query, "HOW_TO", query_entities)

        # Generate continuation response from cached steps
        continuation_answer = tracker.format_continuation_response(
            current_step=completed_step,
            include_all_remaining=True  # Show ALL remaining steps
        )

        # Get ALL remaining steps for metadata
        next_steps = tracker.get_steps_from(completed_step + 1)

        # CRITICAL FIX: Preserve topic and FAQ ID for next turn
        preserved_entities = continuation_context.get("entities", {})
        if continuation_context.get("topic") and "topics" not in preserved_entities:
            preserved_entities["topics"] = [continuation_context["topic"]]

        # Preserve FAQ ID in all_results
        all_results = []
        if last_faq_id:
            all_results = [{
                "question_id": last_faq_id,
                "question": f"Các bước tiếp theo sau Bước {completed_step}"
            }]

        # Build response
        response = {
            "status": "success",
            "question": f"Các bước tiếp theo sau Bước {completed_step}",
            "answer": continuation_answer,
            "confidence": 0.95,  # High confidence for continuation
            "related_entities": preserved_entities,  # PRESERVE context!
            "alternative_actions": [],
            "related_questions": [],
            "all_results": all_results,  # PRESERVE FAQ ID!
            "is_continuation": True,
            "completed_step": completed_step,
            "next_steps": next_steps,
            "total_steps": tracker.get_total_steps()
        }

        logger.info(f"✅ Step continuation response generated ({len(next_steps)} next steps)")

        return response

    def clear_cache(self):
        """Clear query cache"""
        self.cache = {}
        logger.info("Cache cleared")

    def close(self):
        """Close Neo4j connection"""
        self.connector.close()


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Initialize engine
    engine = Neo4jGraphRAGEngine()

    try:
        # Test queries
        test_queries = [
            "Làm sao để nạp tiền từ ngân hàng vào VNPT Money?",
            "Tôi nạp tiền từ Vietinbank bị lỗi thì phải làm gì?",
            "Giao dịch nạp tiền thất bại nhưng ngân hàng đã trừ tiền",
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")

            result = engine.query(query)

            print(f"\nStatus: {result['status']}")
            if result['status'] == 'success':
                print(f"\nAnswer:\n{result['answer']}")
                print(f"\nConfidence: {result['confidence']:.2f}")

                if result.get('alternative_actions'):
                    print(f"\nAlternative Actions:")
                    for alt in result['alternative_actions']:
                        print(f"  - {alt['action']}: {alt['reason']}")

                if result.get('related_questions'):
                    print(f"\nRelated Questions:")
                    for rq in result['related_questions']:
                        print(f"  - {rq['question']}")

    finally:
        # Close connection
        engine.close()
