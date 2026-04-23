# -*- coding: utf-8 -*-
"""
Focused Answer Extractor - LLM-First Strategy

Giải quyết vấn đề: User hỏi 1 ý nhưng bot trả lời hết cả FAQ

Chiến lược LLM-First:
1. LLM EXTRACTION (Primary) - Luôn dùng LLM trước cho độ chính xác cao
2. REGEX FALLBACK - Chỉ khi LLM fail hoặc không trả lời được

Lý do: Chi phí LLM không phải vấn đề, ưu tiên chất lượng câu trả lời.

Author: AI Assistant
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnswerSource(Enum):
    """Nguồn của câu trả lời"""
    LLM_EXTRACTED = "llm_extracted"       # LLM extract (primary)
    REGEX_FALLBACK = "regex_fallback"     # Regex fallback khi LLM fail
    CASE_MATCHED = "case_matched"         # Từ Case node được match
    FAQ_FULL = "faq_full"                 # Toàn bộ FAQ (worst case)


@dataclass
class FocusedAnswer:
    """Kết quả trả lời đúng trọng tâm"""
    answer: str
    source: AnswerSource
    confidence: float
    extracted_info: Dict          # Thông tin được extract (phí, hạn mức, etc.)
    filter_applied: str           # Filter đã áp dụng (Feature, Topic, etc.)
    original_length: int          # Độ dài FAQ gốc
    answer_length: int            # Độ dài câu trả lời


class FocusedAnswerExtractor:
    """
    Extractor trả lời đúng trọng tâm - LLM-FIRST STRATEGY

    Nguyên tắc:
    1. Luôn dùng LLM trước vì có khả năng hiểu ngữ cảnh tốt hơn
    2. Regex chỉ dùng khi LLM fail hoặc trả về kết quả không tốt
    3. Không giới hạn chi phí - ưu tiên chất lượng
    """

    def __init__(self, neo4j_connector=None):
        """Initialize extractor"""
        self.connector = neo4j_connector

        # LLM client (lazy init)
        self._llm_client = None

        # Intent → Info type mapping (for LLM prompts)
        self.intent_focus_map = {
            "FEE": "PHÍ (fee) - số tiền cần trả, miễn phí hay có phí",
            "LIMIT": "HẠN MỨC (limit) - số tiền tối đa/tối thiểu",
            "TIME": "THỜI GIAN (time) - bao lâu để xử lý, thời gian chờ",
            "HOW_TO": "CÁC BƯỚC thực hiện (steps) - hướng dẫn từng bước",
            "TROUBLESHOOT": "GIẢI PHÁP KHẮC PHỤC (troubleshooting) - TẤT CẢ các bước xử lý, trường hợp, và thông tin liên hệ hỗ trợ",
            "REQUIREMENT": "ĐIỀU KIỆN/YÊU CẦU - những gì cần chuẩn bị",
            "COMPARISON": "SO SÁNH - sự khác nhau giữa các phương thức",
        }

        # Intents that need FULL information (không cắt ngắn)
        # CRITICAL: Include ALL intents that might have detailed answers
        self.full_info_intents = {"TROUBLESHOOT", "HOW_TO", "REQUIREMENT", "GENERAL"}

    @property
    def llm_client(self):
        """Lazy init LLM client"""
        if self._llm_client is None:
            try:
                from openai import OpenAI, DefaultHttpxClient
                import config

                if config.LLM_PROVIDER == "vllm":
                    # vLLM with OpenAI-compatible API
                    http_client = DefaultHttpxClient(trust_env=False, timeout=config.VLLM_TIMEOUT)
                    self._llm_client = OpenAI(
                        api_key=config.VLLM_API_KEY,
                        base_url=config.VLLM_API_BASE,
                        http_client=http_client,
                    )
                    self._llm_model = config.VLLM_MODEL
                else:
                    # OpenAI
                    self._llm_client = OpenAI(api_key=config.OPENAI_API_KEY)
                    self._llm_model = config.LLM_MODEL
            except Exception as e:
                logger.error(f"Failed to init LLM client: {e}")
        return self._llm_client

    def extract_focused_answer(
        self,
        user_query: str,
        faq_answer: str,
        faq_question: str,
        intent: str,
        entities: Dict,
        graph_entities: Dict = None
    ) -> FocusedAnswer:
        """
        Extract câu trả lời đúng trọng tâm - LLM FIRST

        Args:
            user_query: Câu hỏi của user
            faq_answer: Nội dung FAQ đầy đủ
            faq_question: Câu hỏi FAQ
            intent: Intent đã classify (FEE, LIMIT, TIME, etc.)
            entities: Entities extract từ query
            graph_entities: Entities từ graph (fees, limits, timeframes, etc.)

        Returns:
            FocusedAnswer với câu trả lời đúng trọng tâm
        """
        original_length = len(faq_answer)
        graph_entities = graph_entities or {}

        logger.info(f"🎯 Focused extraction (LLM-First) - Intent: {intent}, Query: {user_query[:50]}...")

        # ============================================
        # LAYER 1: LLM EXTRACTION (PRIMARY)
        # ============================================
        # Luôn thử LLM trước vì có khả năng hiểu ngữ cảnh tốt nhất
        if self.llm_client:
            llm_answer = self._llm_extract_focused(
                user_query, faq_answer, faq_question, intent, entities, graph_entities
            )

            if llm_answer and llm_answer.get("success"):
                logger.info(f"✅ Layer 1 SUCCESS: LLM extraction")
                return FocusedAnswer(
                    answer=llm_answer["answer"],
                    source=AnswerSource.LLM_EXTRACTED,
                    confidence=llm_answer.get("confidence", 0.90),
                    extracted_info=llm_answer.get("info", {}),
                    filter_applied=f"Intent: {intent}, LLM extraction",
                    original_length=original_length,
                    answer_length=len(llm_answer["answer"])
                )

        # ============================================
        # LAYER 2: REGEX FALLBACK
        # ============================================
        # Chỉ dùng khi LLM fail
        logger.info("⚠️ LLM failed, trying regex fallback...")

        if intent in ["FEE", "LIMIT", "TIME"]:
            regex_answer = self._regex_extract_fallback(
                faq_answer, intent, entities, user_query
            )

            if regex_answer:
                logger.info(f"✅ Layer 2 SUCCESS: Regex fallback")
                return FocusedAnswer(
                    answer=regex_answer["answer"],
                    source=AnswerSource.REGEX_FALLBACK,
                    confidence=0.75,  # Lower confidence for regex
                    extracted_info=regex_answer["info"],
                    filter_applied=regex_answer["filter"],
                    original_length=original_length,
                    answer_length=len(regex_answer["answer"])
                )

        # ============================================
        # LAYER 3: CASE-BASED SECTION EXTRACTION
        # ============================================
        # Cho HOW_TO, TROUBLESHOOT - extract section liên quan
        if intent in ["HOW_TO", "TROUBLESHOOT"]:
            case_answer = self._try_case_based_extraction(
                faq_answer, entities, intent, user_query
            )

            if case_answer:
                logger.info(f"✅ Layer 3 SUCCESS: Case-based extraction")
                return FocusedAnswer(
                    answer=case_answer["answer"],
                    source=AnswerSource.CASE_MATCHED,
                    confidence=0.80,
                    extracted_info=case_answer.get("info", {}),
                    filter_applied=case_answer.get("filter", "Case matching"),
                    original_length=original_length,
                    answer_length=len(case_answer["answer"])
                )

        # ============================================
        # FALLBACK: Return full FAQ
        # ============================================
        logger.warning(f"⚠️ All layers failed, using full FAQ answer")

        return FocusedAnswer(
            answer=faq_answer,
            source=AnswerSource.FAQ_FULL,
            confidence=0.5,
            extracted_info={},
            filter_applied="None",
            original_length=original_length,
            answer_length=original_length
        )

    def _llm_extract_focused(
        self,
        user_query: str,
        faq_answer: str,
        faq_question: str,
        intent: str,
        entities: Dict,
        graph_entities: Dict
    ) -> Optional[Dict]:
        """
        Layer 1: LLM extraction với strict constraints

        Đây là layer chính - luôn được thử trước
        """
        if not self.llm_client:
            return None

        try:
            import config

            # Build context từ entities
            entity_context = self._build_entity_context(entities, graph_entities)

            # Get focus instruction for this intent
            focus_instruction = self.intent_focus_map.get(
                intent,
                "thông tin TRẢ LỜI TRỰC TIẾP cho câu hỏi"
            )

            # Kiểm tra xem intent có cần giữ đầy đủ thông tin không
            needs_full_info = intent in self.full_info_intents

            if needs_full_info:
                # TROUBLESHOOT, HOW_TO, REQUIREMENT, GENERAL cần giữ ĐẦY ĐỦ thông tin
                system_prompt = f"""Bạn là AI trích xuất thông tin CHÍNH XÁC cho VNPT Money.

