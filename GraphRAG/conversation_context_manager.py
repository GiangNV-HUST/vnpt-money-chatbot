"""
Conversation Context Manager for Multi-turn Dialogues
Tracks conversation state, detects contextual references, and manages step-by-step interactions
NOW WITH LANGCHAIN MEMORY INTEGRATION!
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangChain imports (after logger is defined)
# Note: In LangChain v1.2+, memory classes are deprecated
# We'll use a simpler in-memory approach with LangChain message history
try:
    from langchain_community.chat_message_histories import ChatMessageHistory
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
    logger.info("LangChain available - will use ChatMessageHistory for conversation tracking")
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    logger.warning(f"LangChain not available: {e}. Install with: pip install langchain langchain-openai langchain-community")

import config


class ConversationContextManager:
    """
    Manages conversation context for multi-turn dialogues

    Features:
    - Detects contextual references ("sau khi", "tiếp theo", "bước tiếp theo")
    - Tracks current topic and entities
    - Maintains conversation history
    - Identifies step-based interactions
    """

    def __init__(self, max_history: int = 5, enable_langchain_memory: bool = None):
        """
        Initialize ConversationContextManager

        Args:
            max_history: Maximum number of turns to keep in history
            enable_langchain_memory: Enable LangChain memory (default: from config)
        """
        self.max_history = max_history
        self.conversation_history = []
        self.current_context = {
            "topic": None,
            "entities": {},
            "current_step": None,
            "all_steps": [],
            "completed_steps": [],
            "last_faq_id": None,
            "last_answer": None
        }

        # Initialize LangChain Memory
        self.enable_langchain_memory = enable_langchain_memory if enable_langchain_memory is not None else getattr(config, 'ENABLE_LANGCHAIN_MEMORY', False)
        self.langchain_memory = None

        if self.enable_langchain_memory and LANGCHAIN_AVAILABLE:
            self._initialize_langchain_memory()
        elif self.enable_langchain_memory and not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain memory requested but not available. Falling back to basic memory.")
            self.enable_langchain_memory = False

    def _initialize_langchain_memory(self):
        """
        Initialize LangChain message history and LLM for summarization

        In LangChain v1.2+, we use ChatMessageHistory + custom summarization logic
        """
        try:
            # Initialize LLM for summarization
            self.llm = ChatOpenAI(
                model=getattr(config, 'LLM_MODEL', 'gpt-4o-mini'),
                temperature=0.0,  # Low temperature for consistent summaries
                api_key=getattr(config, 'OPENAI_API_KEY', '')
            )

            # Initialize message history
            self.langchain_memory = ChatMessageHistory()

            # Configuration
            self.memory_type = getattr(config, 'MEMORY_TYPE', 'summary_buffer')
            self.max_token_limit = getattr(config, 'MEMORY_MAX_TOKEN_LIMIT', 2000)
            self.conversation_summary = ""  # Store summary of old messages
            self.summary_message_count = 0  # Track how many messages have been summarized

            logger.info(f"Initialized LangChain ChatMessageHistory with {self.memory_type} mode (max_token_limit={self.max_token_limit})")

        except Exception as e:
            logger.error(f"Failed to initialize LangChain memory: {e}")
            logger.warning("Falling back to basic memory")
            self.enable_langchain_memory = False
            self.langchain_memory = None
            self.llm = None

    def add_turn(self, user_query: str, bot_response: Dict):
        """
        Add a conversation turn to history (both basic and LangChain memory)

        Args:
            user_query: User's query
            bot_response: Bot's response (RAG result)
        """
        # Extract bot's answer text
        bot_answer = bot_response.get("answer", "")

        # Add to LangChain memory if enabled
        if self.enable_langchain_memory and self.langchain_memory:
            try:
                # Add messages to history
                self.langchain_memory.add_user_message(user_query)
                self.langchain_memory.add_ai_message(bot_answer)
                logger.debug("Added turn to LangChain memory")

                # Check if we need to summarize (summary_buffer mode)
                if self.memory_type == "summary_buffer":
                    self._maybe_summarize_old_messages()

            except Exception as e:
                logger.error(f"Failed to save to LangChain memory: {e}")

        # Add to basic history (for backward compatibility)
        turn = {
            "timestamp": datetime.now(),
            "user_query": user_query,
            "bot_response": bot_response,
            "entities": bot_response.get("related_entities", {}),
            "faq_id": bot_response.get("all_results", [{}])[0].get("question_id") if bot_response.get("all_results") else None
        }

        self.conversation_history.append(turn)

        # Keep only last max_history turns
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

        # Update current context
        self._update_context(user_query, bot_response)

    def _maybe_summarize_old_messages(self):
        """
        Summarize old messages if conversation exceeds token limit
        (Implements ConversationSummaryBufferMemory behavior)
        """
        try:
            messages = self.langchain_memory.messages

            # Rough token count estimation (1 token ~ 4 characters for Vietnamese)
            total_chars = sum(len(msg.content) for msg in messages)
            estimated_tokens = total_chars // 4

            # If under limit, no need to summarize
            if estimated_tokens <= self.max_token_limit:
                return

            # Keep last N messages, summarize the rest
            # Keep at least 2 recent exchanges (4 messages)
            keep_recent = min(4, len(messages))
            messages_to_summarize = messages[self.summary_message_count:-keep_recent] if len(messages) > keep_recent else []

            if messages_to_summarize:
                logger.info(f"Summarizing {len(messages_to_summarize)} old messages to save tokens...")

                # Build conversation text
                conv_text = "\n".join([
                    f"{'Khách hàng' if isinstance(msg, HumanMessage) else 'VNPT Assistant'}: {msg.content}"
                    for msg in messages_to_summarize
                ])

                # Ask LLM to summarize
                summary_prompt = f"""Hãy tóm tắt cuộc hội thoại sau đây một cách ngắn gọn, giữ lại các thông tin quan trọng:

