# -*- coding: utf-8 -*-
"""
Phân tích root causes của các lỗi - chủ yếu là entity extraction vs Neo4j matching
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
from neo4j_connector import Neo4jConnector

print("=" * 80)
print("ROOT CAUSE ANALYSIS: Entity Extraction vs Neo4j Matching")
print("=" * 80)

extractor = EnhancedEntityExtractor()
connector = Neo4jConnector()

# Test cases
test_cases = [
    {
        "name": "Hủy nạp tiền tự động",
        "query": "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?",
        "expected_faq_keywords": ["hủy", "nạp tiền", "tự động"],
        "expected_steps": 6
    },
    {
        "name": "Thanh toán hóa đơn viễn thông",
        "query": "Tôi muốn thanh toán hóa đơn viễn thông qua VNPT Money",
        "expected_faq_keywords": ["thanh toán", "hóa đơn", "viễn thông"],
        "expected_steps": 6
    },
    {
        "name": "Thanh toán hóa đơn điện",
        "query": "Tôi muốn thanh toán hóa đơn tiền điện qua VNPT Money",
        "expected_faq_keywords": ["thanh toán", "hóa đơn", "điện"],
        "expected_steps": 5
    },
    {
        "name": "Mua vé máy bay",
        "query": "Làm sao mua vé máy bay trên VNPT Money?",
        "expected_faq_keywords": ["mua vé", "máy bay"],
        "expected_steps": 3
    },
    {
        "name": "Rút tiền về ngân hàng",
        "query": "Làm sao rút tiền về ngân hàng từ VNPT Money?",
        "expected_faq_keywords": ["rút tiền", "ngân hàng"],
        "expected_steps": 5
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"{i}. {test['name']}")
    print(f"{'=' * 80}")

    query = test['query']
    print(f"Query: {query}")

    # Step 1: Extract entities
    print(f"\n{'─' * 40}")
    print("STEP 1: Entity Extraction")
    print(f"{'─' * 40}")

    entities, confidence = extractor.extract_with_confidence(query)
    topics = entities.get('Topic', [])
    actions = entities.get('Action', [])

    print(f"Topics extracted: {topics}")
    print(f"Actions extracted: {actions}")
    print(f"Confidence: {confidence:.0%}")

    # Step 2: Query Neo4j with extracted entities
    print(f"\n{'─' * 40}")
    print("STEP 2: Neo4j Query with Extracted Entities")
    print(f"{'─' * 40}")

    # Build cypher query using extracted topics
    if topics:
        topic = topics[0]  # Use first topic
        cypher_query = """
        MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
        WHERE toLower(faq.question) CONTAINS $topic_lower
        MATCH (p)-[:HAS_STEP]->(s:Step)
        WITH faq, p, count(s) as step_count
        RETURN faq.id as faq_id,
               faq.question as question,
               step_count
        ORDER BY step_count DESC
        LIMIT 5
        """

        with connector.driver.session(database=connector.database) as session:
            results = session.run(cypher_query, {"topic_lower": topic.lower()}).data()

        print(f"Searching Neo4j with topic: '{topic}'")
        print(f"Found {len(results)} FAQs:")

        for j, r in enumerate(results, 1):
            print(f"  {j}. {r['faq_id']}: {r['question'][:60]}... ({r['step_count']} steps)")

    # Step 3: Query Neo4j with EXPECTED keywords
    print(f"\n{'─' * 40}")
    print("STEP 3: Neo4j Query with EXPECTED Keywords")
    print(f"{'─' * 40}")

    expected_keywords = test['expected_faq_keywords']

    # Build cypher with ALL expected keywords
    where_conditions = " AND ".join([
        f"toLower(faq.question) CONTAINS '{kw}'"
        for kw in expected_keywords
    ])

    cypher_query2 = f"""
    MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
    WHERE {where_conditions}
    MATCH (p)-[:HAS_STEP]->(s:Step)
    WITH faq, p, count(s) as step_count
    RETURN faq.id as faq_id,
           faq.question as question,
           step_count
    ORDER BY step_count DESC
    LIMIT 5
    """

    with connector.driver.session(database=connector.database) as session:
        results2 = session.run(cypher_query2).data()

    print(f"Searching Neo4j with keywords: {expected_keywords}")
    print(f"Found {len(results2)} FAQs:")

    for j, r in enumerate(results2, 1):
        print(f"  {j}. {r['faq_id']}: {r['question'][:60]}... ({r['step_count']} steps)")

    # Step 4: Analysis
    print(f"\n{'─' * 40}")
    print("ANALYSIS")
    print(f"{'─' * 40}")

    if topics:
        extracted_topic = topics[0]
        has_all_keywords = all(kw in extracted_topic.lower() for kw in expected_keywords)

        if has_all_keywords:
            print(f"✅ GOOD: Extracted topic '{extracted_topic}' contains all expected keywords")
        else:
            missing = [kw for kw in expected_keywords if kw not in extracted_topic.lower()]
            print(f"⚠️ PARTIAL: Extracted topic '{extracted_topic}' is missing: {missing}")
            print(f"   → This can cause wrong FAQ matching!")
    else:
        print(f"❌ BAD: No topic extracted!")

    if len(results2) == 0:
        print(f"⚠️ WARNING: No FAQ in Neo4j matches all expected keywords!")
        print(f"   → The FAQ might not exist or keywords are wrong")
    elif topics and len(results) < len(results2):
        print(f"⚠️ ISSUE: Extracted entities find FEWER FAQs ({len(results)}) than expected keywords ({len(results2)})")
        print(f"   → Entity extraction is TOO GENERIC or MISSING keywords")

connector.close()

print(f"\n{'=' * 80}")
print("SUMMARY OF ROOT CAUSES")
print(f"{'=' * 80}")

print("""
Các loại lỗi chính:

1. **Entity extraction quá generic**
   - Extract: "Nạp tiền" thay vì "Hủy nạp tiền tự động"
   - Kết quả: Match nhiều FAQs sai, không match FAQ đúng

2. **Entity extraction thiếu keywords**
   - Extract: "Thanh toán" thay vì "Thanh toán hóa đơn điện"
   - Kết quả: Match FAQs generic, không match FAQs specific

3. **Neo4j không có FAQ với keywords cụ thể**
   - Tìm FAQ với "mua vé máy bay" nhưng graph chỉ có "mua vé"
   - Kết quả: Phải dùng generic keywords, có thể match sai

4. **LLM variability**
   - Cùng query nhưng LLM extract khác nhau mỗi lần
   - Kết quả: Tests không stable 100%

GIẢI PHÁP:
✅ Add specific regex patterns (đã làm)
✅ Lower LLM threshold để trigger nhiều hơn (đã làm)
🔄 Cần: Add more specific patterns cho các edge cases
🔄 Cần: Improve Neo4j fallback query với better keyword matching
""")