🎯 NHIỆM VỤ: Trích xuất {focus_instruction}

⚠️⚠️⚠️ QUY TẮC CỰC KỲ QUAN TRỌNG - BẮT BUỘC TUÂN THỦ:
1. GIỮ NGUYÊN 100% NỘI DUNG GỐC - KHÔNG ĐƯỢC TÓM TẮT
2. GIỮ NGUYÊN 100% FORMAT GỐC:
   - Nếu gốc dùng "•" thì PHẢI dùng "•"
   - Nếu gốc dùng "-" thì PHẢI dùng "-"
   - Nếu gốc dùng "1.", "2." thì PHẢI dùng "1.", "2."
   - Nếu gốc dùng "Bước 1:", "Bước 2:" thì PHẢI dùng "Bước 1:", "Bước 2:"
3. GIỮ NGUYÊN TẤT CẢ các bước hướng dẫn
4. GIỮ NGUYÊN TẤT CẢ các trường hợp (trạng thái "Thành công", "Đang xử lý", "Thất bại", etc.)
5. GIỮ NGUYÊN SỐ ĐIỆN THOẠI, HOTLINE, URL, thông tin liên hệ
6. GIỮ NGUYÊN thời gian chờ, hạn mức thời gian
7. GIỮ NGUYÊN lưu ý quan trọng
8. KHÔNG THÊM dấu "-" hoặc bullet mới nếu gốc không có
9. KHÔNG THAY ĐỔI cách đánh số bước

