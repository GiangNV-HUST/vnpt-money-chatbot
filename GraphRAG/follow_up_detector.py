"""
Follow-up Detector - LLM-based detection for conversation continuity
Phát hiện câu hỏi follow-up vs câu hỏi mới hoàn toàn
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import config

# Try to import OpenAI
try:
    from openai import OpenAI, DefaultHttpxClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available for follow-up detection")


@dataclass
class FollowUpResult:
    """Result of follow-up detection"""
    is_follow_up: bool
    confidence: float
    topic: Optional[str]
    context_needed: Optional[str]
    reasoning: Optional[str]
    detection_method: str  # "llm", "rule", "memory_score"


class FollowUpDetector:
    """
    Detects whether a query is a follow-up to previous conversation

    Uses a 3-layer approach:
    1. Rule-based quick check (fast, free)
    2. Memory score threshold (from Mem0 search)
    3. LLM-based detection (accurate, when uncertain)
    """

    def __init__(self):
        """Initialize Follow-up Detector"""
        self.llm_client = None
        self.llm_model = None

        if OPENAI_AVAILABLE:
            try:
                if config.LLM_PROVIDER == "vllm":
                    # vLLM with OpenAI-compatible API
                    http_client = DefaultHttpxClient(trust_env=False, timeout=config.VLLM_TIMEOUT)
                    self.llm_client = OpenAI(
                        api_key=config.VLLM_API_KEY,
                        base_url=config.VLLM_API_BASE,
                        http_client=http_client,
                    )
                    self.llm_model = config.VLLM_MODEL
                elif config.OPENAI_API_KEY:
                    self.llm_client = OpenAI(api_key=config.OPENAI_API_KEY)
                    self.llm_model = getattr(config, 'LLM_MODEL', 'gpt-4o-mini')

                if self.llm_client:
                    logger.info(f"FollowUpDetector initialized with LLM: {self.llm_model}")
            except Exception as e:
                logger.warning(f"FollowUpDetector LLM init failed: {e}")

        if not self.llm_client:
            logger.warning("FollowUpDetector running without LLM support")

        # Rule-based patterns
        self._init_patterns()

    def _init_patterns(self):
        """Initialize rule-based patterns"""

        # Strong follow-up signals (definitely follow-up)
        self.strong_follow_up_patterns = [
            # Conditional follow-up
            r'^nếu\s+(như\s+)?(vậy|thế|trạng\s+thái)',
            r'^(còn\s+)?nếu\s+.{0,30}(thì|thế)\s+(sao|thế\s+nào|làm\s+gì)',
            r'(trường\s+hợp|tình\s+huống)\s+(đó|này|trên)',

            # Continuation signals
            r'^(tiếp\s+theo|bước\s+tiếp)',
            r'^(còn|vậy|thế)\s+(thì|nếu|còn)',
            r'(rồi|xong)\s+(thì\s+)?(sao|làm\s+gì)',

            # Reference to previous context
            r'(giao\s+dịch|trạng\s+thái|trường\s+hợp)\s+(đó|này|trên|ấy)',
            r'(như\s+)?(đã\s+nói|vừa\s+hỏi|ở\s+trên)',

            # Implicit subject (missing topic)
            r'^(thời\s+gian|phí|hạn\s+mức)\s+(là\s+)?bao\s+(lâu|nhiêu)',
            r'^bao\s+(lâu|nhiêu)',

            # Very short follow-up (clearly missing subject)
            r'^còn\s+\w+\s+(thì\s+)?(sao|thế\s+nào)\??$',  # "còn X thì sao?"
        ]

        # Strong new topic signals (definitely NOT follow-up)
        self.new_topic_patterns = [
            # Complete questions with new topic
            r'(làm\s+sao|làm\s+thế\s+nào|cách\s+nào)\s+để\s+.{10,}',
            r'hướng\s+dẫn\s+(tôi|mình|em)\s+.{10,}',
            r'tôi\s+muốn\s+(biết|hỏi)\s+về\s+.{5,}',

            # Explicit new topic keywords
            r'(đăng\s+ký|đăng\s+nhập|liên\s+kết|hủy|xóa)\s+(ví|tài\s+khoản)',
            r'(nạp|rút|chuyển)\s+tiền\s+.{5,}',  # Full new action
        ]

        # Topics to extract
        self.topic_keywords = {
            "chuyển tiền": ["chuyển tiền", "chuyển khoản", "transfer"],
            "nạp tiền": ["nạp tiền", "nạp cước", "top-up", "deposit"],
            "rút tiền": ["rút tiền", "rút", "withdraw"],
            "thanh toán": ["thanh toán", "trả tiền", "payment"],
            "liên kết ngân hàng": ["liên kết", "link", "kết nối ngân hàng"],
            "đăng ký": ["đăng ký", "tạo tài khoản", "register"],
            "ekyc": ["ekyc", "định danh", "xác thực"],
        }

    def detect(self,
               query: str,
               memories: List[Dict] = None,
               previous_qa: Dict = None,
               memory_score_threshold: float = 0.7,
               use_llm: bool = True) -> FollowUpResult:
        """
        Detect if query is a follow-up question

        Args:
            query: Current user query
            memories: List of memories from Mem0 search
            previous_qa: Previous Q&A pair (optional, for context)
            memory_score_threshold: Threshold for memory-based detection
            use_llm: Whether to use LLM for uncertain cases

        Returns:
            FollowUpResult with detection details
        """
        query_lower = query.lower().strip()

        # Layer 1: Rule-based quick check
        rule_result = self._check_rules(query_lower)
        if rule_result is not None:
            return rule_result

        # Layer 2: Memory score check
        if memories:
            memory_result = self._check_memory_score(query_lower, memories, memory_score_threshold)
            if memory_result.confidence >= 0.8:
                # High confidence from memory - trust it
                return memory_result

        # Layer 3: LLM-based detection (for uncertain cases)
        if use_llm and self.llm_client and memories:
            llm_result = self._detect_with_llm(query, memories, previous_qa)
            if llm_result:
                return llm_result

        # Default: Not a follow-up (no context available)
        return FollowUpResult(
            is_follow_up=False,
            confidence=0.5,
            topic=self._extract_topic(query_lower),
            context_needed=None,
            reasoning="No strong signals detected, treating as new query",
            detection_method="default"
        )

    def _check_rules(self, query_lower: str) -> Optional[FollowUpResult]:
        """Layer 1: Rule-based pattern matching"""

        # Check strong follow-up patterns
        for pattern in self.strong_follow_up_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"   Rule: Strong follow-up pattern matched: {pattern}")
                return FollowUpResult(
                    is_follow_up=True,
                    confidence=0.9,
                    topic=None,  # Will be filled from memory
                    context_needed=query_lower,
                    reasoning=f"Matched follow-up pattern: {pattern[:30]}",
                    detection_method="rule"
                )

        # Check strong new topic patterns
        for pattern in self.new_topic_patterns:
            if re.search(pattern, query_lower):
                topic = self._extract_topic(query_lower)
                logger.info(f"   Rule: Strong new topic pattern matched: {pattern}")
                return FollowUpResult(
                    is_follow_up=False,
                    confidence=0.9,
                    topic=topic,
                    context_needed=None,
                    reasoning=f"Matched new topic pattern: {pattern[:30]}",
                    detection_method="rule"
                )

        # No strong signals from rules
        return None

    def _check_memory_score(self,
                            query_lower: str,
                            memories: List[Dict],
                            threshold: float) -> FollowUpResult:
        """Layer 2: Memory score based detection"""

        if not memories:
            return FollowUpResult(
                is_follow_up=False,
                confidence=0.3,
                topic=self._extract_topic(query_lower),
                context_needed=None,
                reasoning="No memories found",
                detection_method="memory_score"
            )

        top_memory = memories[0]
        score = top_memory.get("score", 0)
        metadata = top_memory.get("metadata", {})

        # High score = likely follow-up
        if score >= threshold:
            topic = metadata.get("topic") or self._extract_topic_from_memory(top_memory)

            logger.info(f"   Memory: High score {score:.2f} >= {threshold}, likely follow-up")

            return FollowUpResult(
                is_follow_up=True,
                confidence=min(score, 0.95),  # Cap confidence
                topic=topic,
                context_needed=self._infer_context_needed(query_lower, top_memory),
                reasoning=f"High memory relevance score: {score:.2f}",
                detection_method="memory_score"
            )
        else:
            return FollowUpResult(
                is_follow_up=False,
                confidence=1 - score,  # Low memory score = confident it's new
                topic=self._extract_topic(query_lower),
                context_needed=None,
                reasoning=f"Low memory relevance score: {score:.2f}",
                detection_method="memory_score"
            )

    def _detect_with_llm(self,
                         query: str,
                         memories: List[Dict],
                         previous_qa: Dict = None) -> Optional[FollowUpResult]:
        """Layer 3: LLM-based detection"""

        if not self.llm_client:
            return None

        try:
            # Build context from memories
            memory_context = "\n".join([
                f"- {m.get('memory', '')}" for m in memories[:5]
            ])

            # Build previous Q&A context if available
            prev_context = ""
            if previous_qa:
                prev_context = f"""
