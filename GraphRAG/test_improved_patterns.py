# -*- coding: utf-8 -*-
"""
Test improved regex patterns
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
import config

# Disable LLM to test pure regex
config.ENABLE_LLM_FALLBACK = False

extractor = EnhancedEntityExtractor()

test_queries = [
    ('Yêu cầu gì để mở tài khoản VNPT Money?', 'Action', ['Mở tài khoản']),
    ('Phải có CCCD mới mở được không?', 'Requirement', ['Có CCCD']),
    ('Nhập số tiền cần chuyển', 'Topic', ['Chuyển tiền']),
    ('Hủy dịch vụ nạp tiền tự động', 'Topic', ['Hủy dịch vụ']),
    ('Tôi muốn định danh tài khoản', 'Topic', ['Định danh']),
    ('Xem lịch sử giao dịch', 'Action', ['Xem lịch sử giao dịch']),
    ('Bấm vào nút Xác nhận', 'UIElement', ['Xác nhận']),
]

print("=" * 80)
print("TEST IMPROVED REGEX PATTERNS")
print("=" * 80)

passed = 0
total = 0

for query, entity_type, expected_vals in test_queries:
    entities, conf = extractor.extract_with_confidence(query)
    extracted = entities.get(entity_type, [])

    # Check if any expected value is in extracted
    match = any(
        any(exp.lower() in ext.lower() or ext.lower() in exp.lower()
            for ext in extracted)
        for exp in expected_vals
    )

    total += 1
    if match:
        passed += 1
        status = "✅"
    else:
        status = "❌"

    print(f"\n{status} Query: {query}")
    print(f"   Entity Type: {entity_type}")
    print(f"   Expected: {expected_vals}")
    print(f"   Extracted: {extracted}")
    print(f"   Confidence: {conf:.0%}")

print(f"\n{'=' * 80}")
print(f"RESULTS: {passed}/{total} ({passed/total*100:.0f}%)")
print(f"{'=' * 80}")