🚫 TUYỆT ĐỐI KHÔNG ĐƯỢC:
- Tóm tắt nội dung
- Thay đổi format bullet/numbering
- Cắt bỏ thông tin
- Thêm prefix "-" hoặc "•" nếu gốc không có

✅ CHỈ CÓ THỂ:
- Loại bỏ phần mở đầu không cần thiết (nếu có)
- Loại bỏ câu chào hoặc thông tin hoàn toàn không liên quan (nếu có)

Nếu không chắc chắn, HÃY TRẢ VỀ NGUYÊN VĂN FAQ GỐC.
Nếu không tìm thấy thông tin chính xác, trả lời "KHÔNG_TÌM_THẤY" """
            else:
                # FEE, LIMIT, TIME - có thể trích xuất nhưng GIỮ NGUYÊN FORMAT
                system_prompt = f"""Bạn là AI trích xuất thông tin CHÍNH XÁC cho VNPT Money.

⚠️ QUY TẮC QUAN TRỌNG:
1. GIỮ NGUYÊN 100% FORMAT GỐC:
   - Nếu gốc dùng "•" thì PHẢI dùng "•"
   - Nếu gốc dùng "-" thì PHẢI dùng "-"
   - KHÔNG ĐƯỢC thêm prefix "-" hoặc "•" nếu gốc không có
2. CHỈ trả lời ĐÚNG thông tin được hỏi
3. Nếu FAQ chứa nhiều phương thức/trường hợp, chỉ trả lời phần liên quan
4. GIỮ NGUYÊN URL, hotline nếu có trong phần trả lời
5. Nếu không tìm thấy thông tin chính xác, trả lời "KHÔNG_TÌM_THẤY"

