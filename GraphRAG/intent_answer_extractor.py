# -*- coding: utf-8 -*-
"""
Intent-Based Answer Extractor
Extracts specific information from FAQ answers based on user intent.

This solves the core problem: Entity nodes are used for FILTERING but not for COMPOSING answers.
Now we use LLM to extract ONLY the relevant information based on detected intent.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from openai import OpenAI, DefaultHttpxClient
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentAnswerExtractor:
    """
    Extracts specific information from FAQ answers based on user intent.

    Instead of returning the FULL FAQ answer, this extracts only:
    - FEE intent -> Extract fee information only
    - LIMIT intent -> Extract limit/quota information only
    - TIME intent -> Extract time/duration information only
    - HOW_TO intent -> Extract steps for the specific method asked
    - TROUBLESHOOT intent -> Extract solution for the specific error
    - COMPARISON intent -> Extract all options for comparison
    """

    def __init__(self):
        """Initialize the extractor with LLM client (OpenAI or vLLM)"""
        if config.LLM_PROVIDER == "vllm":
            # vLLM with OpenAI-compatible API
            http_client = DefaultHttpxClient(trust_env=False, timeout=config.VLLM_TIMEOUT)
            self.client = OpenAI(
                api_key=config.VLLM_API_KEY,
                base_url=config.VLLM_API_BASE,
                http_client=http_client,
            )
            self.model = config.VLLM_MODEL
        else:
            # OpenAI
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = config.LLM_MODEL

        # Intent-specific extraction prompts
        self.extraction_prompts = {
            "FEE": self._get_fee_prompt,
            "LIMIT": self._get_limit_prompt,
            "TIME": self._get_time_prompt,
            "HOW_TO": self._get_howto_prompt,
            "TROUBLESHOOT": self._get_troubleshoot_prompt,
            "COMPARISON": self._get_comparison_prompt,
            "INFO_REQUEST": self._get_info_prompt,
            "STATUS_CHECK": self._get_status_prompt,
        }

        logger.info("IntentAnswerExtractor initialized")

    def extract(
        self,
        faq_answer: str,
        user_query: str,
        intent: str,
        entities: Dict[str, List[str]],
        faq_question: str = ""
    ) -> Dict:
        """
        Extract relevant information from FAQ answer based on intent.

        Args:
            faq_answer: Full FAQ answer text
            user_query: Original user question
            intent: Detected intent (FEE, LIMIT, TIME, HOW_TO, etc.)
            entities: Extracted entities from query
            faq_question: Original FAQ question for context

        Returns:
            Dict with:
            - extracted_answer: The focused answer
            - extraction_type: What was extracted
            - confidence: How confident we are
            - raw_data: Structured data if applicable
        """
        if not faq_answer:
            return {
                "extracted_answer": "",
                "extraction_type": "empty",
                "confidence": 0.0,
                "raw_data": None
            }

        # Get the appropriate prompt builder
        prompt_builder = self.extraction_prompts.get(intent, self._get_info_prompt)

        # Build the extraction prompt
        prompt = prompt_builder(faq_answer, user_query, entities, faq_question)

        try:
            # Call LLM for extraction
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(intent)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for precise extraction
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()

            # Parse the result
            parsed = self._parse_extraction_result(result_text, intent)

            logger.info(f"Intent extraction ({intent}): {len(parsed.get('extracted_answer', ''))} chars")

            return parsed

        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Fallback: return truncated answer
            return {
                "extracted_answer": faq_answer[:500] + "..." if len(faq_answer) > 500 else faq_answer,
                "extraction_type": "fallback",
                "confidence": 0.3,
                "raw_data": None
            }

    def _get_system_prompt(self, intent: str) -> str:
        """Get system prompt based on intent"""
        base = """Bạn là chuyên gia trích xuất thông tin từ tài liệu FAQ của VNPT Money.
Nhiệm vụ: Trích xuất CHÍNH XÁC thông tin được yêu cầu, KHÔNG thêm thông tin khác.

