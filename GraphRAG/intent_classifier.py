# -*- coding: utf-8 -*-
"""
Intent Classification Module - REFINED VERSION
Based on analysis of 803 FAQs from VNPT Money dataset.

INTENT DISTRIBUTION (from data analysis):
- HOW_TO: 218 FAQs (27%) - "như thế nào", "làm sao", "cách"
- TROUBLESHOOT: 116 FAQs (14%) - "báo lỗi", "thất bại", "chưa nhận"
- STATUS_CHECK: 113 FAQs (14%) - "kiểm tra", "tra cứu", "xem lịch sử"
- REQUIREMENT: 54 FAQs (7%) - "điều kiện", "yêu cầu"
- TIME: 49 FAQs (6%) - "bao lâu", "thời gian"
- FEE: 42 FAQs (5%) - "phí", "mất phí", "chi phí"
- LIMIT: 21 FAQs (3%) - "hạn mức", "tối đa", "giới hạn"
- WHY: 20 FAQs (2%) - "tại sao", "vì sao"
- INFO_REQUEST: Remaining - General information queries
"""

from typing import Dict, Tuple, List
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Enhanced Intent Classifier based on real FAQ data analysis.

    Priority order (checked first to last, most specific first):
    1. FEE - Specific fee questions
    2. LIMIT - Specific limit questions
    3. TIME - Specific time questions
    4. TROUBLESHOOT - Error/problem queries
    5. STATUS_CHECK - Status/history checking
    6. REQUIREMENT - Conditions/requirements
    7. WHY - Explanation queries
    8. HOW_TO - Step-by-step guides
    9. INFO_REQUEST - General info (fallback)
    """

    def __init__(self):
        """Initialize intent patterns with priority ordering"""

        # Intent patterns ordered by specificity (most specific first)
        self.intent_patterns = {
            # ============================================
            # SPECIFIC INFO INTENTS (Highest Priority)
            # ============================================

            "FEE": {
                "patterns": [
                    # Direct fee questions - 42 FAQs in dataset
                    r"(phí|fee|chi phí).*(bao nhiêu|là gì|như thế nào|\?)",
                    r"(bao nhiêu|là).*(phí|fee|chi phí)",
                    r"(có|mất|tốn|bị)\s+(phí|tiền)",
                    r"miễn phí",
                    r"(phí|fee)\s+(nạp|rút|chuyển|thanh toán|dịch vụ)",
                    r"(nạp|rút|chuyển|thanh toán).*(phí|fee|mất tiền)",
                    r"^phí\b",  # Starts with "phí"
                    r"biểu\s+phí",
                    r"bảng\s+phí",
                    r"chính\s+sách\s+phí",
                    r"(có|không)\s+mất\s+(tiền|phí)",
                    r"tính\s+phí",
                    r"rút\s+tiền.*(mất|bị)\s+phí",
                    r"chuyển\s+tiền.*(mất|có)\s+phí",
                ],
                "keywords": [
                    "phí", "fee", "chi phí", "mất phí", "tốn phí", "miễn phí",
                    "biểu phí", "bảng phí", "phí dịch vụ", "mất tiền", "bị phí"
                ],
                "weight": 3.0,  # Highest priority
                "priority": 1
            },

            "LIMIT": {
                "patterns": [
                    # Direct limit questions - 21 FAQs in dataset
                    r"(hạn mức|giới hạn|limit).*(bao nhiêu|là gì|như thế nào|\?)",
                    r"(bao nhiêu|là).*(hạn mức|giới hạn|limit)",
                    r"(tối đa|tối thiểu|max|min).*(bao nhiêu|là)",
                    r"(được|có thể).*(tối đa|nhiều nhất)",
                    r"(nạp|rút|chuyển).*(tối đa|tối thiểu|bao nhiêu tiền)",
                    r"(số tiền|mức).*(tối đa|tối thiểu)",
                    r"(vượt|quá)\s+hạn\s+mức",
                    r"giao\s+dịch\s+quá\s+hạn\s+mức",
                    r"báo.*hạn\s+mức",
                ],
                "keywords": [
                    "hạn mức", "giới hạn", "limit", "tối đa", "tối thiểu",
                    "max", "min", "nhiều nhất", "ít nhất", "quá hạn mức"
                ],
                "weight": 3.0,
                "priority": 2
            },

            "TIME": {
                "patterns": [
                    # Direct time questions - 49 FAQs in dataset
                    r"(bao lâu|mất bao lâu|khi nào)",
                    r"thời\s+gian.*(bao lâu|là|xử lý)",
                    r"(bao lâu|mấy).*(ngày|giờ|phút)",
                    r"(mất|cần|tốn).*(bao lâu|bao nhiêu).*(thời gian|ngày|giờ)",
                    r"(trong vòng|trong|sau).*(ngày|giờ|phút)",
                    r"(nạp|rút|chuyển|hoàn).*(mất|cần).*(bao lâu|thời gian)",
                    r"(tiền|giao dịch).*(về|tới|đến|hoàn).*(khi nào|bao lâu)",
                    r"chờ\s+bao\s+lâu",
                    r"ngày\s+làm\s+việc",
                ],
                "keywords": [
                    "thời gian", "bao lâu", "mất bao lâu", "khi nào",
                    "ngay lập tức", "real-time", "ngày làm việc", "chờ bao lâu"
                ],
                "weight": 3.0,
                "priority": 3
            },

            # ============================================
            # PROBLEM-SOLVING INTENTS
            # ============================================

            "TROUBLESHOOT": {
                "patterns": [
                    # Error handling - 116 FAQs in dataset
                    r"báo\s*(lỗi|\")",  # "báo lỗi" or báo "..."
                    r"(bị|gặp|có)\s*(lỗi|vấn đề|sự cố|trục trặc)",
                    r"(thất bại|fail|error|không thành công)",
                    r"(chưa|không|ko)\s*(nhận|có|về|được|thành công)",
                    r"tại sao.*(chưa|không|ko|lỗi|thất bại)",
                    r"làm sao để.*(khắc phục|sửa|fix)",
                    r"phải làm.*(gì|thế nào|sao).*(khi|nếu).*(lỗi|sự cố|vấn đề)",
                    r"(giao dịch|tiền).*(chưa|không).*(về|nhận|tới|thành công)",
                    r"(đã|rồi).*(mà|nhưng).*(chưa|không)",
                    r"(đang\s+xử\s+lý|processing).*(đã|bị).*(trừ|mất)",
                    r"(đã|bị).*(trừ|mất).*(đang\s+xử\s+lý|processing|chưa)",
                    r"(sinh\s*trắc|ekyc).*(báo|hiện).*(lỗi|sai)",
                    r"(ngày\s*sinh|định\s*danh|cmnd|cccd).*(không\s*khớp|sai)",
                    r"(khuôn mặt|OTP).*(không|chưa|sai)",
                    r"thông tin.*(không|chưa).*(khớp|hợp lệ|trùng)",
                ],
                "keywords": [
                    "chưa nhận được", "không nhận được", "bị lỗi", "gặp sự cố",
                    "thất bại", "không thành công", "chưa về", "phải làm gì",
                    "tại sao", "khắc phục", "đang xử lý", "đã trừ tiền",
                    "báo lỗi", "không được", "lỗi", "không hợp lệ", "không khớp"
                ],
                "weight": 2.5,
                "priority": 4
            },

            "STATUS_CHECK": {
                "patterns": [
                    # Status/history checking - 113 FAQs in dataset
                    r"(kiểm tra|check|xem|tra cứu).*(trạng thái|status|tình trạng|giao dịch|lịch sử)",
                    r"(xem|kiểm tra).*(giao dịch|transaction|số dư)",
                    r"giao dịch.*(đang|đã|chưa|trong)",
                    r"(trạng thái|status).*(giao dịch|chuyển tiền|nạp tiền|rút tiền)",
                    r"xem.*(lịch sử|history|giao dịch)",
                    r"(muốn|cần).*(kiểm tra|xem|tra cứu)",
                    r"(tìm|tra).*(giao dịch|transaction)",
                ],
                "keywords": [
                    "kiểm tra", "tra cứu", "xem", "trạng thái",
                    "tình trạng", "lịch sử", "status", "số dư"
                ],
                "weight": 2.0,
                "priority": 5
            },

            "REQUIREMENT": {
                "patterns": [
                    # Requirements/conditions - 54 FAQs in dataset
                    r"điều\s+kiện.*(để|gì|là|cần)",
                    r"(yêu cầu|requirements).*(gì|là|cần)",
                    r"(cần|phải).*(gì|những gì|điều kiện).*(để|cho)",
                    r"(muốn|để).*(cần|phải).*(gì|những gì)",
                    r"làm\s+sao\s+để\s+được",
                ],
                "keywords": [
                    "điều kiện", "yêu cầu", "cần gì", "cần những gì",
                    "requirements", "để được", "phải có"
                ],
                "weight": 2.0,
                "priority": 6
            },

            "WHY": {
                "patterns": [
                    # Explanation queries - 20 FAQs in dataset
                    r"^tại\s+sao",  # Starts with "tại sao"
                    r"^vì\s+sao",   # Starts with "vì sao"
                    r"tại\s+sao.*(tôi|mình|bạn)",
                    r"vì\s+sao.*(tôi|mình|bạn)",
                    r"(lý do|nguyên nhân).*(gì|là|sao)",
                ],
                "keywords": [
                    "tại sao", "vì sao", "lý do", "nguyên nhân"
                ],
                "weight": 2.0,
                "priority": 7
            },

            # ============================================
            # INSTRUCTION INTENTS
            # ============================================

            "HOW_TO": {
                "patterns": [
                    # Step-by-step guides - 218 FAQs in dataset
                    r"(làm thế nào|làm sao|cách|như thế nào).*(để|cho|thì|\?)",
                    r"(hướng dẫn|chỉ dẫn|chỉ cách)",
                    r"(muốn|cần).*(làm|thực hiện)",
                    r"(bước|step).*(để|cho|thực hiện)",
                    r"^(cách|how to)",
                    r"(muốn|cần).*(phải làm gì|làm gì|thế nào)",
                    r"(thực hiện|làm|thao tác).*(như thế nào|thế nào|\?)",
                    r"(giao dịch|chuyển tiền|nạp tiền|rút tiền).*(như thế nào)(\?|$)",
                    r"(mở|đóng|hủy|đăng ký|tạo|liên kết).*(tài khoản|ví|ngân hàng).*(\?|như thế nào)",
                    r"(tôi có thể|có thể).*(như thế nào|\?)",
                    r"thao\s+tác.*(như|thế nào)",
                ],
                "keywords": [
                    "làm thế nào", "như thế nào", "cách", "hướng dẫn", "bước",
                    "quy trình", "thủ tục", "thao tác", "phải làm gì",
                    "làm gì", "thực hiện", "có thể"
                ],
                "weight": 1.5,
                "priority": 8
            },

            "COMPARISON": {
                "patterns": [
                    r"(so sánh|khác nhau|giống nhau)",
                    r"(nên|tốt hơn|hay hơn).*(chọn|dùng|sử dụng)",
                    r"(cách nào|phương thức nào).*(tốt|nhanh|rẻ)",
                    r"(có những|các).*(cách|phương thức|hình thức)",
                    r"(khác|giống).*(gì|như thế nào)",
                    r"(ưu|nhược).*(điểm)",
                ],
                "keywords": [
                    "so sánh", "khác nhau", "giống nhau", "tốt hơn",
                    "nên chọn", "ưu điểm", "nhược điểm"
                ],
                "weight": 1.5,
                "priority": 9
            },

            # ============================================
            # GENERAL INTENT (Fallback)
            # ============================================

            "INFO_REQUEST": {
                "patterns": [
                    r"(là gì|what is|nghĩa là)",
                    r"^(có|được|có thể)",
                    r"(thông tin|info).*(về|của)",
                ],
                "keywords": [
                    "là gì", "thông tin"
                ],
                "weight": 1.0,
                "priority": 10
            },
        }

        # Sort intents by priority for classification
        self._sorted_intents = sorted(
            self.intent_patterns.items(),
            key=lambda x: x[1]["priority"]
        )

    def classify(self, query: str) -> Tuple[str, float, Dict]:
        """
        Classify user query intent with priority-based scoring.

        Args:
            query: User query string

        Returns:
            Tuple of (intent_name, confidence, details)
        """
        query_lower = query.lower().strip()

        intent_scores = {}
        matched_patterns = {}

        # Check each intent
        for intent, config in self.intent_patterns.items():
            score = 0
            patterns_matched = []
            keywords_matched = []

            # Check regex patterns
            for pattern in config["patterns"]:
                if re.search(pattern, query_lower):
                    score += 1
                    patterns_matched.append(pattern)

            # Check keywords
            for keyword in config["keywords"]:
                if keyword.lower() in query_lower:
                    score += 0.5
                    keywords_matched.append(keyword)

            # Apply weight
            weighted_score = score * config["weight"]

            # Add priority bonus for ties (higher priority = higher bonus)
            priority_bonus = (11 - config["priority"]) * 0.1
            weighted_score += priority_bonus if score > 0 else 0

            if weighted_score > 0:
                intent_scores[intent] = weighted_score
                matched_patterns[intent] = {
                    "patterns": patterns_matched,
                    "keywords": keywords_matched,
                    "raw_score": score,
                    "weighted_score": weighted_score,
                    "priority": config["priority"]
                }

        # Get best intent
        if not intent_scores:
            return "INFO_REQUEST", 0.3, {}

        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent_name = best_intent[0]

        # ============================================
        # SPECIAL CASE: TIME vs TROUBLESHOOT conflict
        # When query has BOTH time keywords ("bao lâu", "khi nào") AND
        # troubleshoot keywords ("thất bại", "không thành công"),
        # prefer TIME because user is asking ABOUT time/duration
        # ============================================
        if intent_name == "TROUBLESHOOT" and "TIME" in intent_scores:
            time_keywords = ["bao lâu", "khi nào", "mất bao lâu", "thời gian"]
            has_time_question = any(kw in query_lower for kw in time_keywords)
            if has_time_question:
                intent_name = "TIME"
                best_intent = ("TIME", intent_scores["TIME"])

        # Calculate confidence
        max_possible = len(self.intent_patterns[intent_name]["patterns"]) + \
                      len(self.intent_patterns[intent_name]["keywords"]) * 0.5
        max_possible *= self.intent_patterns[intent_name]["weight"]

        confidence = min(best_intent[1] / max_possible, 1.0) if max_possible > 0 else 0.0

        # Boost confidence for specific intents
        if intent_name in ["FEE", "LIMIT", "TIME"]:
            confidence = max(confidence, 0.6)  # Minimum 60% for specific intents

        logger.info(f"Intent classified: {intent_name} (confidence: {confidence:.2%})")

        return intent_name, confidence, matched_patterns.get(intent_name, {})

    def classify_with_fallback(self, query: str, entities: Dict = None) -> Tuple[str, float, Dict]:
        """
        Classify with entity-based fallback for ambiguous queries.

        Args:
            query: User query
            entities: Extracted entities from query

        Returns:
            Tuple of (intent_name, confidence, details)
        """
        intent, confidence, details = self.classify(query)

        # If confidence is low, use entities to help
        if confidence < 0.4 and entities:
            # Check for fee-related entities
            if entities.get("Fee"):
                return "FEE", 0.7, {"source": "entity_fallback"}

            # Check for limit-related entities
            if entities.get("Limit"):
                return "LIMIT", 0.7, {"source": "entity_fallback"}

            # Check for error-related entities
            if entities.get("Error"):
                return "TROUBLESHOOT", 0.7, {"source": "entity_fallback"}

            # Check for status-related entities
            if entities.get("Status"):
                return "STATUS_CHECK", 0.7, {"source": "entity_fallback"}

        return intent, confidence, details

    def is_specific_intent(self, intent: str) -> bool:
        """Check if intent is a specific extraction intent (FEE, LIMIT, TIME)"""
        return intent in ["FEE", "LIMIT", "TIME"]

    def get_extraction_type(self, intent: str) -> str:
        """Map intent to extraction type for IntentAnswerExtractor"""
        mapping = {
            "FEE": "FEE",
            "LIMIT": "LIMIT",
            "TIME": "TIME",
            "TROUBLESHOOT": "TROUBLESHOOT",
            "STATUS_CHECK": "STATUS_CHECK",
            "REQUIREMENT": "INFO_REQUEST",
            "WHY": "INFO_REQUEST",
            "HOW_TO": "HOW_TO",
            "COMPARISON": "COMPARISON",
            "INFO_REQUEST": "INFO_REQUEST"
        }
        return mapping.get(intent, "INFO_REQUEST")


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    classifier = IntentClassifier()

    # Test cases based on REAL FAQ questions from dataset
    test_queries = [
        # FEE queries (42 FAQs in dataset)
        ("Tôi rút tiền thành công nhưng bị mất phí khi giao dịch", "FEE"),
        ("Chuyển tiền đến ngân hàng có mất phí hay không?", "FEE"),
        ("Phí nạp tiền từ ngân hàng liên kết là bao nhiêu?", "FEE"),

        # LIMIT queries (21 FAQs in dataset)
        ("Tôi thực hiện nạp tiền từ ngân hàng báo giao dịch quá hạn mức", "LIMIT"),
        ("Hạn mức chuyển tiền tối đa là bao nhiêu?", "LIMIT"),
        ("Tôi có thể nạp tối đa bao nhiêu tiền?", "LIMIT"),

        # TIME queries (49 FAQs in dataset)
        ("Tiền bị trừ nhưng nạp tiền không thành công, bao lâu thì tiền được hoàn?", "TIME"),
        ("Chuyển tiền mất bao lâu?", "TIME"),
        ("Thời gian xử lý giao dịch là bao lâu?", "TIME"),

        # TROUBLESHOOT queries (116 FAQs in dataset)
        ("Tôi nạp tiền từ ngân hàng Vietinbank báo thông tin thẻ không hợp lệ", "TROUBLESHOOT"),
        ("Tôi thực hiện giao dịch nạp tiền thất bại nhưng ngân hàng đã trừ tiền", "TROUBLESHOOT"),
        ("Chuyển tiền rồi mà chưa nhận được", "TROUBLESHOOT"),
        ("Giao dịch bị lỗi phải làm sao?", "TROUBLESHOOT"),

        # STATUS_CHECK queries (113 FAQs in dataset)
        ("Tôi có thể xem các giao dịch nạp tiền trong tháng như thế nào?", "STATUS_CHECK"),
        ("Kiểm tra trạng thái giao dịch", "STATUS_CHECK"),
        ("Xem lịch sử chuyển tiền", "STATUS_CHECK"),

        # REQUIREMENT queries (54 FAQs in dataset)
        ("Điều kiện để tôi liên kết ngân hàng thành công", "REQUIREMENT"),
        ("Điều kiện để tôi đăng ký tài khoản Mobile Money là gì?", "REQUIREMENT"),

        # WHY queries (20 FAQs in dataset)
        ("Tại sao tôi không rút tiền được về ngân hàng Techcombank", "WHY"),
        ("Tại sao tôi không liên kết được với thẻ quốc tế", "WHY"),

        # HOW_TO queries (218 FAQs in dataset)
        ("Tôi có thể nạp tiền từ ngân hàng vào ứng dụng VNPT Money như thế nào?", "HOW_TO"),
        ("Làm thế nào để chuyển tiền?", "HOW_TO"),
        ("Cách liên kết ngân hàng?", "HOW_TO"),
    ]

    print("=" * 80)
    print("REFINED INTENT CLASSIFICATION TEST (Based on 803 FAQs)")
    print("=" * 80)

    correct = 0
    total = len(test_queries)

    for query, expected in test_queries:
        intent, confidence, details = classifier.classify(query)
        is_correct = intent == expected
        correct += 1 if is_correct else 0

        status = "OK" if is_correct else "X "
        print(f"\n[{status}] Query: {query[:60]}...")
        print(f"     Expected: {expected:15s} | Got: {intent:15s} (conf: {confidence:.0%})")

        if not is_correct and details:
            print(f"     Matched: {details.get('keywords', [])[:3]}")

    print(f"\n{'=' * 80}")
    print(f"ACCURACY: {correct}/{total} ({correct/total*100:.1f}%)")
    print("=" * 80)