🎯 FOCUS: Trích xuất {focus_instruction}

📋 VÍ DỤ FORMAT ĐÚNG:
- Nếu gốc là: "Phí: Miễn phí" → Trả về: "Phí: Miễn phí" (KHÔNG thêm "-")
- Nếu gốc là: "• Miễn phí" → Trả về: "• Miễn phí" (giữ bullet gốc)
- Nếu gốc là: "Để biết thêm chi tiết, vui lòng tham khảo: https://..." → GIỮ NGUYÊN URL

🚫 KHÔNG ĐƯỢC:
- Thêm prefix "-" hoặc "•" nếu gốc không có
- Thay đổi format bullet/numbering
- Cắt bỏ URL hoặc thông tin liên hệ"""

            user_prompt = f"""CÂU HỎI NGƯỜI DÙNG: {user_query}

THÔNG TIN ĐÃ BIẾT TỪ HỆ THỐNG:
{entity_context}

NỘI DUNG FAQ NGUỒN:
Câu hỏi: {faq_question}
Trả lời: {faq_answer}

YÊU CẦU: Trích xuất và trả lời NGẮN GỌN, ĐÚNG TRỌNG TÂM câu hỏi của người dùng.
Chỉ trả lời phần liên quan, không liệt kê thêm thông tin không được hỏi."""

            # Tăng max_tokens cho TROUBLESHOOT/HOW_TO vì cần giữ nhiều thông tin
            max_tokens = 1000 if needs_full_info else 500

            response = self.llm_client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for focused extraction
                max_tokens=max_tokens
            )

            result_text = response.choices[0].message.content.strip()

            # Check for failure response
            if "KHÔNG_TÌM_THẤY" in result_text:
                logger.info("LLM could not find relevant information")
                return None

            # Validate result - điều chỉnh theo intent
            if needs_full_info:
                # TROUBLESHOOT/HOW_TO: Cần kiểm tra kỹ hơn
                # Phát hiện các câu trả lời chỉ là tiêu đề/mô tả ngắn
                is_title_only = self._is_title_or_summary_response(result_text, faq_answer)

                if is_title_only:
                    logger.warning(f"LLM returned title/summary only instead of detailed answer - REJECTING")
                    return None

                # Kiểm tra độ dài tối thiểu - cần ít nhất 30% nội dung gốc cho HOW_TO
                min_ratio = 0.25 if intent == "HOW_TO" else 0.20
                if len(result_text) < len(faq_answer) * min_ratio:
                    logger.warning(f"LLM answer too short ({len(result_text)} chars, need at least {int(len(faq_answer) * min_ratio)}) - REJECTING")
                    return None

                if result_text and len(result_text) >= 50:
                    reduction = 1 - len(result_text) / len(faq_answer)
                    logger.info(f"Full-info intent ({intent}): keeping detailed answer ({len(result_text)} chars)")
                    return {
                        "success": True,
                        "answer": result_text,
                        "confidence": 0.90,
                        "info": {
                            "method": "llm_extraction_full",
                            "reduction": f"{reduction*100:.0f}%" if reduction > 0 else "0%"
                        }
                    }
                else:
                    logger.warning(f"LLM returned too short answer for {intent}")
                    return None
            else:
                # FEE, LIMIT, TIME: Yêu cầu câu trả lời ngắn gọn
                if result_text and len(result_text) < len(faq_answer) * 0.9:
                    reduction = 1 - len(result_text) / len(faq_answer)
                    return {
                        "success": True,
                        "answer": result_text,
                        "confidence": 0.90 if reduction > 0.3 else 0.80,
                        "info": {
                            "method": "llm_extraction",
                            "reduction": f"{reduction*100:.0f}%"
                        }
                    }
                else:
                    logger.warning("LLM returned answer too long or same as original")
                    return None

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    def _is_title_or_summary_response(self, response: str, original_faq: str) -> bool:
        """
        Phát hiện xem câu trả lời có phải là tiêu đề/mô tả ngắn thay vì nội dung chi tiết

        Args:
            response: Câu trả lời từ LLM
            original_faq: FAQ gốc

        Returns:
            True nếu response chỉ là title/summary
        """
        response_lower = response.lower().strip()
        original_lower = original_faq.lower()

        # Pattern 1: Response bắt đầu bằng "Hướng dẫn" và không có các bước chi tiết
        title_patterns = [
            r'^hướng dẫn\s+(?:cách\s+)?[\w\s]+(?:vnpt\s*money|ví\s+điện\s+tử)?\.?$',
            r'^cách\s+[\w\s]+(?:vnpt\s*money|ví\s+điện\s+tử)?\.?$',
            r'^quy trình\s+[\w\s]+(?:vnpt\s*money)?\.?$',
            r'^các bước\s+(?:để\s+)?[\w\s]+\.?$',
        ]

        for pattern in title_patterns:
            if re.match(pattern, response_lower, re.IGNORECASE):
                # Đây là title pattern - kiểm tra có nội dung chi tiết không
                if len(response) < 150:  # Quá ngắn để là hướng dẫn chi tiết
                    return True

        # Pattern 2: Response không có các bước đánh số hoặc bullet
        has_steps = bool(re.search(r'(?:bước\s*\d+|^\s*\d+[\.\)]\s|^[-•]\s)', response, re.MULTILINE | re.IGNORECASE))
        has_colon_items = bool(re.search(r':\s*\n', response))  # Có items với colon

        # Nếu FAQ gốc có các bước nhưng response không có
        original_has_steps = bool(re.search(r'(?:bước\s*\d+|^\s*\d+[\.\)]\s|^[-•]\s)', original_faq, re.MULTILINE | re.IGNORECASE))

        if original_has_steps and not has_steps and len(response) < 200:
            return True

        # Pattern 3: Response quá ngắn so với FAQ gốc có nhiều bước
        step_count_original = len(re.findall(r'(?:bước\s*\d+|\d+[\.\)])', original_lower, re.IGNORECASE))
        if step_count_original >= 3 and len(response) < 100:
            return True

        # Pattern 4: Chỉ là một câu mô tả đơn giản
        if not '\n' in response and len(response) < 120:
            # Single line, short response
            if any(response_lower.startswith(prefix) for prefix in [
                'hướng dẫn', 'cách', 'quy trình', 'các bước', 'thông tin về'
            ]):
                return True

        return False

    def _build_entity_context(self, entities: Dict, graph_entities: Dict) -> str:
        """Build context string từ entities"""

        context_parts = []

        # From query entities
        if entities.get("Feature"):
            context_parts.append(f"- Phương thức/tính năng: {', '.join(entities['Feature'])}")
        if entities.get("Topic"):
            context_parts.append(f"- Chủ đề: {', '.join(entities['Topic'])}")
        if entities.get("Bank"):
            context_parts.append(f"- Ngân hàng: {', '.join(entities['Bank'])}")
        if entities.get("Error"):
            context_parts.append(f"- Lỗi: {', '.join(entities['Error'])}")

        # From graph entities
        if graph_entities.get("fees"):
            fees = graph_entities["fees"]
            if isinstance(fees, list):
                context_parts.append(f"- Phí trong hệ thống: {', '.join(str(f) for f in fees)}")
        if graph_entities.get("limits"):
            limits = graph_entities["limits"]
            if isinstance(limits, list):
                context_parts.append(f"- Hạn mức trong hệ thống: {', '.join(str(l) for l in limits)}")
        if graph_entities.get("timeframes"):
            timeframes = graph_entities["timeframes"]
            if isinstance(timeframes, list):
                context_parts.append(f"- Thời gian trong hệ thống: {', '.join(str(t) for t in timeframes)}")

        return "\n".join(context_parts) if context_parts else "Không có thông tin bổ sung"

    def _regex_extract_fallback(
        self,
        faq_answer: str,
        intent: str,
        entities: Dict,
        user_query: str
    ) -> Optional[Dict]:
        """
        Layer 2: Regex fallback khi LLM fail

        Chỉ dùng cho FEE, LIMIT, TIME vì có patterns rõ ràng
        """
        # Get filters từ entities
        filters = entities.get("Feature", []) + entities.get("Topic", [])

        # Find matching section if multi-section FAQ
        target_text = self._find_relevant_section(faq_answer, filters, user_query)
        if not target_text:
            target_text = faq_answer

        if intent == "FEE":
            return self._extract_fee_regex(target_text, filters)
        elif intent == "LIMIT":
            return self._extract_limit_regex(target_text, filters)
        elif intent == "TIME":
            return self._extract_time_regex(target_text, filters)

        return None

    def _extract_fee_regex(self, text: str, filters: List[str]) -> Optional[Dict]:
        """Extract fee using regex patterns"""

        text_lower = text.lower()

        fee_patterns = [
            (r'(miễn phí|không mất phí|không tính phí|không thu phí)', 'Miễn phí'),
            (r'phí[:\s]*(miễn phí)', 'Miễn phí'),
            (r'phí[:\s]*(\d+[\.,]?\d*\s*(vnđ|đồng|đ|vnd|%)?)', None),
            (r'mất phí[:\s]*(\d+[\.,]?\d*\s*(vnđ|đồng|đ|vnd)?)', None),
            (r'(\d+[\.,]?\d*\s*(vnđ|đồng|đ|vnd))\s*/\s*(giao dịch|lần)', None),
            (r'tham khảo.*?(https://[^\s]+)', 'url'),
        ]

        for pattern, default_value in fee_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if default_value == 'Miễn phí':
                    return {
                        "answer": "Phí: Miễn phí",
                        "info": {"fee": "Miễn phí"},
                        "filter": f"Regex pattern matched"
                    }
                elif default_value == 'url':
                    url_match = re.search(r'(https://[^\s]+)', text)
                    if url_match:
                        return {
                            "answer": f"Vui lòng tham khảo biểu phí tại: {url_match.group(1)}",
                            "info": {"fee": "url", "url": url_match.group(1)},
                            "filter": "URL reference"
                        }
                else:
                    fee_value = match.group(1)
                    return {
                        "answer": f"Phí: {fee_value}",
                        "info": {"fee": fee_value},
                        "filter": "Regex pattern matched"
                    }

        return None

    def _extract_limit_regex(self, text: str, filters: List[str]) -> Optional[Dict]:
        """Extract limit using regex patterns"""

        text_lower = text.lower()

        limit_patterns = [
            (r'hạn mức[:\s]*(\d+[\.,]?\d*\s*(triệu|tr|nghìn|k|vnđ|đồng)[^,\n]*)', None),
            (r'tối đa[:\s]*(\d+[\.,]?\d*\s*(triệu|tr|nghìn|k|vnđ|đồng)[^,\n]*)', None),
            (r'tối thiểu[:\s]*(\d+[\.,]?\d*\s*(triệu|tr|nghìn|k|vnđ|đồng)[^,\n]*)', None),
            (r'(\d+[\.,]?\d*\s*(triệu|tr))\s*/\s*(ngày|tháng|giao dịch)', None),
            (r'giới hạn[:\s]*(\d+[\.,]?\d*[^,\n]*)', None),
        ]

        for pattern, _ in limit_patterns:
            match = re.search(pattern, text_lower)
            if match:
                limit_value = match.group(1).strip()
                return {
                    "answer": f"Hạn mức: {limit_value}",
                    "info": {"limit": limit_value},
                    "filter": "Regex pattern matched"
                }

        return None

    def _extract_time_regex(self, text: str, filters: List[str]) -> Optional[Dict]:
        """Extract time using regex patterns"""

        text_lower = text.lower()

        time_patterns = [
            (r'(ngay lập tức|real-?time|tức thì|ngay)', 'Ngay lập tức'),
            (r'(T\+\d+\s*(ngày)?[^,\n]*)', None),  # T+1, T+2 format
            (r'trong vòng[:\s]*(\d+[\s-]*\d*\s*(ngày|giờ|phút)[^,\n]*)', None),
            (r'(\d+[\s-]*\d*\s*ngày\s*làm\s*việc)', None),
            (r'thời gian[:\s]*(\d+[\s-]*\d*\s*(ngày|giờ|phút)[^,\n]*)', None),
            (r'(\d+[\s-]*\d*\s*(ngày|giờ|phút))', None),
        ]

        for pattern, default_value in time_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                if default_value:
                    return {
                        "answer": f"Thời gian: {default_value}",
                        "info": {"time": default_value},
                        "filter": "Regex pattern matched"
                    }
                else:
                    time_value = match.group(1)
                    return {
                        "answer": f"Thời gian: {time_value}",
                        "info": {"time": time_value},
                        "filter": "Regex pattern matched"
                    }

        return None

    def _find_relevant_section(
        self,
        faq_answer: str,
        filters: List[str],
        query: str
    ) -> Optional[str]:
        """Find section in multi-section FAQ that matches the query"""

        sections = self._split_faq_into_sections(faq_answer)

        if len(sections) <= 1:
            return None  # Single section, no filtering needed

        # Score each section
        best_section = None
        best_score = 0
        query_lower = query.lower()

        for section_name, section_content in sections:
            score = 0
            section_text = (section_name + " " + section_content).lower()

            # Match with filters
            for f in filters:
                filter_words = f.lower().split()
                matches = sum(1 for w in filter_words if w in section_text and len(w) > 2)
                score += matches * 3

            # Match with query keywords
            query_words = [w for w in query_lower.split() if len(w) > 2]
            matches = sum(1 for w in query_words if w in section_text)
            score += matches

            if score > best_score:
                best_score = score
                best_section = section_content

        return best_section if best_score >= 3 else None

    def _split_faq_into_sections(self, faq_answer: str) -> List[Tuple[str, str]]:
        """Split FAQ into sections based on structure patterns"""

        sections = []
        lines = faq_answer.split('\n')

        section_start_patterns = [
            r'^(\d+[\.\)])\s*(.+?)[:：]?\s*$',
            r'^[-•]\s*(.+?)[:：]\s*$',
            r'^(Cách|Phương thức|Hình thức)\s*\d+[:：]?\s*(.*)$',
            r'^\*\*(.+?)\*\*[:：]?\s*$',
        ]

        current_section_name = ""
        current_section_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_section_start = False
            section_name = ""

            for pattern in section_start_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    is_section_start = True
                    groups = match.groups()
                    section_name = ' '.join(g for g in groups if g).strip()
                    break

            if is_section_start:
                if current_section_name and current_section_content:
                    sections.append((current_section_name, '\n'.join(current_section_content)))
                current_section_name = section_name
                current_section_content = []
            else:
                current_section_content.append(line)

        if current_section_name and current_section_content:
            sections.append((current_section_name, '\n'.join(current_section_content)))

        return sections

    def _try_case_based_extraction(
        self,
        faq_answer: str,
        entities: Dict,
        intent: str,
        user_query: str
    ) -> Optional[Dict]:
        """
        Layer 3: Case-based extraction for HOW_TO/TROUBLESHOOT

        Extract only the relevant section/case from multi-case FAQ
        """
        features = entities.get("Feature", [])
        topics = entities.get("Topic", [])

        sections = self._split_faq_into_sections(faq_answer)

        if len(sections) <= 1:
            return None  # No multi-section structure

        # Find best matching section
        best_section = None
        best_score = 0

        for section_name, section_content in sections:
            score = 0
            section_lower = (section_name + " " + section_content).lower()

            # Match with Feature entities
            for feature in features:
                feature_words = feature.lower().split()
                matches = sum(1 for w in feature_words if w in section_lower)
                score += matches * 3

            # Match with Topic entities
            for topic in topics:
                topic_words = topic.lower().split()
                matches = sum(1 for w in topic_words if w in section_lower)
                score += matches * 2

            # Match with query keywords
            query_words = user_query.lower().split()
            important_words = [w for w in query_words if len(w) > 2]
            matches = sum(1 for w in important_words if w in section_lower)
            score += matches

            if score > best_score:
                best_score = score
                best_section = (section_name, section_content)

        if best_section and best_score >= 3:
            section_name, section_content = best_section
            full_section = f"{section_name}\n{section_content}".strip()

            return {
                "answer": full_section,
                "info": {"section": section_name, "method": "case_matching"},
                "filter": f"Feature: {features}" if features else f"Topic: {topics}"
            }

        return None


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    extractor = FocusedAnswerExtractor()

    # Test case
    test_faq = """Có 3 cách nạp tiền vào VNPT Money:

