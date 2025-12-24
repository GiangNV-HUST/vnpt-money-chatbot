"""
Neo4j GraphRAG Query Engine for VNPT Money Chatbot
Implements graph traversal and retrieval using Neo4j Cypher queries
"""

import logging
from typing import List, Dict, Optional
import numpy as np

from neo4j_connector import Neo4jConnector
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jGraphRAGEngine:
    """GraphRAG Engine using Neo4j backend"""

    def __init__(self):
        """Initialize GraphRAG Engine with Neo4j"""
        self.connector = Neo4jConnector()
        self.embeddings_model = None
        self._initialize_embeddings()

        # Initialize enhanced entity extractor (with regex & confidence scoring)
        from enhanced_entity_extractor import EnhancedEntityExtractor
        self.entity_extractor = EnhancedEntityExtractor()
        logger.info("Enhanced entity extractor initialized (regex + confidence scoring)")

        # Initialize intent classifier (NEW)
        from intent_classifier import IntentClassifier
        self.intent_classifier = IntentClassifier()
        logger.info("Intent classifier initialized")

        # Initialize step extractor (NEW)
        from step_tracker import StepExtractor
        self.step_extractor = StepExtractor(neo4j_connector=self.connector)
        logger.info("Step extractor initialized")

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

    def query(self, user_query: str, top_k: int = 5, continuation_context: Optional[Dict] = None) -> Dict:
        """
        Main query method - ENTITY-FIRST APPROACH with CONTEXT SUPPORT

        Args:
            user_query: User's question
            top_k: Number of results to return
            continuation_context: Optional conversation context for step continuation

        Returns:
            Query result with answers, context, and metadata
        """
        # Check cache (skip if continuation context provided)
        if not continuation_context and config.CACHE_ENABLED and user_query in self.cache:
            logger.info("Returning cached result")
            return self.cache[user_query]

        logger.info(f"Processing query: {user_query}")

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

        # Step 2: Find relevant nodes (GRAPH-ONLY search)
        relevant_nodes = self._find_relevant_nodes(user_query, query_entities, top_k, intent)

        # Step 3: Traverse graph to get context (with early exact match boosting)
        context = self._get_graph_context(relevant_nodes, query_entities, user_query)

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

        # Fallback: If NO entities extracted -> use keyword search
        logger.warning("No entities found in query - using keyword fallback")
        keyword_results = self._keyword_search(query, top_k)

        return keyword_results

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

        # Build entity lists for different types
        topics = query_entities.get("Topic", [])
        services = query_entities.get("Service", [])
        banks = query_entities.get("Bank", [])
        errors = query_entities.get("Error", [])
        actions = query_entities.get("Action", [])
        features = query_entities.get("Feature", [])

        # Combine all entity names for matching
        all_entities = topics + services + banks + errors + actions + features

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

        // ENTITY-SPECIFIC FILTERING: Check Service/Bank/Error matches
        OPTIONAL MATCH (f)-[:MENTIONS_SERVICE]->(s:Service)
        OPTIONAL MATCH (f)-[:MENTIONS_BANK]->(b:Bank)
        OPTIONAL MATCH (f)-[:DESCRIBES_ERROR]->(err:Error)

        WITH f, entity_matches, rel_types, entity_types, matched_entities, exact_matches,
             collect(DISTINCT s.name) as faq_services,
             collect(DISTINCT b.name) as faq_banks,
             collect(DISTINCT err.name) as faq_errors

        // Calculate Service/Bank/Error match bonus
        WITH f, entity_matches, rel_types, entity_types, matched_entities, exact_matches,
             faq_services, faq_banks, faq_errors,
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
             END as error_match_bonus

        // Calculate graph-based score with entity-specific boosting
        WITH f,
             entity_matches,
             rel_types,
             entity_types,
             matched_entities,
             exact_matches,
             service_match_bonus,
             bank_match_bonus,
             error_match_bonus,
             // Bonus for specific relationship types (REDUCED ERROR BOOST)
             CASE
               WHEN 'DESCRIBES_ERROR' IN rel_types THEN 1.5  // REDUCED from 3.0 (let error_match_bonus handle it)
               WHEN 'ABOUT' IN rel_types THEN 1.5
               WHEN 'MENTIONS_BANK' IN rel_types THEN 1.5
               WHEN 'MENTIONS_SERVICE' IN rel_types THEN 1.5
               WHEN 'SUGGESTS_ACTION' IN rel_types THEN 1.2
               ELSE 1.0
             END as rel_weight,
             // Exact match bonus
             exact_matches * 0.5 as exact_match_bonus

        RETURN f.id as id,
               (entity_matches * rel_weight + exact_match_bonus + service_match_bonus + bank_match_bonus + error_match_bonus) as graph_score,
               entity_matches,
               rel_types,
               entity_types,
               matched_entities,
               service_match_bonus,
               bank_match_bonus,
               error_match_bonus
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
                "top_k": top_k
            }
        )

        if not results:
            logger.warning(f"No graph results found for entities: {all_entities}")
            return []

        # Normalize scores
        max_score = max([r["graph_score"] for r in results]) if results else 1.0

        # Log entity-specific boosts for monitoring
        for r in results[:5]:  # Log top 5
            if r.get("service_match_bonus", 0) != 0 or r.get("bank_match_bonus", 0) != 0 or r.get("error_match_bonus", 0) != 0:
                logger.info(f"  FAQ {r['id']}: service_boost={r.get('service_match_bonus', 0):.2f}, "
                          f"bank_boost={r.get('bank_match_bonus', 0):.2f}, "
                          f"error_boost={r.get('error_match_bonus', 0):.2f}, "
                          f"total_score={r['graph_score']:.2f}")

        return [
            {
                "node_id": r["id"],
                "score": float(r["graph_score"]) / max_score,
                "method": "entity_graph",
                "entity_matches": r["entity_matches"],
                "rel_types": r["rel_types"],
                "service_boost": r.get("service_match_bonus", 0),
                "bank_boost": r.get("bank_match_bonus", 0),
                "error_boost": r.get("error_match_bonus", 0)
            }
            for r in results
        ]

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
        """Search by keyword matching"""
        # Simple keyword search in FAQ question and answer
        cypher = """
        MATCH (f:FAQ)
        WHERE toLower(f.question) CONTAINS toLower($query)
           OR toLower(f.answer) CONTAINS toLower($query)
        RETURN f.id as id,
               CASE
                 WHEN toLower(f.question) CONTAINS toLower($query) THEN 2
                 ELSE 1
               END as match_count
        ORDER BY match_count DESC
        LIMIT $top_k
        """

        results = self.connector.execute_query(
            cypher,
            {"query": query, "top_k": top_k}
        )

        # Normalize scores
        max_score = max([r["match_count"] for r in results]) if results else 1
        return [
            {
                "node_id": r["id"],
                "score": r["match_count"] / max_score,
                "method": "keyword"
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
        user_query: str = ""
    ) -> List[Dict]:
        """
        Get context by traversing the graph from relevant nodes
        Applies EARLY exact match boosting before final ranking

        Args:
            relevant_nodes: List of {node_id, score}
            query_entities: Entities from query
            user_query: Original user query for exact match detection

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
            # UPDATED: Also retrieve Case nodes with their Steps
            cypher = """
            MATCH (f:FAQ {id: $node_id})
            OPTIONAL MATCH (f)-[:MENTIONS_SERVICE]->(s:Service)
            OPTIONAL MATCH (f)-[:MENTIONS_BANK]->(b:Bank)
            OPTIONAL MATCH (f)-[:DESCRIBES_ERROR]->(e:Error)
            OPTIONAL MATCH (f)-[:SUGGESTS_ACTION]->(act:Action)
            OPTIONAL MATCH (act)-[:USES_FEATURE]->(feat:Feature)
            OPTIONAL MATCH (f)-[:SIMILAR_TO]-(similar:FAQ)
            OPTIONAL MATCH (f)-[:ABOUT]->(t:Topic)
            RETURN f,
                   collect(DISTINCT s.name) as services,
                   collect(DISTINCT b.name) as banks,
                   collect(DISTINCT e.name) as errors,
                   collect(DISTINCT act.name) as actions,
                   collect(DISTINCT feat.name) as features,
                   collect(DISTINCT {question: similar.question, id: similar.id}) as related_questions,
                   collect(DISTINCT t.name) as topics
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
            if query_lower and question_text:
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(None, query_lower, question_text.lower()).ratio()

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
                # Match Case based on query keywords
                query_lower = user_query.lower()

                # Scoring for each case
                case_scores = []
                for case in case_results:
                    score = 0
                    case_name = (case.get('case_name') or '').lower()
                    case_desc = (case.get('case_description') or '').lower()
                    case_method = (case.get('case_method') or '').lower()

                    # Keyword matching for "liên kết trực tiếp" vs "chuyển khoản"
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

                logger.info(f"Selected Case: {selected_case.get('name')} ({len(case_steps)} steps)")

            # NEW: Build answer from Case steps if available
            if case_steps and selected_case:
                # Use Case steps instead of full FAQ answer
                steps_text = "\n".join([
                    f'Bước {step["number"]}: {step["text"]}'
                    for step in case_steps
                ])
                case_name = selected_case.get('name', '')
                case_based_answer = f"{case_name}:\n\n{steps_text}"
            else:
                case_based_answer = faq.get("answer", "")

            context_item = {
                "question_id": node_id,
                "question": question_text,
                "answer": case_based_answer,  # Use Case-based answer if available
                "relevance_score": relevance_score,
                "related_entities": {
                    "services": [s for s in data.get("services", []) if s],
                    "banks": [b for b in data.get("banks", []) if b],
                    "errors": [e for e in data.get("errors", []) if e],
                    "actions": [a for a in data.get("actions", []) if a],
                    "features": [f for f in data.get("features", []) if f],
                    "topics": [t for t in data.get("topics", []) if t],
                },
                "related_questions": [
                    {"question": rq["question"]}
                    for rq in data.get("related_questions", [])
                    if rq.get("question")
                ][:3],
                "alternative_actions": alternative_actions,
                # NEW: Add Case info
                "selected_case": selected_case.get('name') if selected_case else None,
                "case_steps": case_steps
            }

            context.append(context_item)

        return context

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

            if similarity > 0.9:  # 90%+ similarity
                exact_match_boost = 0.4  # BOOST for exact match (reduced to let entity filtering win)
                logger.info(f"Exact match found ({similarity:.2%}): {result.get('question', '')[:80]}")
            elif similarity > 0.75:  # 75-90% similarity
                exact_match_boost = 0.2  # SMALL boost for very similar (let entity filtering dominate)
                logger.info(f"High similarity ({similarity:.2%}): {result.get('question', '')[:80]}")

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

            elif intent == "HOW_TO":
                # STRONG BOOST for instructional content
                how_to_signals = [
                    "làm thế nào", "như thế nào", "cách", "hướng dẫn",
                    "bước", "step", "để thực hiện", "quy trình", "thủ tục"
                ]
                for signal in how_to_signals:
                    if signal in question_lower or signal in answer_lower:
                        intent_boost += 0.4  # Increased from 0.3 to 0.4
                        logger.info(f"✓ HOW_TO boost: Found '{signal}' in instructional FAQ")
                        break

                # CRITICAL: Detect procedural content with numbered steps (MAJOR boost)
                import re
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
                    intent_boost += 0.6  # MASSIVE boost for step-by-step instructions
                    logger.info(f"✓ HOW_TO PROCEDURAL boost: FAQ contains numbered steps")

                # STRONG PENALTY for troubleshooting answers in HOW_TO queries
                troubleshoot_signals = [
                    "thất bại", "chưa nhận được", "không thành công",
                    "bị lỗi", "bị trừ", "phải làm gì", "tại sao",
                    "kiểm tra trạng thái", "giao dịch thất bại"
                ]
                has_troubleshoot = False
                for signal in troubleshoot_signals:
                    if signal in question_lower or signal in answer_lower:
                        has_troubleshoot = True
                        logger.info(f"⚠️ HOW_TO penalty: Found '{signal}' in troubleshooting FAQ")
                        break

                # Only apply penalty if NO how-to signals found (avoid penalizing mixed content)
                if has_troubleshoot and intent_boost == 0.0:
                    intent_boost -= 0.5  # Heavy penalty only if no how-to content

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

        response = {
            "status": "success",
            "question": top_result["question"],
            "answer": top_result["answer"],  # Already formatted with Case steps
            "confidence": top_result["relevance_score"],
            "related_entities": top_result["related_entities"],
            "alternative_actions": top_result["alternative_actions"],
            "related_questions": top_result["related_questions"][:3],
            "all_results": context[:config.TOP_K_RETRIEVAL],
            # NEW: Add case info
            "case_info": case_info if case_info else None
        }

        return response

    def _query_steps_by_faq_id(
        self,
        faq_id: str,
        from_step: int = 1,
        only_next_step: bool = True
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

            cypher = f"""
            MATCH (faq:FAQ {{question_id: $faq_id}})-[:DESCRIBES_PROCESS]->(p:Process)
            MATCH (p)-[:HAS_STEP]->(s:Step)
            {where_clause}
            RETURN faq.question as faq_question,
                   faq.answer as faq_answer,
                   p.name as process_name,
                   p.id as process_id,
                   s.number as step_num,
                   s.text as step_text
            ORDER BY s.number
            """
            params = {"faq_id": faq_id, "from_step": from_step}

            results = self.connector.execute_query(cypher, params)

            if not results:
                logger.warning(f"No steps found for FAQ ID: {faq_id}")
                return None

            # Build result
            first_row = results[0]
            result = {
                "faq_question": first_row['faq_question'],
                "faq_answer": first_row['faq_answer'],
                "process_name": first_row['process_name'],
                "process_id": first_row['process_id'],
                "steps": [],
                "direction_score": 10  # Perfect match since we're using exact FAQ ID
            }

            for row in results:
                result["steps"].append({
                    "number": row['step_num'],
                    "text": row['step_text']
                })

            result["total_steps"] = len(result["steps"])

            logger.info(f"📊 Query by FAQ ID SUCCESS: Found {result['total_steps']} steps")
            logger.info(f"   FAQ: {result['faq_question'][:60]}...")

            return result

        except Exception as e:
            logger.error(f"Failed to query steps by FAQ ID: {e}")
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

        # CRITICAL FIX: ALWAYS try graph query first if FAQ ID is available
        # Graph data is more accurate than regex-extracted cached steps
        graph_result = None
        if last_faq_id:
            logger.info("🔍 PRIORITY: Querying Step nodes from graph using FAQ ID...")
            logger.info(f"   Using FAQ ID for accurate retrieval: {last_faq_id}")
            # Only get the NEXT step, not all remaining steps
            graph_result = self._query_steps_by_faq_id(last_faq_id, from_step=next_step, only_next_step=True)

            # PRIORITY 2: Fallback to keyword-based query if FAQ ID not available or failed
            if not graph_result:
                logger.info("   Falling back to keyword-based query...")
                # Extract base query (minimal regex - only to remove continuation phrase)
                import re
                base_query = re.sub(r'sau\s+khi\s+.*$', '', user_query, flags=re.IGNORECASE).strip()
                logger.info(f"   Base query: {base_query[:60]}...")

                # GRAPH QUERY: Get steps directly from Step nodes (only next step)
                graph_result = self._query_steps_from_graph(base_query, from_step=next_step, only_next_step=True)

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

        # If still no steps, do a regular FAQ search
        if not tracker.has_steps():
            logger.warning("⚠️  No cached steps available, falling back to FAQ search")
            import re
            base_query = re.sub(r'sau\s+khi\s+.*$', '', user_query, flags=re.IGNORECASE).strip()
            relevant_nodes = self._find_relevant_nodes(base_query, query_entities, 5, "HOW_TO")
            context = self._get_graph_context(relevant_nodes, query_entities, base_query)
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
