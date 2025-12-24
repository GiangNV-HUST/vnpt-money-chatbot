# -*- coding: utf-8 -*-
"""
Enhanced Entity Extractor với Regex & Confidence Scoring
Cải tiến từ SimpleEntityExtractor
"""

import re
from typing import Dict, List, Tuple
from simple_entity_extractor import SimpleEntityExtractor


class EnhancedEntityExtractor(SimpleEntityExtractor):
    """
    Enhanced version với:
    1. Regex patterns cho flexibility
    2. Confidence scoring
    3. Validation layer
    """

    def __init__(self):
        super().__init__()

        # THÊM: Regex patterns cho error detection
        # IMPORTANT: Error names MUST match Neo4j Error node names exactly!
        self.error_patterns_regex = [
            # "tài khoản thụ hưởng chưa nhận được tiền" - MAIN ERROR for transfer/payment issues
            # Pattern 1: Direct "không nhận được tiền"
            (r"(chưa|không|ko)\s+(nhận|có|thấy)\s+(được\s+)?tiền", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 2: "không nhận được" + context about recipient/phone
            (r"(thuê bao|điện thoại|tài khoản|người nhận|bên nhận|thụ hưởng).*(chưa|không|ko)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 3: "nạp/chuyển/rút tiền" + "không nhận được"
            (r"(nạp|chuyển|rút)\s+(tiền|khoản).*(chưa|không|ko)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 4: Existing pattern for "tiền chưa về"
            (r"tiền\s+(chưa|không|ko)\s+(về|tới|đến)", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 5: "thành công nhưng không nhận được" (for your specific case)
            (r"(thành công|đã.*trừ).*(nhưng|mà).*(chưa|không)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),

            # "Thông tin giao dịch không nhận được" - For when transaction shows success but recipient didn't receive
            # This matches FAQ_72! Priority: Check this BEFORE generic patterns
            (r"(nạp|chuyển).*(thành công).*(thuê bao|điện thoại|người nhận|bên nhận).*(không|chưa)\s+nhận", "Thông tin giao dịch không nhận được"),
            # Alternative pattern: "thành công" but carrier/bank confirms not received
            (r"(thành công).*(nhà mạng|ngân hàng).*(khẳng định|xác nhận).*(không|chưa)", "Thông tin giao dịch không nhận được"),

            # Giao dịch thất bại patterns
            (r"giao\s*dịch\s+(thất\s*bại|lỗi|fail)", "giao dịch thất bại"),
            (r"(không|chưa)\s+(chuyển|nạp|rút)\s+được", "giao dịch thất bại"),
            (r"(không|chưa)\s+(thành công)", "giao dịch thất bại"),
            # Pattern: "đã trừ tiền nhưng ... chưa có/nhận"
            (r"(đã|bị)\s+trừ\s+tiền.*(chưa|không)\s+(có|nhận)", "tài khoản thụ hưởng chưa nhận được tiền"),
            (r"(chưa|không)\s+(có|nhận).*(đã|bị)\s+trừ\s+tiền", "tài khoản thụ hưởng chưa nhận được tiền"),

            # Đang xử lý nhưng đã trừ tiền (CRITICAL)
            (r"(đang\s+xử\s+lý|processing).*(đã|bị).*(trừ|mất)\s+tiền", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"(đã|bị).*(trừ|mất)\s+tiền.*(đang\s+xử\s+lý|processing)", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"(nạp|chuyển|rút)\s+tiền.*(đang\s+xử\s+lý|báo.*đang).*(đã|bị)\s+trừ", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"trạng\s+thái.*(đang\s+xử\s+lý).*(đã|bị)\s+trừ", "giao dịch đang xử lý nhưng đã trừ tiền"),

            # OTP patterns
            (r"(không|chưa)\s+nhận\s+(được\s+)?(otp|mã)", "không nhận được OTP"),

            # Account/Card invalid
            (r"(thẻ|tài\s*khoản)\s+(không\s+)?hợp\s*lệ", "thông tin thẻ/tài khoản không hợp lệ"),

            # Over limit
            (r"(quá|vượt)\s+(hạn\s*mức|giới\s*hạn)", "quá hạn mức"),

            # Wrong transfer patterns (CRITICAL for "chuyển tiền nhầm")
            (r"(chuyển|nạp|rút)\s+(tiền\s+)?(nhầm|sai|lỡ)", "chuyển tiền nhầm"),
            (r"(nhầm|sai|lỡ)\s+(chuyển|nạp)", "chuyển tiền nhầm"),
            (r"chuyển\s+nhầm", "chuyển tiền nhầm"),

            # Biometric error patterns (CRITICAL for biometric issues)
            (r"sinh\s*trắc\s*(học)?.*(báo|hiện|thông\s*báo|xuất\s*hiện).*(lỗi|sai)", "lỗi sinh trắc học"),
            (r"(hệ\s*thống|app).*(báo|hiện|thông\s*báo).*(lỗi|sai).*(sinh\s*trắc|ekyc)", "lỗi sinh trắc học"),
            (r'báo\s*lỗi.*[\"\'].*ngày\s*sinh.*[\"\']', "lỗi ngày sinh không khớp"),
            (r'báo\s*lỗi.*[\"\'].*định\s*danh.*[\"\']', "lỗi định danh không khớp"),
            (r"ngày\s*sinh.*(không\s*khớp|không\s*đúng|sai)", "lỗi ngày sinh không khớp"),
            (r"định\s*danh.*(không\s*khớp|không\s*đúng|sai)", "lỗi định danh không khớp"),
            (r"(cmnd|cccd|căn\s*cước).*(không\s*khớp|không\s*đúng|sai)", "lỗi định danh không khớp"),
            (r"(sinh\s*trắc|ekyc).*(thất\s*bại|không\s*thành\s*công)", "sinh trắc học thất bại"),
            (r"(không|chưa).*(sinh\s*trắc|ekyc).*(được|thành\s*công)", "sinh trắc học thất bại"),
        ]

        # THÊM: Regex patterns cho topic detection
        self.topic_patterns_regex = [
            # Mở khóa patterns
            (r"mở\s*khóa\s+(tài\s*khoản|ví)", "Mở khóa tài khoản"),
            (r"unlock\s+(account|ví)", "Mở khóa tài khoản"),

            # Khóa patterns
            (r"khóa\s+(tài\s*khoản|ví)", "Khóa tài khoản"),
            (r"lock\s+(account|ví)", "Khóa tài khoản"),

            # Đổi mật khẩu patterns
            (r"đổi\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"thay\s*đổi\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"đặt\s*lại\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"change\s+password", "Đổi mật khẩu"),
        ]

        # THÊM: Contextual rules
        self.contextual_rules = {
            # Nếu có "chuyển tiền" + "chưa" → Error: chưa nhận được
            ("chuyển tiền", "chưa"): ("Error", "chưa nhận được tiền"),
            ("nạp tiền", "thất bại"): ("Error", "giao dịch thất bại"),

            # Nếu có "mở khóa" + "tài khoản" → Topic: Mở khóa tài khoản
            ("mở khóa", "tài khoản"): ("Topic", "Mở khóa tài khoản"),
            ("mở khóa", "ví"): ("Topic", "Mở khóa tài khoản"),
        }

    def extract_with_confidence(self, query: str) -> Tuple[Dict[str, List[str]], float]:
        """
        Extract entities với confidence score

        Returns:
            (entities_dict, confidence_score)
        """
        # Step 1: Pattern-based extraction (from parent)
        entities = self.extract(query)

        # Step 2: Enhanced regex extraction
        regex_entities = self._extract_with_regex(query)

        # Step 3: Merge results
        entities = self._merge_entities(entities, regex_entities)

        # Step 4: Apply contextual rules
        entities = self._apply_contextual_rules(query, entities)

        # Step 5: Validate
        entities = self._validate_entities(query, entities)

        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(query, entities)

        return entities, confidence

    def _extract_with_regex(self, query: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns"""
        entities = {"Error": [], "Topic": []}

        query_lower = query.lower()

        # Check error regex patterns
        for pattern, error_name in self.error_patterns_regex:
            if re.search(pattern, query_lower):
                if error_name not in entities["Error"]:
                    entities["Error"].append(error_name)

        # Check topic regex patterns
        for pattern, topic_name in self.topic_patterns_regex:
            if re.search(pattern, query_lower):
                if topic_name not in entities["Topic"]:
                    entities["Topic"].append(topic_name)

        return entities

    def _merge_entities(
        self,
        entities1: Dict[str, List[str]],
        entities2: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Merge two entity dicts"""
        merged = entities1.copy()

        for entity_type, values in entities2.items():
            if entity_type not in merged:
                merged[entity_type] = []

            for value in values:
                if value not in merged[entity_type]:
                    merged[entity_type].append(value)

        return merged

    def _apply_contextual_rules(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Apply contextual rules to improve extraction"""
        query_lower = query.lower()

        for (keyword1, keyword2), (entity_type, entity_value) in self.contextual_rules.items():
            if keyword1 in query_lower and keyword2 in query_lower:
                if entity_type not in entities:
                    entities[entity_type] = []
                if entity_value not in entities[entity_type]:
                    entities[entity_type].append(entity_value)

        return entities

    def _validate_entities(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Validate and auto-correct entities"""
        query_lower = query.lower()

        # Rule: Nếu có "mở khóa" → xóa "Khóa tài khoản" (vì "mở khóa" ưu tiên hơn "khóa")
        if "mở khóa" in query_lower and "Mở khóa tài khoản" in entities.get("Topic", []):
            if "Khóa tài khoản" in entities.get("Topic", []):
                entities["Topic"].remove("Khóa tài khoản")

        # Rule: Nếu có "khóa" nhưng KHÔNG có "mở" → có thể là "khóa tài khoản"
        # (logic này đã được xử lý bởi pattern matching)

        # Rule: Nếu query có "chuyển tiền" mà không có Topic, thêm vào
        if "chuyển tiền" in query_lower or "chuyển khoản" in query_lower:
            if "Chuyển tiền" not in entities.get("Topic", []):
                if "Topic" not in entities:
                    entities["Topic"] = []
                entities["Topic"].append("Chuyển tiền")

        # Rule: Nếu query có "nạp tiền" mà không có Topic, thêm vào
        if "nạp tiền" in query_lower or "nạp" in query_lower:
            if "Nạp tiền" not in entities.get("Topic", []):
                if "Topic" not in entities:
                    entities["Topic"] = []
                entities["Topic"].append("Nạp tiền")

        # Rule: Nếu query có "sinh trắc học" hoặc "ekyc" mà không có Topic, thêm vào
        if ("sinh trắc" in query_lower or "ekyc" in query_lower) and "Sinh trắc học" not in entities.get("Topic", []):
            if "Topic" not in entities:
                entities["Topic"] = []
            entities["Topic"].append("Sinh trắc học")

        # Rule: Nếu query có "đổi mật khẩu" / "thay đổi mật khẩu" mà không có Topic, thêm vào
        if ("đổi mật khẩu" in query_lower or "thay đổi mật khẩu" in query_lower or "đặt lại mật khẩu" in query_lower) and "Đổi mật khẩu" not in entities.get("Topic", []):
            if "Topic" not in entities:
                entities["Topic"] = []
            entities["Topic"].append("Đổi mật khẩu")

        # Rule: Nếu có error về "chưa nhận được" + có "chuyển tiền"
        # → Đảm bảo có Topic "Chuyển tiền"
        if entities.get("Error"):
            for error in entities["Error"]:
                if "chưa nhận" in error.lower() and "chuyển" in query_lower:
                    if "Topic" not in entities:
                        entities["Topic"] = []
                    if "Chuyển tiền" not in entities["Topic"]:
                        entities["Topic"].append("Chuyển tiền")
                # Rule: Nếu có error về sinh trắc → Đảm bảo có Topic "Sinh trắc học"
                if ("sinh trắc" in error.lower() or "ekyc" in error.lower() or "ngày sinh" in error.lower() or "định danh" in error.lower()):
                    if "Topic" not in entities:
                        entities["Topic"] = []
                    if "Sinh trắc học" not in entities["Topic"]:
                        entities["Topic"].append("Sinh trắc học")

        return entities

    def _calculate_confidence(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> float:
        """
        Calculate confidence score (0.0 - 1.0)

        Scoring:
        - Error found: +0.4
        - Topic found: +0.3
        - Service found: +0.2
        - Multiple entities: +0.1
        """
        confidence = 0.0

        # Error entities are most important for troubleshooting
        if entities.get("Error"):
            confidence += 0.4

        # Topic helps narrow down
        if entities.get("Topic"):
            confidence += 0.3

        # Service provides context
        if entities.get("Service"):
            confidence += 0.2

        # Multiple entities = higher confidence
        total_entities = sum(len(v) for v in entities.values() if isinstance(v, list))
        if total_entities >= 3:
            confidence += 0.1

        return min(confidence, 1.0)  # Cap at 1.0


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    extractor = EnhancedEntityExtractor()

    test_queries = [
        "Tôi thực hiện giao dịch chuyển tiền đến ngân hàng nhưng tài khoản thụ hưởng chưa nhận được thì phải làm thế nào?",
        "Chuyển tiền rồi mà tiền chưa về",
        "Giao dịch nạp tiền thất bại",
        "Làm sao để chuyển tiền đến Vietinbank?",
        "Không nhận được OTP khi chuyển tiền",
        "Tài khoản không hợp lệ",
    ]

    print("=" * 80)
    print("ENHANCED ENTITY EXTRACTOR TEST")
    print("=" * 80)

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")

        # Extract with confidence
        entities, confidence = extractor.extract_with_confidence(query)

        print(f"\n📊 Confidence: {confidence:.2%}")

        print("\n📌 Extracted Entities:")
        for entity_type, values in entities.items():
            if values and entity_type != 'out_of_scope':
                print(f"  {entity_type}: {values}")

        # Interpretation
        print(f"\n💡 Interpretation:")
        if confidence >= 0.7:
            print("  ✅ HIGH confidence - Extraction is reliable")
        elif confidence >= 0.4:
            print("  🟡 MEDIUM confidence - May need fallback")
        else:
            print("  ⚠️  LOW confidence - Consider using LLM fallback")

        if entities.get("Error"):
            print("  🔧 Detected as TROUBLESHOOTING query")
        elif entities.get("Topic") and not entities.get("Error"):
            print("  📖 Detected as HOW-TO or INFO query")
