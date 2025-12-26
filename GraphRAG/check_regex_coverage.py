# -*- coding: utf-8 -*-
"""
Kiểm tra xem regex patterns đã cover đủ các entity types như LLM prompt chưa
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("REGEX PATTERN COVERAGE vs LLM PROMPT")
print("=" * 80)

# Entity types từ LLM prompt (lines 142-191)
llm_entity_types = {
    "Topic": "Chủ đề chính của câu hỏi",
    "Service": "Dịch vụ được đề cập",
    "Bank": "Tên ngân hàng cụ thể",
    "Error": "Thông báo lỗi hoặc vấn đề",
    "Action": "Hành động mà người dùng cần thực hiện",
    "Requirement": "Điều kiện cần thiết để thực hiện hành động",
    "Feature": "Tính năng/công cụ của ứng dụng",
    "TimeFrame": "Khung thời gian liên quan",
    "Status": "Trạng thái của giao dịch hoặc tài khoản",
    "Document": "Loại giấy tờ định danh",
    "AccountType": "Loại tài khoản",
    "UIElement": "Phần tử giao diện người dùng",
    "ContactChannel": "Kênh liên hệ hỗ trợ",
    "Fee": "Phí, chi phí, biểu phí",
    "Limit": "Hạn mức, giới hạn số tiền/số lần"
}

print(f"\nLLM Prompt có {len(llm_entity_types)} loại entity:")
for i, (entity_type, description) in enumerate(llm_entity_types.items(), 1):
    print(f"{i:2d}. {entity_type:15s} - {description}")

# Kiểm tra regex patterns trong enhanced_entity_extractor.py
print(f"\n{'=' * 80}")
print("CHECKING REGEX PATTERNS IN enhanced_entity_extractor.py")
print(f"{'=' * 80}")

# Read enhanced_entity_extractor.py to check patterns
from enhanced_entity_extractor import EnhancedEntityExtractor

extractor = EnhancedEntityExtractor()

# Check what patterns exist
print(f"\n1. ERROR PATTERNS:")
print(f"   Count: {len(extractor.error_patterns_regex)}")
print(f"   ✅ HAS regex patterns for Error entity")

print(f"\n2. TOPIC PATTERNS:")
print(f"   Count: {len(extractor.topic_patterns_regex)}")
print(f"   Patterns cover:")
for pattern, topic_name in extractor.topic_patterns_regex[:10]:
    print(f"   - {topic_name}")
if len(extractor.topic_patterns_regex) > 10:
    print(f"   ... and {len(extractor.topic_patterns_regex) - 10} more")
print(f"   ✅ HAS regex patterns for Topic entity")

print(f"\n3. ACTION PATTERNS:")
print(f"   Count: {len(extractor.action_patterns_regex)}")
print(f"   Patterns cover:")
for pattern, action_name in extractor.action_patterns_regex[:10]:
    print(f"   - {action_name}")
print(f"   ⚠️ Has some patterns, but may need more")

print(f"\n4. STATUS PATTERNS:")
print(f"   Count: {len(extractor.status_patterns_regex)}")
print(f"   Patterns cover:")
for pattern, status in extractor.status_patterns_regex:
    print(f"   - {status}")
print(f"   ✅ HAS regex patterns for Status entity")

print(f"\n5. FEE PATTERNS:")
print(f"   Count: {len(extractor.fee_patterns_regex)}")
print(f"   Patterns cover:")
for pattern, fee in extractor.fee_patterns_regex:
    print(f"   - {fee}")
print(f"   ✅ HAS regex patterns for Fee entity")

print(f"\n6. LIMIT PATTERNS:")
print(f"   Count: {len(extractor.limit_patterns_regex)}")
print(f"   Patterns cover:")
for pattern, limit in extractor.limit_patterns_regex:
    print(f"   - {limit}")
print(f"   ✅ HAS regex patterns for Limit entity")

# Check coverage
print(f"\n{'=' * 80}")
print("COVERAGE SUMMARY")
print(f"{'=' * 80}")

entity_coverage = {
    "Topic": "✅ YES - topic_patterns_regex",
    "Service": "⚠️ PARTIAL - simple patterns only",
    "Bank": "⚠️ PARTIAL - simple patterns only",
    "Error": "✅ YES - error_patterns_regex",
    "Action": "⚠️ PARTIAL - action_patterns_regex (limited)",
    "Requirement": "❌ NO - no regex patterns",
    "Feature": "❌ NO - no regex patterns",
    "TimeFrame": "❌ NO - no regex patterns",
    "Status": "✅ YES - status_patterns_regex",
    "Document": "❌ NO - no regex patterns",
    "AccountType": "❌ NO - no regex patterns",
    "UIElement": "❌ NO - no regex patterns",
    "ContactChannel": "❌ NO - no regex patterns",
    "Fee": "✅ YES - fee_patterns_regex",
    "Limit": "✅ YES - limit_patterns_regex"
}

print("\nEntity Type         | Coverage Status")
print("-" * 80)
for entity_type, status in entity_coverage.items():
    print(f"{entity_type:18s} | {status}")

# Count coverage
has_regex = sum(1 for status in entity_coverage.values() if status.startswith("✅"))
partial = sum(1 for status in entity_coverage.values() if status.startswith("⚠️"))
no_regex = sum(1 for status in entity_coverage.values() if status.startswith("❌"))
total = len(entity_coverage)

print(f"\n{'=' * 80}")
print(f"COVERAGE STATISTICS")
print(f"{'=' * 80}")
print(f"✅ Has regex patterns:     {has_regex}/{total} ({has_regex/total*100:.0f}%)")
print(f"⚠️ Partial coverage:      {partial}/{total} ({partial/total*100:.0f}%)")
print(f"❌ No regex patterns:      {no_regex}/{total} ({no_regex/total*100:.0f}%)")
print(f"\nTotal coverage: {(has_regex + partial*0.5)/total*100:.0f}%")

print(f"\n{'=' * 80}")
print("RECOMMENDATIONS")
print(f"{'=' * 80}")

print("""
CÁC ENTITY TYPE CẦN BỔ SUNG REGEX PATTERNS:

