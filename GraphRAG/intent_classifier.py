# -*- coding: utf-8 -*-
"""
Intent Classification Module
Classifies user queries into different intent types for better routing
"""

from typing import Dict, Tuple
import re


class IntentClassifier:
    """Classify user intent to improve query understanding"""

    def __init__(self):
        """Initialize intent patterns"""

        # Intent patterns with weights
        self.intent_patterns = {
            "TROUBLESHOOT": {
                "patterns": [
                    # Problem indicators
                    r"(chưa|không|ko|chưa được|không được).*(nhận|có|về)",
                    r"(bị|gặp|có).*(lỗi|vấn đề|sự cố|trục trặc)",
                    r"(thất bại|fail|error|sai|lỗi)",
                    r"tại sao (chưa|không|ko)",
                    r"làm sao để (khắc phục|sửa|fix)",
                    r"phải làm (gì|thế nào|sao).*(khi|nếu).*(lỗi|sự cố|vấn đề)",
                    r"(giao dịch|tiền).*(chưa|không).*(về|nhận|tới)",
                    # Checking status after action
                    r"(đã|rồi).*(mà|nhưng).*(chưa|không)",
                    r"thực hiện.*(nhưng|mà).*(chưa|không)",
                    # Transaction processing but money deducted (CRITICAL)
                    r"(đang\s+xử\s+lý|processing).*(đã|bị).*(trừ|mất)",
                    r"(đã|bị).*(trừ|mất).*(đang\s+xử\s+lý|processing)",
                    r"báo.*(đang\s+xử\s+lý).*(đã|bị)\s+trừ",
                    r"trạng\s+thái.*(đang\s+xử\s+lý).*(ngân\s+hàng|tài\s+khoản).*(trừ|mất)",
                    # Biometric troubleshooting (CRITICAL)
                    r"(sinh\s*trắc|ekyc).*(báo|hiện|xuất\s*hiện).*(lỗi|sai)",
                    r"(hệ\s*thống|app).*(báo|hiện).*(lỗi|sai).*(sinh\s*trắc|ekyc)",
                    r"báo\s*lỗi.*(sinh\s*trắc|ekyc|ngày\s*sinh|định\s*danh|cmnd|cccd)",
                    r"(ngày\s*sinh|định\s*danh|cmnd|cccd).*(không\s*khớp|không\s*đúng|sai)",
                    r"(sinh\s*trắc|ekyc).*(thất\s*bại|không\s*thành\s*công)",
                    r"(không|chưa).*(sinh\s*trắc|ekyc).*(được|thành\s*công)",
                ],
                "keywords": [
                    "chưa nhận được", "không nhận được", "bị lỗi", "gặp sự cố",
                    "thất bại", "không thành công", "chưa về", "phải làm gì",
                    "tại sao", "làm sao", "khắc phục", "đang xử lý", "đã trừ tiền",
                    "báo lỗi", "sinh trắc", "ekyc", "ngày sinh", "định danh"
                ],
                "weight": 2.0  # High priority for troubleshooting
            },

            "HOW_TO": {
                "patterns": [
                    r"(làm thế nào|làm sao|cách|như thế nào).*(để|cho|thì|\?)",
                    r"(hướng dẫn|chỉ dẫn|chỉ cách)",
                    r"(muốn|cần).*(làm|thực hiện)",
                    r"(tôi có thể|có thể).*(không|được)",
                    r"(bước|step).*(để|cho)",
                    r"^(cách|how to)",
                    # NEW: "muốn...phải làm gì" pattern (common Vietnamese question)
                    r"(muốn|cần).*(phải làm gì|làm gì|thế nào)",
                    r"(phải làm gì|làm như thế nào).*(để|cho)",
                    # NEW: Direct action questions
                    r"(mở khóa|khóa|hủy|đăng ký|tạo).*(tài khoản|ví).*(làm|thế nào|phải)",
                    # CRITICAL: "thực hiện...như thế nào" pattern (verb + như thế nào)
                    r"(thực hiện|làm|thao tác|tiến hành).*(như thế nào|thế nào|\?)",
                    r"(giao dịch|chuyển tiền|nạp tiền|rút tiền).*(như thế nào|thế nào)(\?|$)",
                ],
                "keywords": [
                    "làm thế nào", "như thế nào", "cách", "hướng dẫn", "bước",
                    "quy trình", "thủ tục", "thao tác", "phải làm gì",
                    "làm gì", "muốn", "thực hiện"
                ],
                "weight": 1.5
            },

            "INFO_REQUEST": {
                "patterns": [
                    r"(là gì|what is|nghĩa là)",
                    r"(có|được|bao nhiêu).*(phí|fee|charge)",
                    r"(thời gian|bao lâu|mất bao lâu)",
                    r"(giới hạn|hạn mức|limit)",
                    r"(yêu cầu|điều kiện|requirements)",
                    r"^(có|được|có thể)",
                ],
                "keywords": [
                    "là gì", "phí", "giá", "mất bao lâu", "thời gian",
                    "hạn mức", "điều kiện", "yêu cầu", "thông tin"
                ],
                "weight": 1.0
            },

            "STATUS_CHECK": {
                "patterns": [
                    r"(kiểm tra|check|xem|tra cứu).*(trạng thái|status|tình trạng)",
                    r"(xem|kiểm tra).*(giao dịch|transaction)",
                    r"giao dịch.*(đang|đã|chưa)",
                ],
                "keywords": [
                    "kiểm tra", "tra cứu", "xem", "trạng thái",
                    "tình trạng", "lịch sử"
                ],
                "weight": 1.3
            },
        }

    def classify(self, query: str) -> Tuple[str, float, Dict]:
        """
        Classify user query intent

        Args:
            query: User query string

        Returns:
            Tuple of (intent_name, confidence, details)
        """
        query_lower = query.lower().strip()

        intent_scores = {}
        matched_patterns = {}

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

            if weighted_score > 0:
                intent_scores[intent] = weighted_score
                matched_patterns[intent] = {
                    "patterns": patterns_matched,
                    "keywords": keywords_matched,
                    "raw_score": score,
                    "weighted_score": weighted_score
                }

        # Get best intent
        if not intent_scores:
            return "GENERAL", 0.0, {}

        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent_name = best_intent[0]

        # Calculate confidence (normalize by max possible score)
        max_possible = len(self.intent_patterns[intent_name]["patterns"]) + \
                      len(self.intent_patterns[intent_name]["keywords"]) * 0.5
        max_possible *= self.intent_patterns[intent_name]["weight"]

        confidence = min(best_intent[1] / max_possible, 1.0) if max_possible > 0 else 0.0

        return intent_name, confidence, matched_patterns.get(intent_name, {})

    def is_troubleshooting_query(self, query: str) -> bool:
        """Quick check if query is about troubleshooting"""
        intent, confidence, _ = self.classify(query)
        return intent == "TROUBLESHOOT" and confidence > 0.3


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    classifier = IntentClassifier()

    test_queries = [
        # Troubleshooting queries
        "Tôi thực hiện giao dịch chuyển tiền đến ngân hàng nhưng tài khoản thụ hưởng chưa nhận được thì phải làm thế nào?",
        "Chuyển tiền rồi mà chưa nhận được",
        "Gặp lỗi khi chuyển tiền",
        "Tại sao tiền chưa về tài khoản",

        # How-to queries
        "Làm thế nào để chuyển tiền đến ngân hàng?",
        "Hướng dẫn nạp tiền vào ví",
        "Cách liên kết ngân hàng",

        # Info queries
        "Chuyển tiền có mất phí không?",
        "Hạn mức chuyển tiền là bao nhiêu?",
        "Thời gian chuyển tiền mất bao lâu?",

        # Status check
        "Kiểm tra trạng thái giao dịch",
        "Xem lịch sử chuyển tiền",
    ]

    print("=" * 80)
    print("INTENT CLASSIFICATION TEST")
    print("=" * 80)

    for query in test_queries:
        intent, confidence, details = classifier.classify(query)

        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"Intent: {intent} (Confidence: {confidence:.2%})")

        if details:
            if details.get("patterns"):
                print(f"  Matched patterns: {len(details['patterns'])}")
            if details.get("keywords"):
                print(f"  Matched keywords: {details['keywords']}")
            print(f"  Score: {details.get('raw_score', 0):.1f} (weighted: {details.get('weighted_score', 0):.2f})")