QUY TẮC QUAN TRỌNG:
1. CHỈ trích xuất thông tin liên quan đến câu hỏi
2. KHÔNG bịa thêm thông tin không có trong nguồn
3. Giữ nguyên số liệu, tên riêng chính xác
4. Trả lời ngắn gọn, đúng trọng tâm
5. Nếu không tìm thấy thông tin → trả về "KHÔNG TÌM THẤY"
"""

        intent_specific = {
            "FEE": "\n\nFOCUS: Trích xuất thông tin về PHÍ (số tiền, miễn phí, điều kiện phí)",
            "LIMIT": "\n\nFOCUS: Trích xuất thông tin về HẠN MỨC (tối đa, tối thiểu, theo ngày/tháng)",
            "TIME": "\n\nFOCUS: Trích xuất thông tin về THỜI GIAN (bao lâu, ngay lập tức, ngày làm việc)",
            "HOW_TO": "\n\nFOCUS: Trích xuất CÁC BƯỚC thực hiện cho phương thức cụ thể được hỏi",
            "TROUBLESHOOT": "\n\nFOCUS: Trích xuất GIẢI PHÁP cho lỗi/vấn đề cụ thể",
            "COMPARISON": "\n\nFOCUS: Trích xuất và SO SÁNH các phương thức/tùy chọn",
            "INFO_REQUEST": "\n\nFOCUS: Trích xuất thông tin cụ thể được hỏi",
            "STATUS_CHECK": "\n\nFOCUS: Trích xuất cách kiểm tra trạng thái",
        }

        return base + intent_specific.get(intent, "")

    def _build_entity_context(self, entities: Dict) -> str:
        """Build entity context string from all available entities"""
        context_parts = []

        # Core entities
        if entities.get("Feature"):
            context_parts.append(f"Phương thức: {', '.join(entities['Feature'])}")
        if entities.get("Topic"):
            context_parts.append(f"Chủ đề: {', '.join(entities['Topic'])}")
        if entities.get("Service"):
            context_parts.append(f"Dịch vụ: {', '.join(entities['Service'])}")
        if entities.get("Bank"):
            context_parts.append(f"Ngân hàng: {', '.join(entities['Bank'])}")

        # Intent-specific entities from graph
        if entities.get("fees"):
            context_parts.append(f"Thông tin phí từ hệ thống: {', '.join(entities['fees'])}")
        if entities.get("limits"):
            context_parts.append(f"Thông tin hạn mức từ hệ thống: {', '.join(entities['limits'])}")
        if entities.get("timeframes"):
            context_parts.append(f"Thông tin thời gian từ hệ thống: {', '.join(entities['timeframes'])}")
        if entities.get("statuses"):
            context_parts.append(f"Trạng thái: {', '.join(entities['statuses'])}")
        if entities.get("errors"):
            context_parts.append(f"Lỗi liên quan: {', '.join(entities['errors'])}")
        if entities.get("actions"):
            context_parts.append(f"Hành động: {', '.join(entities['actions'][:3])}")  # Limit to 3
        if entities.get("requirements"):
            context_parts.append(f"Yêu cầu: {', '.join(entities['requirements'])}")
        if entities.get("contact_channels"):
            context_parts.append(f"Kênh liên hệ: {', '.join(entities['contact_channels'])}")

        return "\n".join(context_parts) if context_parts else ""

    def _get_fee_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for FEE extraction"""
        entity_context = self._build_entity_context(entities)

        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}

THÔNG TIN BỔ SUNG TỪ HỆ THỐNG:
{entity_context if entity_context else "Không có thông tin bổ sung"}

YÊU CẦU: Trích xuất thông tin PHÍ cho câu hỏi trên.

FORMAT TRẢ LỜI:
{{
  "fee_amount": "<số tiền hoặc 'Miễn phí'>",
  "fee_description": "<mô tả chi tiết>",
  "conditions": "<điều kiện áp dụng nếu có>",
  "answer": "<câu trả lời hoàn chỉnh về phí>"
}}"""

    def _get_limit_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for LIMIT extraction"""
        entity_context = self._build_entity_context(entities)

        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}

THÔNG TIN BỔ SUNG TỪ HỆ THỐNG:
{entity_context if entity_context else "Không có thông tin bổ sung"}

YÊU CẦU: Trích xuất thông tin HẠN MỨC cho câu hỏi trên.

