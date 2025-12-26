# -*- coding: utf-8 -*-
"""
Test các variations của cùng một query để xem entity extraction stability
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor

extractor = EnhancedEntityExtractor()

print("=" * 80)
print("ENTITY EXTRACTION - QUERY VARIATIONS TEST")
print("=" * 80)

test_cases = [
    # Thanh toán hóa đơn variations
    ("Thanh toán hóa đơn điện", [
        "Tôi muốn thanh toán hóa đơn tiền điện qua VNPT Money",
        "Làm sao thanh toán tiền điện trên VNPT Money?",
        "Hướng dẫn tôi thanh toán hóa đơn điện",
        "Thanh toán cước điện qua app VNPT Money"
    ]),

    # Nạp tiền variations
    ("Nạp tiền điện thoại", [
        "Tôi muốn nạp tiền điện thoại qua VNPT Money",
        "Làm sao nạp tiền điện thoại trên app?",
        "Nạp cước điện thoại qua VNPT Money",
        "Hướng dẫn nạp tiền cho số điện thoại"
    ]),

    # Hủy dịch vụ variations
    ("Hủy nạp tiền tự động", [
        "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?",
        "Làm sao hủy nạp tiền tự động?",
        "Hướng dẫn hủy dịch vụ nạp tiền tự động",
        "Cách hủy nạp tiền tự động trên VNPT Money"
    ]),

    # Chuyển tiền variations
    ("Chuyển tiền", [
        "Tôi muốn chuyển tiền đến ngân hàng",
        "Làm sao chuyển tiền từ VNPT Money ra ngân hàng?",
        "Hướng dẫn chuyển tiền về tài khoản ngân hàng",
        "Cách chuyển tiền ra ngoài"
    ])
]

for category, queries in test_cases:
    print(f"\n{'=' * 80}")
    print(f"CATEGORY: {category}")
    print(f"{'=' * 80}")

    topics_extracted = []
    for i, query in enumerate(queries, 1):
        entities, confidence = extractor.extract_with_confidence(query)
        topics = entities.get('Topic', [])

        print(f"\n{i}. Query: {query}")
        print(f"   Topics: {topics}")
        print(f"   Confidence: {confidence:.0%}")

        topics_extracted.append(tuple(topics))

    # Check consistency
    unique_topics = set(topics_extracted)
    if len(unique_topics) == 1:
        print(f"\n✅ CONSISTENT - All variations extracted same topics: {topics_extracted[0]}")
    else:
        print(f"\n⚠️ INCONSISTENT - Got {len(unique_topics)} different topic sets:")
        for t in unique_topics:
            count = topics_extracted.count(t)
            print(f"   {count}/{len(queries)}: {t}")

print(f"\n{'=' * 80}")
print("SUMMARY")
print(f"{'=' * 80}")
print("\nThis test shows how stable entity extraction is across query variations.")
print("Consistent extraction is important for reliable FAQ matching.")