Previous Question: {previous_qa.get('question', '')}
Previous Answer: {previous_qa.get('answer', '')[:500]}
"""

            prompt = f"""Bạn là chuyên gia phân tích hội thoại. Hãy xác định xem câu hỏi mới có phải là câu hỏi TIẾP NỐI (follow-up) từ ngữ cảnh trước hay là câu hỏi MỚI hoàn toàn.

{prev_context}

Các thông tin đã lưu từ hội thoại trước:
{memory_context}

Câu hỏi mới: "{query}"

Phân tích:
1. Câu hỏi mới có đề cập đến điều kiện/trạng thái từ ngữ cảnh trước không?
2. Câu hỏi mới có thiếu chủ ngữ/đối tượng (cần context để hiểu) không?
3. Chủ đề câu hỏi mới có liên quan đến ngữ cảnh trước không?

Trả lời bằng JSON:
{{
    "is_follow_up": true/false,
    "confidence": 0.0-1.0,
    "topic": "chủ đề của câu hỏi",
    "context_needed": "thông tin cần từ ngữ cảnh trước (nếu là follow-up)",
    "reasoning": "giải thích ngắn gọn"
}}

Chỉ trả về JSON, không có text khác."""

            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "Bạn là AI phân tích hội thoại, trả lời bằng JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)

            result = json.loads(result_text)

            logger.info(f"   LLM: is_follow_up={result['is_follow_up']}, confidence={result['confidence']:.2f}")

            return FollowUpResult(
                is_follow_up=result.get("is_follow_up", False),
                confidence=result.get("confidence", 0.5),
                topic=result.get("topic"),
                context_needed=result.get("context_needed"),
                reasoning=result.get("reasoning"),
                detection_method="llm"
            )

        except json.JSONDecodeError as e:
            logger.warning(f"LLM response not valid JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM follow-up detection failed: {e}")
            return None

    def _extract_topic(self, query_lower: str) -> Optional[str]:
        """Extract topic from query using keywords"""
        for topic, keywords in self.topic_keywords.items():
            for kw in keywords:
                if kw in query_lower:
                    return topic
        return None

    def _extract_topic_from_memory(self, memory: Dict) -> Optional[str]:
        """Extract topic from memory content"""
        content = memory.get("memory", "").lower()
        for topic, keywords in self.topic_keywords.items():
            for kw in keywords:
                if kw in content:
                    return topic
        return None

    def _infer_context_needed(self, query_lower: str, memory: Dict) -> str:
        """Infer what context is needed from the query"""
        # Common patterns that indicate what's being asked
        if "thời gian" in query_lower or "bao lâu" in query_lower:
            return "thời gian xử lý"
        if "phí" in query_lower or "bao nhiêu" in query_lower:
            return "phí/chi phí"
        if "trạng thái" in query_lower:
            return "thông tin về trạng thái"
        if "đang xử lý" in query_lower:
            return "xử lý khi trạng thái đang xử lý"

        # Default: return the query as context needed
        return query_lower


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Follow-up Detector")
    print("=" * 60)

    detector = FollowUpDetector()

    # Test cases
    test_cases = [
        # Follow-up cases
        {
            "query": "nếu trạng thái đang xử lý thì thời gian xử lý bao lâu?",
            "memories": [
                {"memory": "User chuyển tiền đến ngân hàng", "score": 0.85, "metadata": {"topic": "chuyển tiền"}},
                {"memory": "Có 2 trạng thái: Thành công hoặc Đang xử lý", "score": 0.82, "metadata": {}},
            ],
            "expected": True
        },
        {
            "query": "còn nếu thất bại thì sao?",
            "memories": [
                {"memory": "User hỏi về nạp tiền điện thoại", "score": 0.75, "metadata": {"topic": "nạp tiền"}},
            ],
            "expected": True
        },
        {
            "query": "thời gian là bao lâu?",
            "memories": [
                {"memory": "User rút tiền về ngân hàng", "score": 0.80, "metadata": {"topic": "rút tiền"}},
            ],
            "expected": True
        },

        # New topic cases
        {
            "query": "làm sao để liên kết ngân hàng Vietcombank?",
            "memories": [
                {"memory": "User chuyển tiền đến ngân hàng", "score": 0.40, "metadata": {"topic": "chuyển tiền"}},
            ],
            "expected": False
        },
        {
            "query": "hướng dẫn tôi cách nạp tiền điện thoại",
            "memories": [],
            "expected": False
        },
    ]

    print("\nRunning test cases...\n")

    for i, tc in enumerate(test_cases, 1):
        result = detector.detect(
            query=tc["query"],
            memories=tc["memories"],
            use_llm=True
        )

        status = "✅" if result.is_follow_up == tc["expected"] else "❌"
        print(f"{status} Test {i}: {tc['query'][:50]}...")
        print(f"   Expected: {tc['expected']}, Got: {result.is_follow_up}")
        print(f"   Confidence: {result.confidence:.2f}, Method: {result.detection_method}")
        print(f"   Topic: {result.topic}, Context: {result.context_needed}")
        print(f"   Reasoning: {result.reasoning}")
        print()

    print("=" * 60)
    print("Testing complete!")