FORMAT TRẢ LỜI:
{{
  "min_amount": "<số tiền tối thiểu>",
  "max_amount": "<số tiền tối đa>",
  "period": "<theo ngày/tháng/giao dịch>",
  "conditions": "<điều kiện áp dụng>",
  "answer": "<câu trả lời hoàn chỉnh về hạn mức>"
}}"""

    def _get_time_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for TIME extraction"""
        entity_context = self._build_entity_context(entities)

        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}

THÔNG TIN BỔ SUNG TỪ HỆ THỐNG:
{entity_context if entity_context else "Không có thông tin bổ sung"}

YÊU CẦU: Trích xuất thông tin THỜI GIAN cho câu hỏi trên.

FORMAT TRẢ LỜI:
{{
  "duration": "<thời gian xử lý>",
  "conditions": "<điều kiện ảnh hưởng thời gian>",
  "answer": "<câu trả lời hoàn chỉnh về thời gian>"
}}"""

    def _get_howto_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for HOW_TO extraction"""
        features = entities.get("Feature", [])
        topics = entities.get("Topic", [])

        # Determine which method user is asking about
        method_hint = ""
        if features:
            method_hint = f"Người dùng hỏi về phương thức: {', '.join(features)}"

        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}
Chủ đề: {', '.join(topics) if topics else 'không xác định'}
{method_hint}

YÊU CẦU:
1. Nếu tài liệu có NHIỀU phương thức, CHỈ trích xuất các bước cho phương thức được hỏi
2. Nếu không rõ phương thức, trích xuất phương thức phổ biến nhất
3. Giữ nguyên thứ tự các bước

FORMAT TRẢ LỜI:
{{
  "method_name": "<tên phương thức>",
  "steps": [
    "Bước 1: ...",
    "Bước 2: ...",
    "..."
  ],
  "notes": "<lưu ý quan trọng nếu có>",
  "answer": "<câu trả lời hoàn chỉnh với các bước>"
}}"""

    def _get_troubleshoot_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for TROUBLESHOOT extraction"""
        errors = entities.get("Error", [])
        statuses = entities.get("Status", [])

        error_context = f"Lỗi được đề cập: {', '.join(errors)}" if errors else ""
        status_context = f"Trạng thái: {', '.join(statuses)}" if statuses else ""

        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}
{error_context}
{status_context}

YÊU CẦU:
1. Xác định vấn đề/lỗi người dùng gặp phải
2. Trích xuất GIẢI PHÁP cụ thể cho vấn đề đó
3. Nếu có nhiều trường hợp (đã nhận tiền/chưa nhận tiền), chọn đúng trường hợp

FORMAT TRẢ LỜI:
{{
  "problem": "<mô tả vấn đề>",
  "solution_steps": [
    "Bước 1: ...",
    "Bước 2: ...",
    "..."
  ],
  "contact_info": "<thông tin liên hệ nếu cần>",
  "answer": "<câu trả lời hoàn chỉnh về cách xử lý>"
}}"""

    def _get_comparison_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for COMPARISON extraction"""
        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}

YÊU CẦU: Trích xuất và so sánh các phương thức/tùy chọn có trong tài liệu.

FORMAT TRẢ LỜI:
{{
  "options": [
    {{
      "name": "<tên phương thức 1>",
      "fee": "<phí>",
      "limit": "<hạn mức>",
      "time": "<thời gian>",
      "pros": "<ưu điểm>",
      "cons": "<nhược điểm>"
    }},
    ...
  ],
  "recommendation": "<khuyến nghị nếu có>",
  "answer": "<câu trả lời so sánh hoàn chỉnh>"
}}"""

    def _get_info_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for general INFO_REQUEST extraction"""
        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI GỐC FAQ: {faq_question}

CÂU HỎI NGƯỜI DÙNG: {user_query}

YÊU CẦU: Trích xuất thông tin trả lời CHÍNH XÁC cho câu hỏi người dùng.

FORMAT TRẢ LỜI:
{{
  "answer": "<câu trả lời trực tiếp, ngắn gọn>",
  "additional_info": "<thông tin bổ sung nếu cần>"
}}"""

    def _get_status_prompt(
        self,
        faq_answer: str,
        user_query: str,
        entities: Dict,
        faq_question: str
    ) -> str:
        """Build prompt for STATUS_CHECK extraction"""
        return f"""NGUỒN TÀI LIỆU:
{faq_answer}