1. Nạp tiền từ ngân hàng liên kết:
   - Bước 1: Mở ứng dụng VNPT Money
   - Bước 2: Chọn "Nạp tiền"
   - Bước 3: Chọn ngân hàng liên kết
   - Phí: Miễn phí
   - Hạn mức: 50 triệu/ngày
   - Thời gian: Ngay lập tức

2. Nạp tiền qua chuyển khoản ngân hàng:
   - Bước 1: Mở app ngân hàng
   - Bước 2: Chuyển khoản đến số tài khoản VNPT Money
   - Phí: 3,300 VNĐ/giao dịch
   - Hạn mức: 100 triệu/ngày
   - Thời gian: 1-3 ngày làm việc

3. Nạp tiền qua ATM:
   - Phí: 5,500 VNĐ
   - Hạn mức: 20 triệu/ngày"""

    print("=" * 60)
    print("TEST FOCUSED ANSWER EXTRACTOR (LLM-First)")
    print("=" * 60)

    # Test 1: FEE intent
    print("\n📌 Test 1: Hỏi về PHÍ của ngân hàng liên kết")
    result = extractor.extract_focused_answer(
        user_query="Phí nạp tiền từ ngân hàng liên kết là bao nhiêu?",
        faq_answer=test_faq,
        faq_question="Cách nạp tiền vào VNPT Money?",
        intent="FEE",
        entities={"Feature": ["liên kết ngân hàng"], "Topic": ["Nạp tiền"]},
        graph_entities={}
    )
    print(f"Query: Phí nạp tiền từ ngân hàng liên kết là bao nhiêu?")
    print(f"Answer: {result.answer}")
    print(f"Source: {result.source.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Reduction: {(1 - result.answer_length/result.original_length)*100:.0f}%")

    # Test 2: LIMIT intent
    print("\n📌 Test 2: Hỏi về HẠN MỨC")
    result = extractor.extract_focused_answer(
        user_query="Hạn mức nạp tiền từ ngân hàng liên kết?",
        faq_answer=test_faq,
        faq_question="Cách nạp tiền vào VNPT Money?",
        intent="LIMIT",
        entities={"Feature": ["liên kết ngân hàng"]},
        graph_entities={}
    )
    print(f"Query: Hạn mức nạp tiền từ ngân hàng liên kết?")
    print(f"Answer: {result.answer}")
    print(f"Source: {result.source.value}")

    # Test 3: HOW_TO với Feature filter
    print("\n📌 Test 3: Hỏi về CÁCH nạp tiền từ ngân hàng liên kết")
    result = extractor.extract_focused_answer(
        user_query="Cách nạp tiền từ ngân hàng liên kết?",
        faq_answer=test_faq,
        faq_question="Cách nạp tiền vào VNPT Money?",
        intent="HOW_TO",
        entities={"Feature": ["liên kết ngân hàng"], "Topic": ["Nạp tiền"]},
        graph_entities={}
    )
    print(f"Query: Cách nạp tiền từ ngân hàng liên kết?")
    print(f"Answer: {result.answer[:200]}...")
    print(f"Source: {result.source.value}")
    print(f"Filter applied: {result.filter_applied}")
