# -*- coding: utf-8 -*-
"""
Test script for ContactChannel extraction fix
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
from neo4j_rag_engine import Neo4jGraphRAGEngine

def test_entity_extraction():
    """Test entity extraction"""
    print("=" * 80)
    print("TEST 1: Entity Extraction")
    print("=" * 80)

    extractor = EnhancedEntityExtractor()
    query = "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

    print(f"\nQuery: {query}\n")

    entities, confidence = extractor.extract_with_confidence(query)

    print("Extracted Entities:")
    for entity_type, values in entities.items():
        if values:
            print(f"  {entity_type}: {values}")

    print(f"\nConfidence: {confidence:.2%}")

    # Check if expected entities were extracted
    expected_contact = "Vinaphone: 18001091"
    success = expected_contact in entities.get("ContactChannel", [])

    if success:
        print(f"\n✅ SUCCESS: '{expected_contact}' was extracted!")
    else:
        print(f"\n❌ FAILED: '{expected_contact}' was NOT extracted")
        print(f"   Got: {entities.get('ContactChannel', [])}")

    return success

def test_end_to_end():
    """Test full chatbot query"""
    print("\n" + "=" * 80)
    print("TEST 2: End-to-End Query")
    print("=" * 80)

    engine = Neo4jGraphRAGEngine()
    query = "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

    print(f"\nQuery: {query}\n")

    result = engine.query(query)

    print("Status:", result.get("status"))
    print("Confidence:", f"{result.get('confidence', 0)}%")

    answer = result.get("answer", "")
    print(f"\nAnswer:\n{answer}\n")

    # Check if answer contains Vinaphone contact
    success = "18001091" in answer

    if success:
        print("✅ SUCCESS: Answer contains Vinaphone contact (18001091)")
    else:
        print("❌ FAILED: Answer does NOT contain Vinaphone contact")

    return success

def main():
    print("\n🧪 Testing ContactChannel Extraction Fix\n")

    test1_pass = test_entity_extraction()
    test2_pass = test_end_to_end()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Entity Extraction): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (End-to-End Query):  {'✅ PASS' if test2_pass else '❌ FAIL'}")

    if test1_pass and test2_pass:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