CÂU HỎI NGƯỜI DÙNG: {user_query}

YÊU CẦU: Trích xuất cách kiểm tra trạng thái giao dịch/tài khoản.

FORMAT TRẢ LỜI:
{{
  "check_steps": [
    "Bước 1: ...",
    "Bước 2: ...",
    "..."
  ],
  "status_meanings": "<giải thích các trạng thái nếu có>",
  "answer": "<câu trả lời hoàn chỉnh về cách kiểm tra>"
}}"""

    def _parse_extraction_result(self, result_text: str, intent: str) -> Dict:
        """Parse the LLM extraction result"""
        try:
            # Try to parse as JSON
            # Find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                data = json.loads(json_match.group())

                # Extract the answer field
                answer = data.get("answer", "")
                if not answer:
                    # Try to construct answer from other fields
                    answer = self._construct_answer_from_data(data, intent)

                return {
                    "extracted_answer": answer,
                    "extraction_type": intent.lower(),
                    "confidence": 0.9,
                    "raw_data": data
                }
            else:
                # No JSON found, use the text directly
                return {
                    "extracted_answer": result_text,
                    "extraction_type": intent.lower(),
                    "confidence": 0.7,
                    "raw_data": None
                }

        except json.JSONDecodeError:
            # JSON parsing failed, use raw text
            return {
                "extracted_answer": result_text,
                "extraction_type": intent.lower(),
                "confidence": 0.6,
                "raw_data": None
            }

    def _construct_answer_from_data(self, data: Dict, intent: str) -> str:
        """Construct answer from structured data if 'answer' field is missing"""
        if intent == "FEE":
            fee = data.get("fee_amount", "")
            desc = data.get("fee_description", "")
            return f"Phí: {fee}. {desc}".strip()

        elif intent == "LIMIT":
            min_amt = data.get("min_amount", "")
            max_amt = data.get("max_amount", "")
            period = data.get("period", "")
            return f"Hạn mức: {min_amt} - {max_amt} ({period})".strip()

        elif intent == "TIME":
            duration = data.get("duration", "")
            return f"Thời gian: {duration}".strip()

        elif intent == "HOW_TO":
            steps = data.get("steps", [])
            if steps:
                return "\n".join(steps)
            return ""

        elif intent == "TROUBLESHOOT":
            steps = data.get("solution_steps", [])
            if steps:
                return "\n".join(steps)
            return ""

        return ""


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    extractor = IntentAnswerExtractor()

    # Test case: FEE extraction
    test_faq = """Có 2 cách nạp tiền vào VNPT Money:

1. Nạp tiền từ ngân hàng liên kết:
   - Bước 1: Mở ứng dụng VNPT Money
   - Bước 2: Chọn "Nạp tiền"
   - Bước 3: Chọn ngân hàng liên kết
   - Bước 4: Nhập số tiền
   - Bước 5: Xác nhận OTP
   - Phí: Miễn phí
   - Hạn mức: 50 triệu/ngày
   - Thời gian: Ngay lập tức

2. Nạp tiền qua chuyển khoản ngân hàng:
   - Bước 1: Mở app ngân hàng
   - Bước 2: Chuyển khoản đến số tài khoản VNPT Money
   - Bước 3: Nhập nội dung theo hướng dẫn
   - Phí: 3,300 VNĐ/giao dịch
   - Hạn mức: 100 triệu/ngày
   - Thời gian: 1-3 ngày làm việc"""

    # Test FEE intent
    print("=" * 60)
    print("TEST: FEE extraction for 'liên kết ngân hàng'")
    print("=" * 60)

    result = extractor.extract(
        faq_answer=test_faq,
        user_query="Phí nạp tiền từ ngân hàng liên kết là bao nhiêu?",
        intent="FEE",
        entities={"Feature": ["liên kết ngân hàng"], "Topic": ["Nạp tiền"]},
        faq_question="Cách nạp tiền vào VNPT Money?"
    )

    print(f"\nExtracted Answer:\n{result['extracted_answer']}")
    print(f"\nConfidence: {result['confidence']}")
    print(f"Raw Data: {result.get('raw_data')}")
