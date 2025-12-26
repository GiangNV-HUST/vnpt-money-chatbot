# -*- coding: utf-8 -*-
"""
So sánh chi tiết LLM extraction vs Regex extraction để tìm gaps
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
import config

extractor = EnhancedEntityExtractor()

print("=" * 80)
print("LLM vs REGEX EXTRACTION COMPARISON")
print("=" * 80)

# Test cases covering various scenarios
test_cases = [
    # Topic extraction
    "Tôi muốn hủy dịch vụ nạp tiền tự động",
    "Làm sao nạp tiền điện thoại qua VNPT Money?",
    "Thanh toán hóa đơn viễn thông",
    "Chuyển tiền đến ngân hàng",
    "Rút tiền về tài khoản ngân hàng",

    # Action extraction
    "Nhập số tiền cần chuyển",
    "Chọn ngân hàng muốn liên kết",
    "Bấm vào nút Xác nhận",
    "Vào mục Cá nhân để cài đặt",

    # Requirement extraction
    "Nạp tiền cần những điều kiện gì?",
    "Yêu cầu gì để mở tài khoản VNPT Money?",
    "Phải có CCCD mới mở được không?",

    # Feature extraction
    "App có hỗ trợ thanh toán bằng QR không?",
    "Làm sao xem lịch sử giao dịch?",
    "Có sinh trắc học để đăng nhập không?",

    # Multi-entity queries
    "Chuyển tiền từ Vietinbank sang VNPT Money cần điều kiện gì?",
    "Liên kết thẻ ATM Techcombank vào mục nào?",

    # Complex process queries
    "Hủy nạp tiền tự động thì vào mục nào và bấm nút nào?",
    "Đăng ký thanh toán tự động hóa đơn điện",
]

# Re-enable LLM fallback
config.ENABLE_LLM_FALLBACK = True

gaps_by_entity_type = {}

for i, query in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"{i}. {query}")
    print(f"{'=' * 80}")

    # Get regex-only extraction
    original_llm_setting = config.ENABLE_LLM_FALLBACK
    config.ENABLE_LLM_FALLBACK = False
    regex_entities, regex_conf = extractor.extract_with_confidence(query)

    # Get hybrid extraction (with LLM)
    config.ENABLE_LLM_FALLBACK = True
    hybrid_entities, hybrid_conf = extractor.extract_with_confidence(query)
    config.ENABLE_LLM_FALLBACK = original_llm_setting

    # Compare
    print(f"\n{'─' * 40}")
    print("REGEX EXTRACTION:")
    print(f"{'─' * 40}")
    for entity_type, values in regex_entities.items():
        if values:
            print(f"  {entity_type}: {values}")
    print(f"  Confidence: {regex_conf:.0%}")

    print(f"\n{'─' * 40}")
    print("HYBRID EXTRACTION (Regex + LLM):")
    print(f"{'─' * 40}")
    for entity_type, values in hybrid_entities.items():
        if values:
            print(f"  {entity_type}: {values}")
    print(f"  Confidence: {hybrid_conf:.0%}")

    # Find gaps
    print(f"\n{'─' * 40}")
    print("GAPS (Hybrid found but Pure Regex missed):")
    print(f"{'─' * 40}")

    has_gaps = False
    for entity_type, hybrid_vals in hybrid_entities.items():
        if not hybrid_vals:
            continue

        regex_vals = regex_entities.get(entity_type, [])

        # Check if Hybrid found something regex didn't
        missing = []
        for hybrid_val in hybrid_vals:
            # Check if this value or similar value exists in regex results
            found = any(
                hybrid_val.lower() in regex_val.lower() or
                regex_val.lower() in hybrid_val.lower()
                for regex_val in regex_vals
            )
            if not found:
                missing.append(hybrid_val)

        if missing:
            has_gaps = True
            print(f"  ⚠️ {entity_type}: {missing}")

            # Track gaps
            if entity_type not in gaps_by_entity_type:
                gaps_by_entity_type[entity_type] = []
            gaps_by_entity_type[entity_type].extend(missing)

    if not has_gaps:
        print(f"  ✅ No gaps - Regex matched LLM!")

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY OF GAPS")
print(f"{'=' * 80}")

if gaps_by_entity_type:
    print(f"\nFound gaps in {len(gaps_by_entity_type)} entity types:\n")

    for entity_type, gaps in sorted(gaps_by_entity_type.items()):
        print(f"\n{entity_type} ({len(gaps)} gaps):")
        print(f"{'─' * 40}")

        # Group similar gaps
        unique_gaps = list(set(gaps))
        for gap in sorted(unique_gaps):
            count = gaps.count(gap)
            print(f"  • {gap} ({count}x)")
else:
    print("\n✅ NO GAPS FOUND - Regex patterns are comprehensive!")

print(f"\n{'=' * 80}")
print("RECOMMENDATIONS")
print(f"{'=' * 80}")

if gaps_by_entity_type:
    print("\nBased on gaps found, consider adding these patterns:\n")

    for entity_type, gaps in sorted(gaps_by_entity_type.items()):
        print(f"\n{entity_type}:")
        unique_gaps = list(set(gaps))
        for gap in sorted(unique_gaps)[:5]:  # Show top 5
            # Suggest pattern
            gap_lower = gap.lower()

            # Common pattern suggestions
            if ' ' in gap_lower:
                # Multi-word: exact match or partial
                pattern = f'r"{gap_lower}"'
            else:
                # Single word: word boundary
                pattern = f'r"\\b{gap_lower}\\b"'

            print(f"  ({pattern}, \"{gap}\"),")
else:
    print("\n✅ Regex patterns are already comprehensive!")
    print("No additional patterns needed at this time.")