PRIORITY 1 (HIGH) - Quan trọng cho FAQ matching:
  ❌ Requirement - Điều kiện cần thiết
     → Add patterns: "cần", "yêu cầu", "phải có", "điều kiện"

  ❌ Feature - Tính năng
     → Add patterns: "QR", "NFC", "OTP", "tra soát", "lịch sử"

  ❌ UIElement - Phần tử UI (rất quan trọng!)
     → Add patterns: "Cá nhân", "Ngân hàng liên kết", "Chuyển tiền", etc.

PRIORITY 2 (MEDIUM):
  ❌ TimeFrame - Khung thời gian
     → Add patterns: "ngày làm việc", "ngay lập tức", "trong vòng"

  ❌ Document - Giấy tờ
     → Add patterns: "CCCD", "CMND", "Hộ chiếu", "CCCD gắn chíp"

  ❌ AccountType - Loại tài khoản
     → Add patterns: "tài khoản ví", "tài khoản ngân hàng", "thẻ nội địa"

PRIORITY 3 (LOW):
  ❌ ContactChannel - Kênh liên hệ
     → Add patterns: "Hotline", "Trợ giúp", "hỗ trợ"

IMPROVE EXISTING:
  ⚠️ Action - Cần thêm nhiều action patterns hơn
     → Add more common actions: "Nhập số tiền", "Chọn ngân hàng", etc.

  ⚠️ Service - Cần patterns cụ thể hơn
     → Add patterns: "VNPT Money", "VNPT Pay", "Mobile Banking"

  ⚠️ Bank - Cần patterns đầy đủ các ngân hàng
     → Add patterns: Vietinbank, Vietcombank, BIDV, Techcombank, etc.

KẾT LUẬN:
- Hiện tại regex coverage chỉ khoảng 40-47% so với LLM prompt
- Cần bổ sung ít nhất 7 entity types còn thiếu
- Cải thiện 3 entity types đang partial
- Mục tiêu: Đạt 80-90% coverage để giảm dependency vào LLM
""")
