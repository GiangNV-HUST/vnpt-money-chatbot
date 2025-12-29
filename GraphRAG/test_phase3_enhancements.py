#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Phase 3 Enhancements - Status, Conditional, and Keyword Matching

Tests the enhanced Case matching after Neo4j rebuild and code enhancements.
Expected: 90%+ pass rate (up from 55%)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from enhanced_entity_extractor import EnhancedEntityExtractor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_case_matching():
    """Test enhanced case matching with new features"""

    engine = Neo4jGraphRAGEngine()
    extractor = EnhancedEntityExtractor()

    print("="*80)
    print("PHASE 3 ENHANCEMENT TESTS - Case Matching")
    print("="*80)

    test_cases = [
        # ===== METHOD-BASED (should maintain 100% pass rate) =====
        {
            "category": "Method-based (FAQ_0)",
            "query": "tôi muốn nạp tiền bằng chuyển khoản ngân hàng",
            "expected_keywords": ["chuyển khoản", "QR"],
            "should_not_contain": ["liên kết"],
            "description": "Feature extraction - chuyển khoản"
        },
        {
            "category": "Method-based (FAQ_0)",
            "query": "nạp tiền từ ngân hàng liên kết như thế nào",
            "expected_keywords": ["liên kết", "ngân hàng liên kết"],
            "should_not_contain": ["chuyển khoản", "QR"],
            "description": "Feature extraction - liên kết"
        },

        # ===== STATUS-BASED (target 90%+ from 50%) =====
        {
            "category": "Status-based (FAQ_2)",
            "query": "nạp tiền thất bại nhưng ngân hàng đã trừ tiền",
            "expected_keywords": ["thất bại", "không thành công"],
            "should_not_contain": ["thành công", "đang xử lý"],
            "description": "Status extraction - thất bại"
        },
        {
            "category": "Status-based (FAQ_8)",
            "query": "giao dịch nạp tiền đang xử lý nhưng bank đã trừ",
            "expected_keywords": ["đang xử lý"],
            "should_not_contain": ["thất bại", "thành công"],
            "description": "Status extraction - đang xử lý"
        },
        {
            "category": "Status-based",
            "query": "nạp tiền thành công rồi",
            "expected_keywords": ["thành công"],
            "should_not_contain": ["thất bại", "không thành công"],
            "description": "Status extraction - thành công"
        },

        # ===== CONDITIONAL MATCHING (NEW) =====
        {
            "category": "Conditional (FAQ_2)",
            "query": "VNPT Money đã nhận được tiền rồi",
            "expected_keywords": ["đã nhận được tiền", "đã nhận tiền"],
            "should_not_contain": ["chưa nhận"],
            "description": "Conditional - đã nhận tiền"
        },
        {
            "category": "Conditional (FAQ_2)",
            "query": "VNPT Money chưa nhận được tiền",
            "expected_keywords": ["chưa nhận được tiền", "chưa nhận tiền"],
            "should_not_contain": ["đã nhận"],
            "description": "Conditional - chưa nhận tiền"
        },

        # ===== COMBINED TESTS (Status + Feature) =====
        {
            "category": "Combined (FAQ_2 + Method)",
            "query": "chuyển khoản nạp tiền thất bại",
            "expected_keywords": ["chuyển khoản", "thất bại"],
            "should_not_contain": [],
            "description": "Combined - method + status"
        },
    ]

    passed = 0
    failed = 0
    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(test_cases)}: {test['category']}")
        print(f"Query: '{test['query']}'")
        print(f"Expected: {test['expected_keywords']}")
        print(f"{'='*80}")

        try:
            # Extract entities
            entities = extractor.extract(test['query'])
            print(f"\n📊 Extracted Entities:")
            for entity_type, values in entities.items():
                if values:
                    print(f"  - {entity_type}: {values}")

            # Query with Neo4j RAG
            result = engine.query(test['query'], top_k=1)

            # Extract answer and score from result dict
            if result and isinstance(result, dict):
                answer = result.get('answer', '')
                score = result.get('confidence', 0)

                print(f"\n✅ Got result (score: {score:.2f})")
                print(f"Answer preview: {answer[:200]}...")

                # Check if expected keywords are in answer
                answer_lower = answer.lower()
                has_expected = any(keyword.lower() in answer_lower for keyword in test['expected_keywords'])
                has_unwanted = any(keyword.lower() in answer_lower for keyword in test['should_not_contain'])

                if has_expected and not has_unwanted:
                    print(f"✅ PASS - Contains expected keywords, no unwanted keywords")
                    passed += 1
                    results.append({
                        'test': test['description'],
                        'status': 'PASS',
                        'score': score
                    })
                elif has_unwanted:
                    print(f"❌ FAIL - Contains unwanted keywords: {test['should_not_contain']}")
                    failed += 1
                    results.append({
                        'test': test['description'],
                        'status': 'FAIL',
                        'reason': 'Unwanted keywords found',
                        'score': score
                    })
                else:
                    print(f"❌ FAIL - Missing expected keywords: {test['expected_keywords']}")
                    failed += 1
                    results.append({
                        'test': test['description'],
                        'status': 'FAIL',
                        'reason': 'Expected keywords not found',
                        'score': score
                    })
            else:
                print(f"❌ FAIL - No result returned")
                failed += 1
                results.append({
                    'test': test['description'],
                    'status': 'FAIL',
                    'reason': 'No result',
                    'score': 0
                })

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
            results.append({
                'test': test['description'],
                'status': 'ERROR',
                'reason': str(e),
                'score': 0
            })

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n📊 Results:")
    print(f"  Total tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Pass rate: {pass_rate:.1f}%")

    print(f"\n📋 Detailed Results:")
    for result in results:
        status_icon = "✅" if result['status'] == 'PASS' else "❌"
        print(f"{status_icon} {result['test']}: {result['status']} (score: {result.get('score', 0):.2f})")
        if 'reason' in result:
            print(f"   Reason: {result['reason']}")

    # Target assessment
    print(f"\n🎯 Target Assessment:")
    if pass_rate >= 90:
        print(f"✅ TARGET ACHIEVED! Pass rate {pass_rate:.1f}% >= 90%")
    elif pass_rate >= 70:
        print(f"⚠️  APPROACHING TARGET. Pass rate {pass_rate:.1f}% (need 90%)")
    else:
        print(f"❌ BELOW TARGET. Pass rate {pass_rate:.1f}% (need 90%)")

    return pass_rate >= 90


