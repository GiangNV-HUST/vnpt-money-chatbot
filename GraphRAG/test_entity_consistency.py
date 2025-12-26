# -*- coding: utf-8 -*-
"""
Test Entity Extraction Consistency
Kiểm tra xem cấu trúc extraction của Query có khớp với Document không
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
from llm_entity_extractor import LLMEntityExtractor

def test_entity_structure_consistency():
    """Test if query extraction structure matches document extraction structure"""

    print("=" * 80)
    print("ENTITY STRUCTURE CONSISTENCY TEST")
    print("=" * 80)

    # Initialize extractors
    query_extractor = EnhancedEntityExtractor()
    doc_extractor = LLMEntityExtractor()

    # Get entity types from both
    query_entities, _ = query_extractor.extract_with_confidence("test query")
    doc_extraction = doc_extractor._get_empty_result()

    query_entity_types = set(k for k in query_entities.keys() if k != 'out_of_scope')
    doc_entity_types = set(doc_extraction["entities"].keys())

    print("\n📊 ENTITY TYPES COMPARISON:")
    print(f"\nDocument extraction types ({len(doc_entity_types)}):")
    for entity_type in sorted(doc_entity_types):
        print(f"  ✓ {entity_type}")

    print(f"\nQuery extraction types ({len(query_entity_types)}):")
    for entity_type in sorted(query_entity_types):
        status = "✓" if entity_type in doc_entity_types else "✗"
        print(f"  {status} {entity_type}")

    # Check consistency
    missing_in_query = doc_entity_types - query_entity_types
    extra_in_query = query_entity_types - doc_entity_types

    print("\n" + "=" * 80)
    print("CONSISTENCY CHECK:")
    print("=" * 80)

    if not missing_in_query and not extra_in_query:
        print("✅ PERFECT MATCH! Query và Document có cùng entity types.")
    else:
        if missing_in_query:
            print(f"\n❌ Entity types thiếu trong Query ({len(missing_in_query)}):")
            for entity_type in sorted(missing_in_query):
                print(f"  - {entity_type}")

        if extra_in_query:
            print(f"\n⚠️  Entity types thừa trong Query ({len(extra_in_query)}):")
            for entity_type in sorted(extra_in_query):
                print(f"  - {entity_type}")

    print("\n" + "=" * 80)
    return missing_in_query, extra_in_query


def test_real_queries():
    """Test với các câu hỏi thực tế"""

    print("\n\n" + "=" * 80)
    print("REAL QUERY EXTRACTION TEST")
    print("=" * 80)

    extractor = EnhancedEntityExtractor()

    test_queries = [
        "Phí rút tiền là bao nhiêu?",
        "Làm sao hủy liên kết ngân hàng?",
        "Giao dịch của tôi đang xử lý thì phải làm gì?",
        "Hạn mức chuyển tiền tối đa là bao nhiêu?",
        "Tôi cần CCCD để định danh không?",
        "Nạp tiền từ Vietinbank bị lỗi",
        "Kiểm tra trạng thái giao dịch ở đâu?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print(f"{'='*80}")

        entities, confidence = extractor.extract_with_confidence(query)

        print(f"\n📊 Confidence: {confidence:.2%}")
        print("\n📌 Extracted Entities:")

        # Count non-empty entities
        non_empty_count = 0
        for entity_type, values in entities.items():
            if values and entity_type != 'out_of_scope' and isinstance(values, list):
                non_empty_count += len(values)
                print(f"  {entity_type}: {values}")

        if non_empty_count == 0:
            print("  ⚠️  Không extract được entity nào!")

        print(f"\n💡 Total entities extracted: {non_empty_count}")


if __name__ == "__main__":
    # Test 1: Structure consistency
    missing, extra = test_entity_structure_consistency()

    # Test 2: Real queries
    test_real_queries()

    # Final summary
    print("\n\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)

    if not missing and not extra:
        print("✅ CẤU TRÚC EXTRACTION HOÀN TOÀN KHỚP!")
        print("   Query extraction structure = Document extraction structure")
        print("   GraphRAG sẽ hoạt động tối ưu!")
    else:
        print("❌ CẤU TRÚC EXTRACTION CHƯA KHỚP!")
        print(f"   - Thiếu {len(missing)} entity types trong Query")
        print(f"   - Thừa {len(extra)} entity types trong Query")
        print("   ⚠️  Cần sửa để GraphRAG hoạt động tốt hơn!")

    print("=" * 80)
