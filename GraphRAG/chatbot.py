"""
GraphRAG Chatbot for VNPT Money
Combines GraphRAG retrieval with LLM generation
NOW WITH MEM0 INTELLIGENT MEMORY + FOLLOW-UP DETECTION!
"""

import logging
from typing import Dict, List, Optional

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Mem0 components (NEW!)
try:
    from memory_manager import MemoryManager
    from follow_up_detector import FollowUpDetector
    MEM0_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Mem0 components not available: {e}")
    MEM0_COMPONENTS_AVAILABLE = False


class GraphRAGChatbot:
    """Chatbot that uses GraphRAG + LLM + Mem0 for intelligent conversation with context tracking"""

    def __init__(self, user_id: str = "default"):
        """Initialize chatbot with GraphRAG engine, LLM, and Mem0

        Args:
            user_id: User identifier for Mem0 memory scoping
        """
        self.user_id = user_id

        # Initialize GraphRAG engine
        self.rag_engine = Neo4jGraphRAGEngine()

        # Initialize Conversation Context Manager (legacy backup)
        self.context_manager = ConversationContextManager(max_history=5)
        logger.info("Conversation context manager initialized")

        # Initialize Mem0 Memory Manager (NEW!)
        self.memory_manager = None
        self.follow_up_detector = None

        if MEM0_COMPONENTS_AVAILABLE and getattr(config, 'ENABLE_MEM0', False):
            try:
                self.memory_manager = MemoryManager()
                self.follow_up_detector = FollowUpDetector()
                logger.info("✅ Mem0 Memory Manager and Follow-up Detector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Mem0 components: {e}")
        else:
            logger.info("Mem0 disabled or not available, using legacy context manager")

        # Initialize LLM
        self.llm = None
        self._initialize_llm()

        # Conversation history (legacy, now using context_manager)
        self.conversation_history = []

        # Last RAG result for context (NEW!)
        self.last_rag_result = None

    def _initialize_llm(self):
        """Initialize LLM based on configuration"""
        try:
            if config.LLM_PROVIDER == "vllm":
                self._initialize_vllm()
            elif config.LLM_PROVIDER == "openai":
                self._initialize_openai()
            else:
                logger.warning("No LLM configured, using template responses")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            logger.warning("Falling back to template responses")

    def _initialize_openai(self):
        """Initialize OpenAI LLM"""
        try:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.llm = "openai"
            logger.info(f"OpenAI LLM initialized: {config.LLM_MODEL}")
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
            raise

    def _initialize_vllm(self):
        """Initialize vLLM client (OpenAI-compatible API)"""
        try:
            from openai import OpenAI, DefaultHttpxClient

            # Create httpx client without proxy for vLLM server (bypass corporate proxy)
            http_client = DefaultHttpxClient(
                trust_env=False,
                timeout=config.VLLM_TIMEOUT,
            )

            self.llm_client = OpenAI(
                api_key=config.VLLM_API_KEY,
                base_url=config.VLLM_API_BASE,
                http_client=http_client,
            )
            self.llm = "vllm"
            logger.info(f"vLLM initialized: {config.VLLM_MODEL} at {config.VLLM_API_BASE}")
        except Exception as e:
            logger.error(f"vLLM initialization failed: {e}")
            raise

    def _is_chitchat(self, message: str) -> bool:
        """Check if message is chitchat/greeting (not FAQ-related)"""
        import re

        message_lower = message.lower().strip()

        # CRITICAL FIX: Use word boundaries to prevent false positives
        # Example: "tên bạn là gì?" should match, but "Họ tên bạn không trùng" should NOT

        # Greeting patterns (use word boundaries)
        greeting_patterns = [
            r'\bxin chào\b', r'\bchào bạn\b', r'\bhello\b', r'\bhi\b',
            r'^chào\b', r'\bchào$'  # "chào" at start or end only
        ]

        # Identity question patterns (more specific)
        identity_patterns = [
            r'\bbạn là ai\b', r'\bbạn là gì\b',
            r'\btên bạn là\b', r'\btên bạn\?',  # "tên bạn là gì?" or "tên bạn?"
            r'^tên bạn\b', # Only at start of message
            r'\bai đây\b'
        ]

        # Thanks patterns
        thanks_patterns = [
            r'\bcảm ơn\b', r'\bcám ơn\b', r'\bthank\b', r'\bthanks\b'
        ]

        # Goodbye patterns
        goodbye_patterns = [
            r'\btạm biệt\b', r'\bbye\b', r'\bgoodbye\b'
        ]

        # Capability question patterns
        capability_patterns = [
            r'\bbạn làm được gì\b', r'\bbạn có thể làm gì\b', r'\bgiúp gì được\b'
        ]

        # Combine all patterns
        all_patterns = (greeting_patterns + identity_patterns + thanks_patterns +
                       goodbye_patterns + capability_patterns)

        # Check if any pattern matches
        for pattern in all_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def _handle_chitchat(self, message: str) -> str:
        """Handle chitchat/greeting messages"""
        message_lower = message.lower().strip()

        # Greetings
        if any(x in message_lower for x in ["xin chào", "chào bạn", "hello", "hi ", "chào"]):
            return "Xin chào! Tôi là VNPT Assistant, trợ lý ảo của VNPT Money. Tôi có thể giúp bạn giải đáp các thắc mắc về dịch vụ VNPT Money. Bạn cần hỗ trợ gì?"

        # Identity
        if any(x in message_lower for x in ["bạn là ai", "bạn là gì", "tên bạn", "ai đây"]):
            return "Tôi là VNPT Assistant - trợ lý ảo thông minh của VNPT Money. Tôi được thiết kế để giúp bạn giải đáp các câu hỏi về dịch vụ ví điện tử VNPT Money, bao gồm: nạp tiền, rút tiền, chuyển tiền, liên kết ngân hàng và các tính năng khác. Bạn có câu hỏi gì về VNPT Money không?"

        # Thanks
        if any(x in message_lower for x in ["cảm ơn", "cám ơn", "thank"]):
            return "Rất vui được hỗ trợ bạn! Nếu có thêm câu hỏi, đừng ngại hỏi tôi nhé!"

        # Goodbyes
        if any(x in message_lower for x in ["tạm biệt", "bye", "goodbye"]):
            return "Tạm biệt! Chúc bạn một ngày tốt lành. Hẹn gặp lại!"

        # Capability
        if any(x in message_lower for x in ["bạn làm được gì", "bạn có thể làm gì", "giúp gì được"]):
            return "Tôi có thể giúp bạn:\n- Hướng dẫn sử dụng các tính năng VNPT Money (nạp tiền, rút tiền, chuyển tiền, thanh toán hóa đơn...)\n- Giải quyết các vấn đề kỹ thuật (lỗi giao dịch, liên kết ngân hàng, định danh...)\n- Tư vấn về phí, hạn mức, điều kiện sử dụng\n- Và nhiều thông tin khác về VNPT Money!\n\nBạn cần hỗ trợ gì?"

        # Default chitchat
        return "Tôi là VNPT Assistant. Bạn có câu hỏi gì về dịch vụ VNPT Money không?"

    def chat(self, user_message: str, user_id: str = None) -> str:
        """
        Process user message and return response WITH MEM0 INTELLIGENT CONTEXT

        ENHANCED: Now uses Mem0 for memory + LLM for follow-up detection

        Args:
            user_message: User's input message
            user_id: Optional user ID (uses self.user_id if not provided)

        Returns:
            Chatbot response
        """
        user_id = user_id or self.user_id
        logger.info(f"User: {user_message}")

        # Step 0: Handle chitchat/greetings first
        if self._is_chitchat(user_message):
            response = self._handle_chitchat(user_message)
            logger.info(f"Assistant (chitchat): {response}")
            return response

        # Step 1: MEM0 - Search for relevant memories (NEW!)
        follow_up_context = None
        memories = []

        if self.memory_manager:
            logger.info("🧠 Searching Mem0 for relevant context...")
            memory_result = self.memory_manager.get_context_for_query(
                query=user_message,
                user_id=user_id,
                min_score=getattr(config, 'MEM0_MIN_RELEVANCE_SCORE', 0.5),
                limit=getattr(config, 'MEM0_SEARCH_LIMIT', 5)
            )

            memories = memory_result.get("memories", [])
            has_context = memory_result.get("has_context", False)
            top_score = memory_result.get("top_score", 0)

            logger.info(f"   Found {len(memories)} memories, top_score={top_score:.2f}")

            # Step 2: Follow-up Detection (if memories found)
            if has_context and self.follow_up_detector:
                logger.info("🔍 Detecting if this is a follow-up question...")

                # Get previous Q&A for context
                previous_qa = None
                if self.last_rag_result:
                    previous_qa = {
                        "question": self.conversation_history[-1].get("user", "") if self.conversation_history else "",
                        "answer": self.last_rag_result.get("answer", "")[:500]
                    }

                detection_result = self.follow_up_detector.detect(
                    query=user_message,
                    memories=memories,
                    previous_qa=previous_qa,
                    memory_score_threshold=getattr(config, 'MEM0_FOLLOW_UP_THRESHOLD', 0.7),
                    use_llm=getattr(config, 'FOLLOW_UP_USE_LLM', True)
                )

                logger.info(f"   Detection: is_follow_up={detection_result.is_follow_up}, "
                           f"confidence={detection_result.confidence:.2f}, "
                           f"method={detection_result.detection_method}")

                if detection_result.is_follow_up:
                    # Build follow-up context for RAG engine
                    # Get FAQ ID from memory metadata if available
                    faq_id = None
                    if memories:
                        faq_id = memories[0].get("metadata", {}).get("faq_id")
                    # Also check last RAG result
                    if not faq_id and self.last_rag_result:
                        faq_id = self.last_rag_result.get("faq_id")

                    follow_up_context = {
                        "is_follow_up": True,
                        "topic": detection_result.topic or memory_result.get("suggested_topic"),
                        "faq_id": faq_id,
                        "context_needed": detection_result.context_needed,
                        "memories": memories,
                        "confidence": detection_result.confidence
                    }

                    logger.info(f"✅ Follow-up context built: topic='{follow_up_context['topic']}', "
                               f"faq_id='{follow_up_context['faq_id']}'")

        # Step 3: Legacy context check (backup if Mem0 not available)
        enhanced_query = user_message
        continuation_context = None

        if not follow_up_context:
            # Use legacy context manager
            enhanced_query, continuation_context = self.context_manager.enhance_query_with_context(user_message)

        # Step 4: Retrieve relevant context from GraphRAG
        rag_result = self.rag_engine.query(
            enhanced_query,
            continuation_context=continuation_context,
            follow_up_context=follow_up_context  # NEW parameter!
        )

        # Step 5: Generate response based on intent and extraction result
        intent = rag_result.get("intent", "GENERAL")
        extraction_info = rag_result.get("extraction_info")
        steps = rag_result.get("steps", [])
        has_steps = steps and len(steps) > 0

        # Log intent and extraction info
        logger.info(f"Intent: {intent}, Has extraction: {extraction_info is not None}, Has steps: {has_steps}")

        if rag_result.get("status") == "success":
            # Check if LLM extraction was successful
            if extraction_info and extraction_info.get("confidence", 0) > 0.5:
                # Use extracted answer directly (already focused on intent)
                response = rag_result.get("answer", "")
                logger.info(f"Using LLM-extracted answer (intent: {intent})")

                # Format for readability
                response = self._format_answer_for_readability(response)

            elif has_steps:
                # Procedural FAQ - use original answer to preserve all steps
                logger.info(f"Procedural FAQ detected ({len(steps)} steps), using original answer")
                response = rag_result.get("answer", "")
                response = self._format_answer_for_readability(response)

            elif intent == "TROUBLESHOOT" and self._has_multiple_cases(rag_result.get("answer", "")):
                # TROUBLESHOOT with multiple cases - keep ALL cases, don't let LLM filter
                logger.info(f"TROUBLESHOOT with multiple cases - using original answer to preserve all scenarios")
                response = rag_result.get("answer", "")
                response = self._format_answer_for_readability(response)

            elif self.llm:
                # Fallback: Use LLM for reformatting (no extraction was done)
                response = self._generate_llm_response(user_message, rag_result, continuation_context)

            else:
                response = self._generate_template_response(rag_result)

        elif rag_result.get("status") == "no_specific_answer":
            # FAQ found but doesn't answer the SPECIFIC question
            # (e.g., user asked about Vietcombank but FAQ doesn't mention it)
            logger.info(f"No specific answer found for: {user_message}")
            response = rag_result.get("answer", "")

            # If LLM is available, make the response more natural
            if self.llm and rag_result.get("missing_entity"):
                missing_entity = rag_result.get("missing_entity")
                response = f"Xin lỗi, tôi không có thông tin cụ thể về {missing_entity} trong cơ sở dữ liệu. "
                response += "Bạn có thể liên hệ Hotline 1900 8198 hoặc truy cập "
                response += "https://vnptpay.vn/web/trogiup/bieuphi_mm để xem biểu phí chi tiết."

        else:
            # No results found
            if self.llm:
                response = self._generate_llm_response(user_message, rag_result, continuation_context)
            else:
                response = self._generate_template_response(rag_result)

        # Step 6: Save to Mem0 Memory (NEW!)
        if self.memory_manager:
            try:
                # Prepare metadata for memory
                memory_metadata = {
                    "faq_id": rag_result.get("faq_id"),
                    "intent": intent,
                    "topic": rag_result.get("follow_up_topic") or self._extract_topic_from_result(rag_result),
                    "confidence": rag_result.get("confidence", 0)
                }

                self.memory_manager.add(
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response[:1000]}  # Truncate long responses
                    ],
                    user_id=user_id,
                    metadata=memory_metadata
                )
                logger.info(f"💾 Saved to Mem0 memory (faq_id={memory_metadata['faq_id']}, topic={memory_metadata['topic']})")
            except Exception as e:
                logger.warning(f"Failed to save to Mem0: {e}")

        # Step 7: Store last RAG result for follow-up detection (NEW!)
        self.last_rag_result = rag_result

        # Step 8: Add to conversation context (legacy backup)
        self.context_manager.add_turn(user_message, rag_result)

        # Step 9: Add to legacy conversation history
        self.conversation_history.append({
            "user": user_message,
            "assistant": response,
            "rag_context": rag_result,
            "intent": intent,
            "is_follow_up": bool(follow_up_context)
        })

        logger.info(f"Assistant: {response[:200]}...")

        return response

    def _extract_topic_from_result(self, rag_result: Dict) -> Optional[str]:
        """Extract topic from RAG result for memory metadata"""
        # Check related entities
        entities = rag_result.get("related_entities", {})

        # Priority order for topic extraction
        if entities.get("Topic"):
            return entities["Topic"][0] if isinstance(entities["Topic"], list) else entities["Topic"]

        # Check question for common topics
        question = rag_result.get("question", "").lower()

        topic_keywords = {
            "chuyển tiền": ["chuyển tiền", "chuyển khoản"],
            "nạp tiền": ["nạp tiền", "nạp cước", "top-up"],
            "rút tiền": ["rút tiền", "rút về"],
            "thanh toán": ["thanh toán", "trả tiền"],
            "liên kết ngân hàng": ["liên kết", "link ngân hàng"],
            "ekyc": ["ekyc", "định danh", "xác thực"],
            "đăng ký": ["đăng ký", "tạo tài khoản"],
        }

        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in question:
                    return topic

        return None

    def _generate_llm_response(self, user_message: str, rag_result: Dict, continuation_context: Optional[Dict] = None) -> str:
        """Generate response using LLM with RAG context"""

        # Build prompt with context
        prompt = self._build_prompt(user_message, rag_result, continuation_context)

        try:
            if self.llm == "vllm":
                return self._call_vllm(prompt)
            elif self.llm == "openai":
                return self._call_openai(prompt)
            else:
                return self._generate_template_response(rag_result)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._generate_template_response(rag_result)

    def _build_prompt(self, user_message: str, rag_result: Dict, continuation_context: Optional[Dict] = None) -> str:
        """Build prompt for LLM with RAG context"""

        if rag_result["status"] != "success":
            return f"""Bạn là trợ lý ảo thông minh của VNPT Money, tên là "VNPT Assistant".

CÂU HỎI: {user_message}

YÊU CẦU:
Rất tiếc, tôi không tìm thấy thông tin chính xác trong cơ sở dữ liệu về câu hỏi này.

Hãy trả lời một cách thân thiện và lịch sự:
1. Xin lỗi khách hàng vì chưa có thông tin
2. Đề xuất họ liên hệ Hotline: 1900 8198 hoặc email: hotro@vnptmoney.vn
3. Giọng điệu chuyên nghiệp, thấu hiểu
4. Ngắn gọn, không dài dòng"""

        # Extract context
        answer = rag_result.get("answer", "")
        related_entities = rag_result.get("related_entities", {})
        alternative_actions = rag_result.get("alternative_actions", [])
        related_questions = rag_result.get("related_questions", [])
        steps = rag_result.get("steps", [])
        confidence = rag_result.get("confidence", 0)

        # Build context string with better structure
        context_parts = []

        # Main answer
        context_parts.append(f"📌 THÔNG TIN CHÍNH:\n{answer}")

        # Steps if available
        if steps and len(steps) > 0:
            steps_text = "\n".join([f"   Bước {i+1}: {step}" for i, step in enumerate(steps)])
            context_parts.append(f"\n📝 CÁC BƯỚC THỰC HIỆN:\n{steps_text}")

        # Related entities (ENRICHED with descriptions)
        if related_entities:
            entities_info = []
            if related_entities.get("services"):
                entities_info.append(f"   • Dịch vụ: {', '.join(related_entities['services'])}")
            if related_entities.get("banks"):
                entities_info.append(f"   • Ngân hàng: {', '.join(related_entities['banks'])}")
            if related_entities.get("features"):
                entities_info.append(f"   • Tính năng: {', '.join(related_entities['features'])}")

            # ENRICHED: Errors with solution
            if related_entities.get("errors"):
                errors = related_entities['errors']
                error_texts = []
                for err in errors:
                    if isinstance(err, dict):
                        name = err.get('name', '')
                        solution = err.get('solution', '')
                        if solution:
                            error_texts.append(f"{name} → Giải pháp: {solution}")
                        else:
                            error_texts.append(name)
                    else:
                        error_texts.append(str(err))
                if error_texts:
                    entities_info.append(f"   • Lỗi & giải pháp: {'; '.join(error_texts)}")

            # ENRICHED: Requirements with description
            if related_entities.get("requirements"):
                reqs = related_entities['requirements']
                req_texts = []
                for req in reqs:
                    if isinstance(req, dict):
                        name = req.get('name', '')
                        desc = req.get('description', '')
                        if desc:
                            req_texts.append(f"{name} ({desc})")
                        else:
                            req_texts.append(name)
                    else:
                        req_texts.append(str(req))
                if req_texts:
                    entities_info.append(f"   • Yêu cầu: {'; '.join(req_texts)}")

            # ENRICHED: Documents with description
            if related_entities.get("documents"):
                docs = related_entities['documents']
                doc_texts = []
                for doc in docs:
                    if isinstance(doc, dict):
                        name = doc.get('name', '')
                        desc = doc.get('description', '')
                        if desc:
                            doc_texts.append(f"{name} - {desc}")
                        else:
                            doc_texts.append(name)
                    else:
                        doc_texts.append(str(doc))
                if doc_texts:
                    entities_info.append(f"   • Giấy tờ cần thiết: {'; '.join(doc_texts)}")

            # ENRICHED: Contact channels with phone
            if related_entities.get("contact_channels"):
                contacts = related_entities['contact_channels']
                contact_texts = []
                for contact in contacts:
                    if isinstance(contact, dict):
                        name = contact.get('name', '')
                        phone = contact.get('phone', '')
                        desc = contact.get('description', '')
                        if phone:
                            contact_texts.append(f"{name}: {phone}")
                        elif desc:
                            contact_texts.append(f"{name} - {desc}")
                        else:
                            contact_texts.append(name)
                    else:
                        contact_texts.append(str(contact))
                if contact_texts:
                    entities_info.append(f"   • Liên hệ hỗ trợ: {'; '.join(contact_texts)}")

            # NEW: Useful links
            if related_entities.get("useful_links"):
                links = related_entities['useful_links']
                link_texts = []
                for link in links:
                    if isinstance(link, dict):
                        name = link.get('name', '')
                        url = link.get('url', '')
                        if url:
                            link_texts.append(f"{name}: {url}")
                    else:
                        link_texts.append(str(link))
                if link_texts:
                    entities_info.append(f"   • Link hữu ích: {'; '.join(link_texts)}")

            if entities_info:
                context_parts.append(f"\n🔗 THÔNG TIN LIÊN QUAN:\n" + "\n".join(entities_info))

        # Alternative actions
        if alternative_actions:
            alt_text = "\n".join([f"   • {alt['action']}: {alt['reason']}" for alt in alternative_actions])
            context_parts.append(f"\n💡 PHƯƠNG ÁN THAY THẾ:\n{alt_text}")

        # Related questions
        if related_questions:
            rq_text = "\n".join([f"   • {rq['question']}" for rq in related_questions[:3]])
            context_parts.append(f"\n❓ CÂU HỎI LIÊN QUAN:\n{rq_text}")

        context = "\n".join(context_parts)

        # Add continuation context instructions if present
        # CRITICAL: Skip if answer is a completion message
        continuation_instruction = ""
        is_completion_answer = ("✅" in answer and ("hoàn thành tất cả" in answer or "Hotline: 1900" in answer))

        if continuation_context and not is_completion_answer:
            # Case 1: Status-based continuation
            if continuation_context.get("status_result"):
                status = continuation_context["status_result"]
                next_step = continuation_context.get("next_step", 2)
                continuation_instruction = f"""
🔄 CONTINUATION CONTEXT (QUAN TRỌNG):
- Người dùng đã hoàn thành bước 1 (kiểm tra trạng thái)
- Trạng thái giao dịch: **{status}**
- BẮT BUỘC: Chỉ trả lời về bước {next_step} (trường hợp trạng thái "{status}")
- KHÔNG lặp lại bước 1 hoặc toàn bộ các bước
- Trả lời ngắn gọn, tập trung vào hành động cần làm tiếp theo

"""
            # Case 2: Step-based continuation (e.g., "đã hoàn thành N bước đầu")
            else:
                completed_step = continuation_context.get("completed_step", 1)
                next_step = continuation_context.get("next_step", 2)
                continuation_instruction = f"""
🔄 CONTINUATION CONTEXT (QUAN TRỌNG):
- Người dùng đã hoàn thành bước 1 đến bước {completed_step}
- Đang cần hướng dẫn tiếp BỘC TIẾP THEO (bước {next_step})
- BẮT BUỘC: Viết câu mở đầu TỰ NHIÊN như đang tiếp tục hội thoại
- VÍ DỤ MỞ ĐẦU TỐT:
  * "Bước tiếp theo:"
  * "Tiếp theo, bạn cần:"
  * "Sau khi hoàn thành {completed_step} bước đầu, bạn tiếp tục:"
- KHÔNG viết: "Để chuyển tiền từ VNPT Money đến ngân hàng:" (quá cứng nhắc!)
- NGỮ CẢNH chỉ chứa bước {next_step} (KHÔNG phải tất cả các bước còn lại)
- GIỮ NGUYÊN số thứ tự bước trong NGỮ CẢNH, KHÔNG đánh số lại
- Chỉ cần viết câu mở đầu tự nhiên rồi sao chép bước từ NGỮ CẢNH

"""

        # Build final prompt with improved instructions
        prompt = f"""Bạn là VNPT Assistant - trợ lý ảo của VNPT Money, nói chuyện TỰ NHIÊN như một người tư vấn viên thân thiện, KHÔNG phải là bot.

🎯 NHIỆM VỤ:
Trả lời câu hỏi dựa trên thông tin từ NGỮ CẢNH, nhưng phải VIẾT LẠI theo phong cách TỰ NHIÊN, THÂN THIỆN, DỄ HIỂU như đang tư vấn 1-1 cho khách hàng.

📋 NGUYÊN TẮC (QUAN TRỌNG):
1. **Nội dung**:
   - CHỈ sử dụng thông tin từ NGỮ CẢNH, KHÔNG bịa thêm
   - CHỈ trả lời ĐÚNG câu hỏi người dùng, KHÔNG thêm thông tin không liên quan
   - Nếu NGỮ CẢNH có nhiều FAQ: CHỈ dùng FAQ phù hợp nhất với câu hỏi
   - ⚠️ **QUAN TRỌNG - LỌC PHƯƠNG THỨC CỤ THỂ**:
     * Nếu câu hỏi đề cập đến PHƯƠNG THỨC/TÍNH NĂNG CỤ THỂ (ví dụ: "ngân hàng liên kết", "QR code", "chuyển khoản", "ví điện tử")
     * VÀ FAQ chứa NHIỀU phương thức/hình thức khác nhau
     * Thì CHỈ trích xuất và trả lời về phương thức được hỏi, BỎ QUA các phương thức khác
     * VÍ DỤ: Nếu hỏi "nạp tiền từ ngân hàng liên kết" → CHỈ trả lời về phương thức liên kết, KHÔNG kể "nạp bằng QR" hoặc phương thức khác
   - ⚠️ **QUAN TRỌNG - CÂU HỎI TROUBLESHOOT (xử lý lỗi/sự cố)**:
     * Nếu NGỮ CẢNH có NHIỀU TRƯỜNG HỢP (ví dụ: "Thành công", "Đang xử lý", "Thất bại")
     * VÀ câu hỏi là về XỬ LÝ SỰ CỐ/LỖI (giao dịch không nhận được tiền, lỗi, thất bại...)
     * Thì PHẢI TRẢ LỜI ĐẦY ĐỦ TẤT CẢ các trường hợp vì người dùng cần biết TẤT CẢ tình huống có thể xảy ra
     * VÍ DỤ: "nạp tiền thành công nhưng chưa nhận được" → trả lời cả trường hợp "Thành công" VÀ "Đang xử lý"

2. **Giọng điệu - TỰ NHIÊN NHƯ NGƯỜI THẬT (⚠️ QUAN TRỌNG NHẤT)**:
   - **TRÁNH ngôn ngữ cứng nhắc kiểu bot**: KHÔNG dùng "Bước 1, Bước 2, Bước 3" TRỪ KHI ngữ cảnh GỐC có sẵn
   - **SỬ DỤNG chuyển tiếp tự nhiên**: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
   - **THÊM động viên và cảm xúc**: "đừng lo nhé", "rất đơn giản", "dễ dàng thôi", "chỉ cần..."
   - **DÙNG ngôn ngữ thân mật**: "bạn", "mình", "nhé", "nha"
   - **NÓI như đang tư vấn trực tiếp**: Mượt mà, thấu hiểu, không cứng nhắc

   - **NẾU NGỮ CẢNH có "Bước 1, 2, 3"** → VIẾT LẠI tự nhiên hơn:
     * THAY VÌ: "Bước 1: Chọn..., Bước 2: Nhập..., Bước 3: Xác nhận..."
     * VIẾT THÀNH: "Đầu tiên, bạn cần chọn... Tiếp theo, bạn nhập... Sau đó xác nhận... Cuối cùng..."

   - **NẾU NGỮ CẢNH KHÔNG có "Bước"** → Trả lời thông thường, tự nhiên
     * Giải thích ngắn gọn, thân thiện
     * KHÔNG tự ý thêm "Bước 1, 2, 3"

3. **Phần "Lưu ý"**: CHỈ bao gồm nếu nó TRỰC TIẾP liên quan đến câu hỏi được hỏi
4. **Icon/Emoji**: CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp để làm nổi bật thông tin quan trọng
5. **KHÔNG thêm**: Câu mở đầu dài "Chào bạn! Tôi hiểu...", "Câu hỏi liên quan" không cần thiết, hoặc "Lưu ý" từ FAQ khác
6. **⚠️ COMPLETION MESSAGE**: Nếu NGỮ CẢNH chứa thông báo hoàn thành (có ✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN thông báo đó, KHÔNG đổi thành format bước

📋 VÍ DỤ TRẢ LỜI TỰ NHIÊN (CONVERSATIONAL):

**Ví dụ 1: Hủy ví VNPT Money** (NGỮ CẢNH có "Bước 1, 2, 3" → VIẾT LẠI tự nhiên):
```
Để hủy ví VNPT Money, bạn cần làm một vài việc nhé:

Đầu tiên, hãy đảm bảo bạn đã ngắt kết nối với tất cả tài khoản ngân hàng trên ví VNPT Money.

Tiếp theo, nếu ví của bạn còn số dư, bạn nên sử dụng hết hoặc chuyển ra ngân hàng trước nhé. Ngoài ra, nếu có khoản nợ nào, bạn cũng cần thanh toán hết luôn.

Sau khi hoàn tất những bước trên, bạn liên hệ với bộ phận hỗ trợ và cung cấp các thông tin cần thiết để họ xử lý việc hủy ví cho bạn.

⚠️ Lưu ý: Khi ví đã được hủy, bạn sẽ không thể khôi phục lại được nhé.
```

**Ví dụ 2: Rút tiền bị mất phí** (NGỮ CẢNH KHÔNG có "Bước" → Trả lời tự nhiên):
```
Khi bạn rút tiền từ ví VNPT Pay, bạn sẽ bị tính khoản phí theo chính sách của VNPT Pay. Đây là phí dịch vụ chuẩn, không phải lỗi nhé.

Nếu bạn muốn biết rõ hơn về mức phí, bạn có thể kiểm tra trong phần "Biểu phí" trên ứng dụng hoặc liên hệ Hotline 1900 8198 để được tư vấn chi tiết hơn.
```

**Ví dụ 3: Nạp tiền từ ngân hàng liên kết** (NGỮ CẢNH có "Bước" → VIẾT LẠI tự nhiên):
```
Nạp tiền từ ngân hàng liên kết rất đơn giản thôi bạn:

Đầu tiên, bạn chọn "Nạp tiền" trên màn hình chính.

Tiếp theo, nhập số tiền bạn muốn nạp vào, rồi ấn "Xác nhận".

Sau đó, hệ thống sẽ gửi mã OTP đến số điện thoại của bạn. Bạn chỉ cần nhập mã OTP này để hoàn tất nạp tiền là xong!

💡 Tiền sẽ được chuyển vào ví của bạn ngay lập tức sau khi xác nhận thành công.
```

**Completion message** (đã hoàn thành TẤT CẢ các bước - GIỮ NGUYÊN):
```
✅ Bạn đã hoàn thành tất cả 5 bước!

Nếu bạn vẫn gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
```
(Lưu ý: GIỮ NGUYÊN toàn bộ completion message, KHÔNG format lại)

⚠️ CRITICAL - QUY TẮC VIẾT:
- DÙNG chuyển tiếp tự nhiên: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
- TRÁNH "Bước 1, Bước 2, Bước 3" trừ khi NGỮ CẢNH gốc BẮT BUỘC phải có
- THÊM động viên: "rất đơn giản thôi", "đừng lo nhé", "dễ dàng", "chỉ cần..."
- DÙNG ngôn ngữ thân mật: "bạn", "nhé", "nha", "của bạn"
- MỖI đoạn XUỐNG DÒNG để dễ đọc (mỗi dòng tối đa 80-100 ký tự)
- GIỮ khoảng trắng giữa các phần để thoáng
- CHỈ bao gồm "Lưu ý" nếu TRỰC TIẾP liên quan đến câu hỏi
- Nếu là COMPLETION MESSAGE: GIỮ NGUYÊN, không format lại

{continuation_instruction}📚 NGỮ CẢNH (Độ tin cậy: {confidence:.0%}):
{context}

❓ CÂU HỎI:
"{user_message}"

💬 TRẢ LỜI (format dễ đọc như ví dụ - mỗi bước/bullet xuống dòng):
"""

        return prompt

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            # System message with formatting instructions
            system_message = """Bạn là VNPT Assistant - trợ lý ảo của VNPT Money, nói chuyện TỰ NHIÊN như một người tư vấn viên thân thiện.

NHIỆM VỤ CHÍNH:
- Trả lời dựa trên thông tin từ NGỮ CẢNH
- Viết theo phong cách TỰ NHIÊN, THÂN THIỆN như đang tư vấn 1-1 cho khách hàng
- Format DỄ ĐỌC: Mỗi dòng tối đa 80-100 ký tự
- KHÔNG bịa đặt thông tin

QUY TẮC VIẾT TỰ NHIÊN (⚠️ QUAN TRỌNG NHẤT):
- TRÁNH ngôn ngữ cứng nhắc kiểu bot: KHÔNG dùng "Bước 1, Bước 2, Bước 3" TRỪ KHI ngữ cảnh GỐC có sẵn
- SỬ DỤNG chuyển tiếp tự nhiên: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
- THÊM động viên và cảm xúc: "đừng lo nhé", "rất đơn giản thôi", "dễ dàng", "chỉ cần..."
- DÙNG ngôn ngữ thân mật: "bạn", "mình", "nhé", "nha", "của bạn"
- NÓI như đang tư vấn trực tiếp: Mượt mà, thấu hiểu, không cứng nhắc

VÍ DỤ TỐT (TỰ NHIÊN):
❌ TRÁNH: "Bước 1: Đảm bảo không còn liên kết. Bước 2: Sử dụng hết số dư. Bước 3: Thanh toán dư nợ."
✅ VIẾT: "Đầu tiên, hãy đảm bảo bạn đã ngắt kết nối với tất cả tài khoản ngân hàng. Tiếp theo, nếu ví còn số dư, bạn nên sử dụng hết hoặc chuyển ra ngân hàng trước nhé."

FORMAT:
- MỖI đoạn XUỐNG DÒNG để dễ đọc (mỗi dòng tối đa 80-100 ký tự)
- KHÔNG dùng bullet points (•)
- GIỮ khoảng trắng giữa các đoạn để thoáng
- CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp
- CHỈ bao gồm "Lưu ý" nếu TRỰC TIẾP liên quan đến câu hỏi
- KHÔNG thêm: "Chào bạn", "Câu hỏi liên quan", hoặc "Lưu ý" từ FAQ không liên quan
- ⚠️ COMPLETION MESSAGE: Nếu NGỮ CẢNH có thông báo hoàn thành (✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN toàn bộ, KHÔNG format lại
"""

            # Call OpenAI API
            response = self.llm_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )

            answer = response.choices[0].message.content.strip()

            # Post-process to improve formatting
            answer = self._format_answer_for_readability(answer)

            return answer

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _call_vllm(self, prompt: str) -> str:
        """Call vLLM server (OpenAI-compatible API)"""
        try:
            # System message with formatting instructions (same as OpenAI)
            system_message = """Bạn là VNPT Assistant - trợ lý ảo của VNPT Money, nói chuyện TỰ NHIÊN như một người tư vấn viên thân thiện.

NHIỆM VỤ CHÍNH:
- Trả lời dựa trên thông tin từ NGỮ CẢNH
- Viết theo phong cách TỰ NHIÊN, THÂN THIỆN như đang tư vấn 1-1 cho khách hàng
- Format DỄ ĐỌC: Mỗi dòng tối đa 80-100 ký tự
- KHÔNG bịa đặt thông tin

QUY TẮC VIẾT TỰ NHIÊN:
- TRÁNH ngôn ngữ cứng nhắc kiểu bot: KHÔNG dùng "Bước 1, Bước 2, Bước 3" TRỪ KHI ngữ cảnh GỐC có sẵn
- SỬ DỤNG chuyển tiếp tự nhiên: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
- THÊM động viên và cảm xúc: "đừng lo nhé", "rất đơn giản thôi", "dễ dàng", "chỉ cần..."
- DÙNG ngôn ngữ thân mật: "bạn", "mình", "nhé", "nha", "của bạn"

FORMAT:
- MỖI đoạn XUỐNG DÒNG để dễ đọc
- GIỮ khoảng trắng giữa các đoạn để thoáng
- CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp
"""

            # Call vLLM server (OpenAI-compatible)
            response = self.llm_client.chat.completions.create(
                model=config.VLLM_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )

            answer = response.choices[0].message.content.strip()

            # Post-process to improve formatting
            answer = self._format_answer_for_readability(answer)

            return answer

        except Exception as e:
            logger.error(f"vLLM API error: {e}")
            raise

    def _has_multiple_cases(self, answer: str) -> bool:
        """
        Check if answer contains multiple cases/scenarios that should ALL be included.
        Used for TROUBLESHOOT intent to prevent LLM from filtering cases.
        """
        import re
        answer_lower = answer.lower()

        # Patterns indicating multiple cases
        case_patterns = [
            r'trường\s+hợp.*thành\s+công',
            r'trường\s+hợp.*đang\s+xử\s+lý',
            r'trường\s+hợp.*thất\s+bại',
            r'nếu\s+trạng\s+thái.*thành\s+công',
            r'nếu\s+trạng\s+thái.*đang\s+xử\s+lý',
            r'trạng\s+thái\s+là\s+["\']?thành\s+công',
            r'trạng\s+thái\s+là\s+["\']?đang\s+xử\s+lý',
        ]

        case_count = 0
        for pattern in case_patterns:
            if re.search(pattern, answer_lower):
                case_count += 1

        # If 2+ case patterns found, this is a multi-case answer
        return case_count >= 2

    def _format_answer_for_readability(self, answer: str) -> str:
        """
        Post-process answer to enforce better formatting:
        - Break long lines with comma-separated actions
        - Add spacing between steps
        """
        import re

        lines = answer.split('\n')
        formatted_lines = []

        for line in lines:
            # Check if this is a step line (Bước X: ...)
            step_match = re.match(r'(Bước\s+\d+:\s*)(.+)', line)

            if step_match:
                step_label = step_match.group(1)  # "Bước 1: "
                step_content = step_match.group(2)  # The actual content

                # If content has multiple comma-separated clauses and is long (>80 chars)
                # OR has 3+ commas (lots of actions)
                comma_count = step_content.count(',')

                if comma_count >= 2 or (comma_count >= 1 and len(step_content) > 80):
                    # Split by comma
                    parts = [p.strip() for p in step_content.split(',')]

                    # First part goes on same line as "Bước X:"
                    formatted_lines.append(f"{step_label}{parts[0]}")

                    # Rest go on separate lines
                    for part in parts[1:]:
                        if part:  # Skip empty parts
                            # Capitalize if starts with lowercase
                            formatted_part = part[0].upper() + part[1:] if part and part[0].islower() else part
                            formatted_lines.append(formatted_part)

                    # Add blank line after step for spacing
                    formatted_lines.append('')
                else:
                    # Step is short enough, keep as is
                    formatted_lines.append(line)
                    # Add blank line after step for spacing
                    if len(step_content) > 0:
                        formatted_lines.append('')
            else:
                # Not a step line, keep as is
                formatted_lines.append(line)

        # Remove trailing blank lines
        while formatted_lines and not formatted_lines[-1].strip():
            formatted_lines.pop()

        return '\n'.join(formatted_lines)

    def _generate_template_response(self, rag_result: Dict) -> str:
        """Generate template response without LLM"""

        if rag_result["status"] != "success":
            return """Xin lỗi, tôi chưa tìm thấy thông tin phù hợp với câu hỏi của bạn trong cơ sở dữ liệu.

Để được hỗ trợ tốt hơn, bạn có thể:
📞 Gọi Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
🌐 Truy cập: https://vnptpay.vn

Chúng tôi luôn sẵn sàng hỗ trợ bạn!"""

        # Extract information
        answer = rag_result.get("answer", "")
        alternative_actions = rag_result.get("alternative_actions", [])
        related_questions = rag_result.get("related_questions", [])
        related_entities = rag_result.get("related_entities", {})
        confidence = rag_result.get("confidence", 0)

        # Build response
        response_parts = []

        # Main answer with confidence indicator
        if confidence >= 0.8:
            response_parts.append(f"{answer}")
        else:
            response_parts.append(f"Dựa trên thông tin tôi tìm được:\n\n{answer}")

        # Alternative actions
        if alternative_actions:
            response_parts.append("\n💡 **Phương án thay thế:**")
            for i, alt in enumerate(alternative_actions, 1):
                response_parts.append(f"{i}. {alt['action']}: {alt['reason']}")

        # Additional info from entities (ENRICHED)
        if related_entities:
            notes = []

            # ENRICHED: Errors with solution
            if related_entities.get("errors"):
                errors = related_entities['errors']
                for err in errors:
                    if isinstance(err, dict) and err.get('solution'):
                        notes.append(f"⚠️ {err.get('name', 'Lỗi')}: {err['solution']}")
                    elif isinstance(err, dict):
                        notes.append(f"⚠️ Lỗi: {err.get('name', '')}")
                    else:
                        notes.append(f"⚠️ Lỗi: {err}")

            if related_entities.get("features"):
                notes.append(f"✨ Tính năng: {', '.join(related_entities['features'])}")

            # ENRICHED: Contact channels
            if related_entities.get("contact_channels"):
                contacts = related_entities['contact_channels']
                for contact in contacts:
                    if isinstance(contact, dict):
                        phone = contact.get('phone', '')
                        desc = contact.get('description', '')
                        if phone:
                            notes.append(f"📞 Liên hệ: {contact.get('name', '')} - {phone}")
                        elif desc:
                            notes.append(f"📞 {desc}")

            # NEW: Useful links
            if related_entities.get("useful_links"):
                links = related_entities['useful_links']
                for link in links:
                    if isinstance(link, dict) and link.get('url'):
                        notes.append(f"🔗 {link.get('name', 'Link')}: {link['url']}")

            if notes:
                response_parts.append("\n" + "\n".join(notes))

        # Related questions
        if related_questions:
            response_parts.append("\n❓ **Bạn có thể quan tâm:**")
            for i, rq in enumerate(related_questions[:3], 1):
                response_parts.append(f"{i}. {rq['question']}")

        # Footer
        response_parts.append("\n---")
        response_parts.append("Nếu cần hỗ trợ thêm, vui lòng liên hệ Hotline: 1900 8198")

        return "\n".join(response_parts)

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history

    def clear_history(self):
        """Clear conversation history and context"""
        self.conversation_history = []
        self.context_manager.clear_context()
        logger.info("Conversation history and context cleared")

    def get_chat_statistics(self) -> Dict:
        """Get chatbot statistics with context info"""
        context_summary = self.context_manager.get_summary()
        return {
            "total_conversations": len(self.conversation_history),
            "llm_enabled": self.llm is not None,
            "llm_provider": config.LLM_PROVIDER,
            "cache_size": len(self.rag_engine.cache),
            "context_turns": context_summary.get("num_turns", 0),
            "current_topic": context_summary.get("current_topic"),
            "has_active_context": context_summary.get("has_active_context", False)
        }