def test_neo4j_case_structure():
    """Verify Neo4j Case nodes have new fields (keywords, status_values)"""

    print(f"\n{'='*80}")
    print("NEO4J CASE STRUCTURE VERIFICATION")
    print(f"{'='*80}")

    from neo4j_connector import Neo4jConnector

    conn = Neo4jConnector()

    try:
        # Check if keywords and status_values fields exist
        result = conn.execute_query("""
        MATCH (c:Case)
        WHERE c.keywords IS NOT NULL OR c.status_values IS NOT NULL
        RETURN count(c) as cases_with_metadata,
               sum(CASE WHEN c.keywords IS NOT NULL THEN 1 ELSE 0 END) as with_keywords,
               sum(CASE WHEN c.status_values IS NOT NULL THEN 1 ELSE 0 END) as with_status
        """)

        if result:
            row = result[0]
            print(f"\n✅ Cases with metadata fields:")
            print(f"  - Total with keywords or status: {row[0]}")
            print(f"  - With keywords: {row[1]}")
            print(f"  - With status_values: {row[2]}")

        # Sample cases with keywords
        result = conn.execute_query("""
        MATCH (c:Case)
        WHERE c.keywords IS NOT NULL AND size(c.keywords) > 0
        RETURN c.name, c.keywords, c.status_values
        LIMIT 5
        """)

        print(f"\n📋 Sample Cases with Keywords:")
        for i, row in enumerate(result, 1):
            name = row[0] or "(No name)"
            keywords = row[1] or []
            status = row[2] or []
            print(f"\n{i}. {name[:60]}...")
            print(f"   Keywords: {keywords}")
            print(f"   Status: {status}")

        conn.close()

    except Exception as e:
        print(f"❌ Error verifying structure: {e}")
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting Phase 3 Enhancement Tests...")
    print()

    # First verify Neo4j structure
    test_neo4j_case_structure()

    # Then test case matching
    success = test_case_matching()

    print(f"\n{'='*80}")
    if success:
        print("✅ PHASE 3 TESTS PASSED - Ready for comprehensive testing!")
    else:
        print("⚠️  PHASE 3 TESTS INCOMPLETE - Review failed cases")
    print(f"{'='*80}")