{conv_text}

Tóm tắt (bằng tiếng Việt, 2-3 câu):"""

                response = self.llm.invoke(summary_prompt)
                new_summary = response.content.strip()

                # Combine with existing summary if any
                if self.conversation_summary:
                    self.conversation_summary = f"{self.conversation_summary}\n\n{new_summary}"
                else:
                    self.conversation_summary = new_summary

                # Track how many messages we've summarized
                self.summary_message_count = len(messages) - keep_recent

                logger.info(f"Summary updated. Total summarized messages: {self.summary_message_count}")
                logger.debug(f"Summary: {self.conversation_summary[:100]}...")

        except Exception as e:
            logger.error(f"Failed to summarize old messages: {e}")

    def _update_context(self, user_query: str, bot_response: Dict):
        """Update current context based on latest turn"""
        # Update entities (MERGE instead of overwrite to preserve context)
        if bot_response.get("related_entities"):
            # CRITICAL FIX: Merge new entities with existing ones instead of overwriting
            # This preserves topic and other entities from previous turns
            new_entities = bot_response["related_entities"]
            for key, value in new_entities.items():
                if value:  # Only update if new value is not empty
                    self.current_context["entities"][key] = value

        # Update topic (only if present in new response, otherwise keep existing)
        topics = bot_response.get("related_entities", {}).get("topics", [])
        if topics:
            self.current_context["topic"] = topics[0]
        # CRITICAL: If no topics in response, keep existing topic (don't reset to None)

        # Update steps from answer
        answer = bot_response.get("answer", "")
        steps = self._extract_steps_from_answer(answer)
        # CRITICAL: Only update all_steps if this is NOT a continuation response
        # For continuation, we want to keep the original all_steps from the initial answer
        if steps and not bot_response.get("is_continuation"):
            self.current_context["all_steps"] = steps
            logger.info(f"Updated all_steps with {len(steps)} steps from new answer")
        elif steps and bot_response.get("is_continuation"):
            logger.info(f"Skipping all_steps update for continuation response (keeping {len(self.current_context.get('all_steps', []))} original steps)")

        # CRITICAL FIX: Update current_step based on bot response
        # Track the LAST step we showed to the user (for "tiếp tục" queries)
        if bot_response.get("is_continuation"):
            # For continuation, track the last step we just showed
            next_steps = bot_response.get("next_steps", [])
            if next_steps:
                # Get the highest step number from next_steps we just showed
                logger.debug(f"next_steps: {next_steps}")
                max_shown_step = max([s.get("number", 0) for s in next_steps])
                self.current_context["current_step"] = max_shown_step
                logger.info(f"Updated current_step to {max_shown_step} (last step shown in continuation)")
        # IMPORTANT: Do NOT update current_step for initial answers (when showing all steps)
        # Only update when it's a continuation - otherwise user hasn't completed any steps yet

        # Update last FAQ and answer
        # CRITICAL FIX: Use 'faq_id' (not 'question_id') to match Neo4j schema
        if bot_response.get("all_results"):
            top_result = bot_response["all_results"][0]
            self.current_context["last_faq_id"] = top_result.get("faq_id") or top_result.get("question_id")
        else:
            self.current_context["last_faq_id"] = None
        self.current_context["last_answer"] = answer

    def _is_final_completion_step(self, step_text: str) -> bool:
        """
        Check if a step is a final completion/result step (not an action step)

        Args:
            step_text: The step text to check

        Returns:
            True if this is a completion step, False if it's an action step
        """
        step_lower = step_text.lower()

        # STRONG completion keywords - if step starts with these, it's definitely completion
        strong_completion_keywords = [
            "màn hình xác nhận",
            "xác nhận thành công",
            "giao dịch thành công",
            "hoàn tất",
            "hoàn thành",
            "kết thúc",
            "completed",
            "success",
            "finished",
        ]

        # Check if step starts with strong completion keywords
        for keyword in strong_completion_keywords:
            if step_lower.startswith(keyword):
                return True

        # Action verbs that indicate this is an action step
        action_verbs = [
            "nhập", "chọn", "ấn", "bấm", "click", "tại", "vào",
            "kiểm tra", "đợi", "chờ", "nhấn",
            "enter", "select", "click", "tap", "check"
        ]

        has_action = any(verb in step_lower for verb in action_verbs)

        # CRITICAL: If step contains "xác nhận" as verb (action), it's NOT completion
        # e.g., "Xác nhận giao dịch và ấn Chuyển tiền" is ACTION
        # e.g., "Màn hình Xác nhận giao dịch và nhấn Rút tiền" is ACTION
        # but "Màn hình xác nhận thành công" is COMPLETION
        if "xác nhận giao dịch" in step_lower or "xác nhận và" in step_lower:
            has_action = True

        # EARLY CHECK: If step mentions a screen/page but then has action verbs, it's ACTION
        # e.g., "Màn hình X và nhấn Y" is ACTION, not COMPLETION
        # This must be checked BEFORE weak completion keywords
        if step_lower.startswith("màn hình") and has_action:
            return False  # Definitely an action step

        # WEAK completion keywords - need to check for absence of action verbs
        weak_completion_keywords = [
            "thành công",
            "sẽ được xử lý",
            "sẽ nhận được",
            "nhận được kết quả",
            "được xử lý",
            "kết quả trên màn hình",
        ]

        # Check if step contains weak completion keywords
        has_weak_completion = any(keyword in step_lower for keyword in weak_completion_keywords)

        # If has weak completion keywords but NO action verbs, it's a completion step
        if has_weak_completion and not has_action:
            return True

        return False

    def _extract_steps_from_answer(self, answer: str) -> List[Dict]:
        """
        Extract steps from answer text

        Returns:
            List of {step_number, step_text, is_completion_step, completed}
        """
        steps = []

        # Try multiple patterns in order of preference
        patterns = [
            # Pattern 1: "Bước 1:", "Bước 2:", etc.
            r'Bước\s+(\d+):\s*(.+?)(?=Bước\s+\d+:|$)',
            # Pattern 2: "**1. Title**", "**2. Title**", etc. (markdown bold)
            r'\*\*(\d+)\.\s+(.+?)\*\*',
            # Pattern 3: "1. Title", "2. Title", etc. (simple numbered list)
            r'^(\d+)\.\s+(.+?)(?=^\d+\.|$)',
        ]

        for pattern in patterns:
            flags = re.IGNORECASE | re.DOTALL
            if pattern.startswith(r'^'):  # Multiline pattern
                flags |= re.MULTILINE

            matches = list(re.finditer(pattern, answer, flags))

            if matches:
                for match in matches:
                    step_num = int(match.group(1))
                    step_text = match.group(2).strip()

                    # Extract just the first line for title (before newline or bullet)
                    lines = step_text.split('\n')
                    if lines:
                        # Remove leading bullets and whitespace
                        title = re.sub(r'^[\s•\-\*]+', '', lines[0]).strip()
                        step_text_full = step_text
                    else:
                        title = step_text
                        step_text_full = step_text

                    # Check if this is a completion step (result, not action)
                    is_completion = self._is_final_completion_step(title)

                    steps.append({
                        "step_number": step_num,
                        "step_text": step_text_full,
                        "step_title": title,
                        "is_completion_step": is_completion,
                        "completed": False
                    })

                    if is_completion:
                        logger.info(f"   Step {step_num} marked as COMPLETION step: {title[:50]}...")

                logger.info(f"Extracted {len(steps)} steps using pattern: {pattern[:30]}...")
                break  # Use first matching pattern

        return steps

    def _extract_status_from_query(self, user_query: str) -> Optional[str]:
        """
        Extract status result from user query

        Returns:
            Status string like "thành công", "đang xử lý", "thất bại", or None
        """
        query_lower = user_query.lower()

        # Status patterns
        status_patterns = {
            "thành công": [
                r'trạng\s+thái\s+(là|bào|hiển\s+thị|cho\s+biết)\s+thành\s+công',
                r'(kết\s+quả|trạng\s+thái)\s+.{0,20}thành\s+công',
                r'thành\s+công',
            ],
            "đang xử lý": [
                r'trạng\s+thái\s+(là|bào|hiển\s+thị)\s+đang\s+xử\s+lý',
                r'(kết\s+quả|trạng\s+thái)\s+.{0,20}đang\s+xử\s+lý',
                r'đang\s+xử\s+lý',
            ],
            "thất bại": [
                r'trạng\s+thái\s+(là|bào|hiển\s+thị)\s+(thất\s+bại|lỗi)',
                r'(kết\s+quả|trạng\s+thái)\s+.{0,20}(thất\s+bại|lỗi)',
                r'thất\s+bại|lỗi',
            ]
        }

        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return status

        return None

    def _find_step_for_status(self, status_result: str, all_steps: List[Dict]) -> int:
        """
        Find which step to continue to based on status result

        Args:
            status_result: Status like "thành công", "đang xử lý", etc.
            all_steps: All steps from the previous answer

        Returns:
            Step number to continue to (default: 2)
        """
        if not all_steps:
            return 2

        status_lower = status_result.lower()

        # Search for the status in step title or text
        for step in all_steps:
            # Check both title and full text
            step_title = step.get("step_title", "").lower()
            step_text = step.get("step_text", "").lower()

            # Match patterns:
            # - "Nếu trạng thái 'Thành công'"
            # - "Trường hợp trạng thái 'Đang xử lý'"
            # - Direct mention of status in title
            if any([
                f'"{status_lower}"' in step_title,
                f"'{status_lower}'" in step_title,
                status_lower in step_title,
                f'"{status_lower}"' in step_text[:100],  # Check first 100 chars
                f"'{status_lower}'" in step_text[:100],
            ]):
                step_num = step.get("step_number", 2)
                logger.info(f"   Found matching step {step_num} for status '{status_result}' in: {step_title[:50]}")
                return step_num

        # Default: if status is mentioned but no matching step found,
        # assume user completed step 1 (checking status) and go to step 2
        logger.info(f"   No exact match for status '{status_result}', defaulting to step 2")
        return 2

    def _extract_topic_from_text(self, text: str) -> Optional[str]:
        """
        Extract topic/action keywords from text

        Args:
            text: Text to extract topic from

        Returns:
            Topic string or None
        """
        if not text:
            return None

        text_lower = text.lower()

        # Common topics/actions in VNPT services
        # IMPORTANT: More SPECIFIC patterns FIRST (checked in order)
        topic_keywords = [
            # Specific cancellation/service management (check before generic transactions)
            ("hủy nạp tiền tự động", ["hủy dịch vụ nạp tiền tự động", "hủy nạp tiền tự động"]),
            ("hủy thanh toán tự động", ["hủy thanh toán tự động", "hủy dịch vụ thanh toán"]),
            ("đăng ký nạp tiền tự động", ["đăng ký nạp tiền tự động", "thiết lập nạp tự động"]),

            # Specific ticket types (check before generic "mua vé")
            ("mua vé máy bay", ["mua vé máy bay", "đặt vé máy bay"]),
            ("mua vé tàu", ["mua vé tàu", "đặt vé tàu"]),
            ("mua vé vui chơi", ["mua vé vui chơi", "mua vé giải trí"]),

            # Specific deposit/recharge types
            ("nạp tiền điện thoại", ["nạp tiền điện thoại", "nạp cước"]),
            ("mua mã thẻ", ["mua mã thẻ", "mua thẻ cào"]),

            # Specific payment types
            ("thanh toán hóa đơn", ["thanh toán hóa đơn", "thanh toán cước"]),
            ("thanh toán khoản vay", ["thanh toán khoản vay", "thanh toán vay"]),

            # Generic transaction types (fallback)
            ("rút tiền", ["rút tiền", "rút", "withdraw"]),
            ("nạp tiền", ["nạp tiền", "nạp", "deposit", "top-up"]),
            ("chuyển tiền", ["chuyển tiền", "chuyển khoản", "transfer"]),
            ("hoàn tiền", ["hoàn tiền", "hoàn trả", "refund"]),
            ("thanh toán", ["thanh toán", "payment"]),
            ("mua vé", ["mua vé", "đặt vé"]),

            # Account operations
            ("đăng ký", ["đăng ký", "register", "sign up"]),
            ("đăng nhập", ["đăng nhập", "login", "sign in"]),
            ("đổi mật khẩu", ["đổi mật khẩu", "thay đổi mật khẩu", "reset password"]),
            ("quên mật khẩu", ["quên mật khẩu", "forgot password"]),

            # Linking/verification
            ("liên kết", ["liên kết", "link", "kết nối"]),
            ("xác thực", ["xác thực", "verify", "authentication"]),
            ("ekyc", ["ekyc", "e-kyc", "định danh"]),
        ]

        # Check for topic keywords
        for topic_name, keywords in topic_keywords:
            for keyword in keywords:
                if keyword in text_lower:
                    logger.info(f"   Found topic keyword: '{keyword}' → topic: '{topic_name}'")
                    return topic_name

        # Fallback: Try to extract from "chọn mục 'X'" pattern
        # Pattern: "chọn mục 'X'" → "X" is likely the topic
        menu_pattern = re.search(r'chọn\s+mục\s+["\']([^"\']+)["\']', text_lower)
        if menu_pattern:
            menu_item = menu_pattern.group(1)
            logger.info(f"   Extracted topic from menu selection: '{menu_item}'")
            return menu_item

        return None

    def detect_contextual_reference(self, user_query: str, require_history: bool = False) -> Dict:
        """
        Detect if user query contains contextual references

        Args:
            user_query: User's query
            require_history: If True, only return contextual if conversation history exists

        Returns:
            {
                "is_contextual": bool,
                "reference_type": str,  # "step_continuation", "clarification", "follow_up"
                "referenced_step": int or None,
                "context_signals": List[str]
            }
        """
        query_lower = user_query.lower()

        result = {
            "is_contextual": False,
            "reference_type": None,
            "referenced_step": None,
            "context_signals": []
        }

        # Step continuation patterns (STRONG signals - always contextual)
        step_continuation_patterns = [
            # CRITICAL: "N bước đầu", "N bước đầu tiên" - means completed steps 1 through N
            # This must be checked BEFORE single step patterns to avoid mismatching
            r'(\d+)\s+bước\s+đầu(\s+tiên)?',

            # Explicit step number references
            r'sau\s+khi\s+(tôi\s+)?đã\s+(.+?bước\s+(\d+))',
            r'đã\s+(hoàn\s+thành|xong|làm\s+xong)\s+bước\s+(\d+)',
            r'bước\s+(\d+)\s+rồi',
            r'xong\s+bước\s+(\d+)',

            # CRITICAL: "làm đến bước N", "đến bước N", "ở bước N"
            r'(làm|đến|ở|tới)\s+(đến\s+)?bước\s+(\d+)',
            r'nếu\s+(tôi\s+)?(làm|đến)\s+bước\s+(\d+)',

            # Embedded step completion (NEW)
            # Pattern: "... sau khi tôi đã [action from step 1]"
            r'sau\s+khi\s+(tôi\s+)?đã\s+(truy\s+cập|chọn|nhập|xác\s+nhận|hoàn\s+thành|làm)',

            # Status-based continuations (NEW - CRITICAL for "đã vào lịch sử, trạng thái thành công")
            # Detect when user reports status/result of an action
            r'(tôi\s+)?đã\s+(vào|kiểm\s+tra|xem)\s+.+?(trạng\s+thái|kết\s+quả)',
            r'trạng\s+thái\s+(là|bào|hiển\s+thị|cho\s+biết)\s+(thành\s+công|đang\s+xử\s+lý|thất\s+bại)',
            r'(kiểm\s+tra|xem)\s+(thấy|thì)\s+.+?(thành\s+công|đang\s+xử\s+lý|thất\s+bại)',
            r'đã\s+.+?(lịch\s+sử|giao\s+dịch).+?(trạng\s+thái|kết\s+quả)',

            # General continuation signals
            r'sau\s+khi\s+(.+?)(hoàn\s+thành|xong|làm\s+xong)',
            r'(tiếp\s+theo|bước\s+tiếp\s+theo|sau\s+đó)',

            # CRITICAL: "tiếp tục" - very common continuation signal
            r'^tiếp\s+tục$',  # Match exact "tiếp tục" query
            r'(^|\s)(tiếp\s+tục)(\s|$)',  # Match "tiếp tục" with word boundaries

            # CRITICAL: "rồi thì làm gì", "thì làm gì tiếp theo" - strong continuation signals
            r'rồi\s+(thì\s+)?(làm\s+gì|phải\s+làm\s+gì|làm\s+sao)',
            r'(thì|rồi)\s+(làm\s+gì|phải\s+làm\s+gì)\s+(tiếp\s+theo|nữa)',
        ]

        for pattern in step_continuation_patterns:
            match = re.search(pattern, query_lower)
            if match:
                result["is_contextual"] = True
                result["reference_type"] = "step_continuation"
                result["context_signals"].append(match.group(0))

                # SPECIAL CASE: "N bước đầu" means completed steps 1 through N
                # So the referenced_step (last completed step) is N, not 1
                if re.match(r'(\d+)\s+bước\s+đầu', match.group(0)):
                    # Extract N from "N bước đầu"
                    num_match = re.match(r'(\d+)', match.group(0))
                    if num_match:
                        result["referenced_step"] = int(num_match.group(1))
                        logger.info(f"   Detected 'N bước đầu' pattern: completed {result['referenced_step']} steps")
                else:
                    # Try to extract step number from "bước N" pattern
                    step_match = re.search(r'bước\s+(\d+)', match.group(0))
                    if step_match:
                        result["referenced_step"] = int(step_match.group(1))

                break

        # Clarification patterns (WEAK signals - only if NOT a complete question)
        # "làm sao để X" is a complete question, NOT a clarification
        # "làm sao?" or "thế nào?" alone is a clarification
        if not result["is_contextual"]:
            clarification_weak_patterns = [
                r'(ý\s+là\s+sao|nghĩa\s+là\s+gì|tức\s+là)',
                r'(giải\s+thích|cho\s+tôi\s+biết\s+thêm)',
            ]

            for pattern in clarification_weak_patterns:
                if re.search(pattern, query_lower):
                    result["is_contextual"] = True
                    result["reference_type"] = "clarification"
                    result["context_signals"].append(pattern)
                    break

        # Follow-up patterns (WEAK signals - only contextual if short query or starts with them)
        if not result["is_contextual"]:
            follow_up_patterns = [
                r'^(còn|và|thế|vậy|rồi)\s',  # Must be at start and followed by space
                r'(thì\s+sao|thì\s+làm\s+gì)',
                r'(phải\s+làm\s+gì|phải\s+làm\s+sao)',
            ]

            for pattern in follow_up_patterns:
                if re.search(pattern, query_lower):
                    result["is_contextual"] = True
                    result["reference_type"] = "follow_up"
                    result["context_signals"].append(pattern)
                    break

        # If require_history is True, only return contextual if history exists
        if require_history and result["is_contextual"] and not self.conversation_history:
            result["is_contextual"] = False
            result["reference_type"] = None

        return result

    def get_continuation_context(self, user_query: str) -> Optional[Dict]:
        """
        Get context for step continuation queries

        Returns:
            {
                "topic": str,
                "completed_step": int,
                "next_step": int,
                "all_steps": List[Dict],
                "previous_answer": str,
                "entities": Dict,
                "is_embedded": bool  # True if step info is embedded in first query
            }
        """
        # Detect contextual reference
        ref_info = self.detect_contextual_reference(user_query)

        if not ref_info["is_contextual"]:
            return None

        logger.info(f"🔗 Contextual reference detected: {ref_info['reference_type']}")
        logger.info(f"   Signals: {ref_info['context_signals']}")

        # Case 1: Has conversation history - use previous context
        if self.conversation_history:
            # Get last turn
            last_turn = self.conversation_history[-1]

            # Build continuation context
            context = {
                "topic": self.current_context.get("topic"),
                "completed_step": ref_info.get("referenced_step"),
                "next_step": None,
                "all_steps": self.current_context.get("all_steps", []),
                "previous_answer": self.current_context.get("last_answer", ""),
                "entities": self.current_context.get("entities", {}),
                "reference_type": ref_info["reference_type"],
                "is_embedded": False,
                "last_faq_id": self.current_context.get("last_faq_id")  # CRITICAL: Include FAQ ID for correct graph query
            }

            # Calculate next step
            if context["completed_step"]:
                # User explicitly mentioned a step number (e.g., "sau khi hoàn thành 2 bước đầu")
                context["next_step"] = context["completed_step"] + 1
            else:
                # PRIORITY 1: Check if user mentioned a status result
                status_result = self._extract_status_from_query(user_query)
                if status_result and context["all_steps"]:
                    context["completed_step"] = 1
                    context["status_result"] = status_result
                    # Find which step corresponds to this status
                    context["next_step"] = self._find_step_for_status(status_result, context["all_steps"])
                    logger.info(f"   Detected status: {status_result}, jumping to step {context['next_step']}")
                else:
                    # PRIORITY 2: Use current_step from context (for "tiếp tục" queries)
                    # This handles cases where user doesn't mention a step number
                    current_step = self.current_context.get("current_step")
                    if current_step:
                        context["completed_step"] = current_step
                        # CRITICAL: Check if we're at the last step (don't increment beyond total)
                        all_steps = context.get("all_steps", [])
                        total_steps = len(all_steps) if all_steps else 999  # Use high number if unknown

                        if current_step >= total_steps:
                            # Already at or beyond last step - keep as is
                            context["next_step"] = current_step + 1  # Will be handled as completion by engine
                            logger.info(f"   At last step: current_step={current_step}, total={total_steps}, next_step={current_step + 1} (for completion detection)")
                        else:
                            context["next_step"] = current_step + 1
                            logger.info(f"   Using tracked current_step: {current_step}, next_step: {current_step + 1}")
                    else:
                        # Fallback: If no current_step tracked, assume user completed step 1
                        context["completed_step"] = 1
                        context["next_step"] = 2
                        logger.info(f"   No current_step tracked, defaulting to step 1")

            # DISABLED: Keyword-based completion detection is UNRELIABLE
            # Let RAG engine use graph data (total_steps_in_process) for accurate completion detection
            #
            # REASON: Keywords like "sẽ được xử lý", "nhận được kết quả" appear in MIDDLE steps too!
            # Example: "Rút tiền" step 5: "Giao dịch của bạn sẽ được xử lý..." <- NOT completion!
            # The LAST step is determined by graph data, not keywords.
            #
            # if context["all_steps"] and context["next_step"]:
            #     logger.info(f"   Checking if step {context['next_step']} is completion step...")
            #     for step in context["all_steps"]:
            #         if step["step_number"] == context["next_step"]:
            #             is_completion = step.get("is_completion_step", False)
            #             logger.info(f"   Found step {context['next_step']}, is_completion_step={is_completion}")
            #             if is_completion:
            #                 logger.info(f"   ✅ Next step {context['next_step']} is a COMPLETION step, marking as finished")
            #                 context["all_steps_completed"] = True
            #             break
            #     else:
            #         logger.info(f"   ⚠️  Step {context['next_step']} not found in all_steps")

            logger.info(f"   ⚠️  Keyword-based completion detection DISABLED (use graph data instead)")

            logger.info(f"   Completed step: {context['completed_step']}, Next step: {context['next_step']}")

            return context

        # Case 2: NO conversation history BUT has embedded step completion
        # Example: "... sau khi tôi đã truy cập giao diện chính, chọn mục Rút tiền"
        # Example: "... sau khi tôi đã truy cập giao diện chính và chọn mục Rút tiền"
        # Example: "tôi đã vào giao diện chính, chọn mục chuyển tiền rồi thì làm gì nữa"
        # Example: "tôi đã hoàn thành bước 4 rồi thì làm gì tiếp theo?"
        else:
            # First, check if there's an explicit step number from detect_contextual_reference
            ref_info = self.detect_contextual_reference(user_query)
            explicit_step = ref_info.get("referenced_step")

            # Check for embedded step completion patterns
            # Match until "rồi", "thì", or continuation markers
            embedded_patterns = [
                # Pattern 1: "sau khi đã ... rồi/thì"
                r'sau\s+khi\s+(tôi\s+)?đã\s+(.+?)(?=\s+rồi|\s+thì\s+làm|\s+thì\s+phải)',
                # Pattern 2: "tôi đã ... rồi/thì" (without "sau khi")
                r'(^|[.!?]\s+)tôi\s+đã\s+(.+?)(?=\s+rồi|\s+thì\s+làm|\s+thì\s+phải)',
                # Pattern 3: Original pattern (fallback)
                r'sau\s+khi\s+(tôi\s+)?đã\s+(.+?)(?=,|\.|$)',
            ]

            for pattern in embedded_patterns:
                match = re.search(pattern, user_query.lower())
                if match:
                    # Extract completed action from the right group
                    completed_action = None
                    if match.lastindex >= 2:
                        # Get the last capture group which contains the action
                        for i in range(match.lastindex, 0, -1):
                            candidate = match.group(i)
                            # Skip groups that are just punctuation or "tôi"
                            if candidate and candidate.strip() not in ['', '.', '!', '?', 'tôi']:
                                completed_action = candidate
                                break

                    if not completed_action:
                        completed_action = match.group(0)

                    logger.info(f"   Embedded step completion detected: '{completed_action}'")

                    # Use explicit step number if found, otherwise default to 1
                    if explicit_step:
                        completed_step = explicit_step
                        next_step = explicit_step + 1
                        logger.info(f"   Using explicit step number: completed_step={completed_step}")
                    else:
                        completed_step = 1
                        next_step = 2
                        logger.info(f"   No explicit step number, defaulting to completed_step=1")

                    # CRITICAL FIX: Extract topic from completed_action or user_query
                    # Without topic, the bot may query wrong FAQ
                    topic = self._extract_topic_from_text(completed_action) or self._extract_topic_from_text(user_query)
                    if topic:
                        logger.info(f"   Extracted topic from query: '{topic}'")

                    # Build minimal context for embedded query
                    context = {
                        "topic": topic,  # CRITICAL: Include topic!
                        "completed_step": completed_step,
                        "next_step": next_step,
                        "all_steps": [],
                        "previous_answer": "",
                        "entities": {},
                        "reference_type": "embedded_step",
                        "is_embedded": True,
                        "completed_action": completed_action
                    }

                    logger.info(f"   Embedded context: completed_step={completed_step}, next_step={next_step}")

                    return context

            # No embedded step info found
            return None

    def enhance_query_with_context(self, user_query: str) -> Tuple[str, Optional[Dict]]:
        """
        Enhance user query with conversation context

        Returns:
            (enhanced_query, context_info)
        """
        # CRITICAL FIX: Detect topic change BEFORE checking continuation
        # If user asks about completely new topic, reset step context
        current_topic = self._extract_topic_from_text(user_query)
        previous_topic = self.current_context.get("topic")

        # Check if topic has changed significantly
        topic_changed = False
        if current_topic and previous_topic:
            # Different topics = reset context
            if current_topic != previous_topic:
                # But allow some related topics (e.g., "nạp tiền" and "nạp tiền điện thoại")
                if not (current_topic in previous_topic or previous_topic in current_topic):
                    topic_changed = True
                    logger.info(f"🔄 Topic changed: '{previous_topic}' → '{current_topic}' - Resetting step context")
                    # Reset step tracking but keep topic
                    self.current_context["current_step"] = None
                    self.current_context["completed_steps"] = []
                    self.current_context["all_steps"] = []

        # CRITICAL: Also detect "new question" patterns that indicate topic reset
        # Even if topic is similar, certain patterns mean "start over"
        new_question_indicators = [
            r'(làm\s+sao|làm\s+thế\s+nào|như\s+thế\s+nào|cách\s+nào)\s+để',  # "làm sao để X" = new question
            r'hướng\s+dẫn\s+(tôi|mình|em)',  # "hướng dẫn tôi" = new question
            r'tôi\s+muốn\s+(biết|hỏi)',  # "tôi muốn biết" = new question
            r'^(nhưng|nhưng\s+mà)\s+',  # Starts with "nhưng" = problem/new issue
        ]

        is_new_question = any(re.search(pattern, user_query.lower()) for pattern in new_question_indicators)

        # SPECIAL CASE: Troubleshooting after success
        # "thành công nhưng..." or "đã làm xong nhưng..." = NEW issue, not continuation
        is_troubleshooting = bool(re.search(r'(thành\s+công|xong|hoàn\s+thành)\s+(nhưng|nhưng\s+mà|mà)', user_query.lower()))

        if is_troubleshooting:
            logger.info(f"🔧 Troubleshooting query detected - Resetting step context")
            self.current_context["current_step"] = None
            self.current_context["completed_steps"] = []
            self.current_context["all_steps"] = []
            topic_changed = True

        # If topic changed or is new question, don't use continuation context
        if topic_changed or is_new_question:
            logger.info(f"🆕 New question detected (topic_changed={topic_changed}, is_new_question={is_new_question}) - Treating as fresh query")
            return user_query, None

        # Check if this is a contextual query
        continuation_context = self.get_continuation_context(user_query)

        if not continuation_context:
            # Not a contextual query, return as-is
            return user_query, None

        # Build enhanced query
        enhanced_parts = []

        # Add topic context
        if continuation_context["topic"]:
            enhanced_parts.append(continuation_context["topic"])

        # Add status context if present (NEW - helps retrieve correct step)
        if continuation_context.get("status_result"):
            status = continuation_context["status_result"]
            enhanced_parts.append(f"trạng thái {status}")

        # Add step context
        if continuation_context["next_step"]:
            enhanced_parts.append(f"Bước {continuation_context['next_step']}")

        # Add original query
        enhanced_parts.append(user_query)

        enhanced_query = " ".join(enhanced_parts)

        logger.info(f"📝 Enhanced query: '{user_query}' → '{enhanced_query}'")

        return enhanced_query, continuation_context

    def get_memory_summary(self) -> Optional[str]:
        """
        Get conversation summary from LangChain memory

        Returns:
            Summary string or None if not using LangChain memory
        """
        if not self.enable_langchain_memory or not self.langchain_memory:
            return None

        try:
            # Return the summary if available
            if self.conversation_summary:
                return self.conversation_summary

            # Otherwise, return recent messages as string
            messages = self.langchain_memory.messages
            if messages:
                return "\n".join([
                    f"{'Khách hàng' if isinstance(msg, HumanMessage) else 'VNPT Assistant'}: {msg.content}"
                    for msg in messages
                ])

            return "Chưa có cuộc hội thoại"

        except Exception as e:
            logger.error(f"Failed to get memory summary: {e}")
            return None

    def get_full_conversation_history(self) -> str:
        """
        Get full conversation history as formatted string (from LangChain memory if available)
        Includes summary + recent messages in summary_buffer mode

        Returns:
            Formatted conversation history
        """
        if self.enable_langchain_memory and self.langchain_memory:
            try:
                lines = []

                # Add summary if exists
                if self.conversation_summary:
                    lines.append("=== TÓM TẮT CUỘC HỘI THOẠI TRƯỚC ĐÓ ===")
                    lines.append(self.conversation_summary)
                    lines.append("\n=== CÁC TIN NHẮN GẦN ĐÂY ===")

                # Add recent messages
                messages = self.langchain_memory.messages
                for msg in messages:
                    prefix = "🤖 VNPT Assistant" if isinstance(msg, AIMessage) else "👤 Khách hàng"
                    lines.append(f"{prefix}: {msg.content}")

                return "\n\n".join(lines) if lines else "Chưa có cuộc hội thoại"

            except Exception as e:
                logger.error(f"Failed to get conversation history from LangChain: {e}")

        # Fallback to basic history
        lines = []
        for turn in self.conversation_history:
            lines.append(f"👤 Khách hàng: {turn['user_query']}")
            lines.append(f"🤖 VNPT Assistant: {turn['bot_response'].get('answer', '')}")
        return "\n\n".join(lines) if lines else "Chưa có cuộc hội thoại"

    def clear_context(self):
        """Clear conversation context (both basic and LangChain memory)"""
        self.conversation_history = []
        self.current_context = {
            "topic": None,
            "entities": {},
            "current_step": None,
            "all_steps": [],
            "completed_steps": [],
            "last_faq_id": None,
            "last_answer": None
        }

        # Clear LangChain memory if enabled
        if self.enable_langchain_memory and self.langchain_memory:
            try:
                self.langchain_memory.clear()
                self.conversation_summary = ""
                self.summary_message_count = 0
                logger.info("LangChain memory cleared")
            except Exception as e:
                logger.error(f"Failed to clear LangChain memory: {e}")

        logger.info("Conversation context cleared")

    def get_summary(self) -> Dict:
        """Get conversation context summary (including LangChain memory info)"""
        summary = {
            "num_turns": len(self.conversation_history),
            "current_topic": self.current_context.get("topic"),
            "total_steps": len(self.current_context.get("all_steps", [])),
            "completed_steps": len(self.current_context.get("completed_steps", [])),
            "has_active_context": len(self.conversation_history) > 0,
            "langchain_memory_enabled": self.enable_langchain_memory,
        }

        # Add LangChain memory info
        if self.enable_langchain_memory and self.langchain_memory:
            memory_summary = self.get_memory_summary()
            summary["langchain_memory_summary"] = memory_summary
            summary["memory_type"] = self.langchain_memory.__class__.__name__

        return summary


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test conversation context manager
    manager = ConversationContextManager()

    # Test step extraction
    answer_with_steps = """
    Để rút tiền từ ví VNPT Pay về tài khoản ngân hàng, bạn làm theo các bước sau:

    Bước 1: Tại giao diện chính, chọn mục "Rút tiền"
    Bước 2: Nhập số tiền cần nạp và nhấn "Tiếp tục"
    Bước 3: Màn hình Xác nhận giao dịch và nhấn "Rút tiền"
    Bước 4: Màn hình nhập OTP
    Bước 5: Màn hình xác nhận giao dịch Rút tiền thành công
    """

    steps = manager._extract_steps_from_answer(answer_with_steps)
    print("Extracted steps:")
    for step in steps:
        print(f"  Step {step['step_number']}: {step['step_text'][:50]}...")

    # Test contextual reference detection
    test_queries = [
        "Tôi có thể rút tiền từ ví VNPT Pay về tài khoản ngân hàng như thế nào sau khi tôi đã truy cập giao diện chính, chọn mục Rút tiền",
        "sau khi tôi đã hoàn thành bước 1",
        "tiếp theo tôi làm gì",
        "xong bước 2 rồi",
        "làm sao để nạp tiền",  # Not contextual
    ]

    print("\n" + "="*60)
    print("Testing contextual reference detection:")
    print("="*60)

    for query in test_queries:
        ref_info = manager.detect_contextual_reference(query)
        print(f"\nQuery: {query}")
        print(f"  Is contextual: {ref_info['is_contextual']}")
        if ref_info['is_contextual']:
            print(f"  Type: {ref_info['reference_type']}")
            print(f"  Referenced step: {ref_info['referenced_step']}")
            print(f"  Signals: {ref_info['context_signals']}")