# ============================================
# INTERACTIVE CHAT
# ============================================

def interactive_chat():
    """Run interactive chatbot session"""
    print("=" * 60)
    print("VNPT Money GraphRAG Chatbot")
    print("=" * 60)
    print("Gõ 'exit' hoặc 'quit' để thoát")
    print("Gõ 'clear' để xóa lịch sử hội thoại")
    print("Gõ 'stats' để xem thống kê")
    print("=" * 60)

    chatbot = GraphRAGChatbot()

    while True:
        try:
            user_input = input("\n\nBạn: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'thoát']:
                print("\nCảm ơn bạn đã sử dụng VNPT Money Chatbot. Hẹn gặp lại!")
                break

            if user_input.lower() == 'clear':
                chatbot.clear_history()
                print("\nĐã xóa lịch sử hội thoại.")
                continue

            if user_input.lower() == 'stats':
                stats = chatbot.get_chat_statistics()
                print(f"\nThống kê:")
                print(f"  - Số lượt hội thoại: {stats['total_conversations']}")
                print(f"  - LLM: {stats['llm_provider']} ({'Enabled' if stats['llm_enabled'] else 'Disabled'})")
                print(f"  - Cache size: {stats['cache_size']}")
                continue

            # Get response
            response = chatbot.chat(user_input)

            print(f"\nVNPT Money Bot: {response}")

        except KeyboardInterrupt:
            print("\n\nCảm ơn bạn đã sử dụng VNPT Money Chatbot. Hẹn gặp lại!")
            break
        except Exception as e:
            logger.error(f"Error in chat loop: {e}")
            print(f"\nXin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.")


if __name__ == "__main__":
    interactive_chat()
