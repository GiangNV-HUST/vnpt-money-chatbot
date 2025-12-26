# -*- coding: utf-8 -*-
"""
Debug why "Thanh toán hóa đơn" cases all fail
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
from neo4j_connector import Neo4jConnector

print("=" * 80)
print("DEBUG: Thanh toán hóa đơn entity extraction")
print("=" * 80)

extractor = EnhancedEntityExtractor()

# Test query
query = "Tôi muốn thanh toán hóa đơn tiền điện qua VNPT Money"

print(f"\nQuery: {query}")
print("-" * 80)

# Extract entities
entities, confidence = extractor.extract_with_confidence(query)

print(f"\n📊 Extracted Entities:")
print(f"   Topics: {entities.get('Topic', [])}")
print(f"   Actions: {entities.get('Action', [])}")
print(f"   UIElements: {entities.get('UIElement', [])}")
print(f"   Confidence: {confidence:.0%}")

# Check in Neo4j
print("\n" + "=" * 80)
print("CHECKING NEO4J FOR 'THANH TOÁN HÓA ĐƠN' FAQs")
print("=" * 80)

connector = Neo4jConnector()

# Query 1: Search for FAQs with "thanh toán" + "hóa đơn"
query1 = """
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
WHERE toLower(faq.question) CONTAINS 'thanh toán'
  AND toLower(faq.question) CONTAINS 'hóa đơn'
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count
RETURN faq.id as faq_id,
       faq.question as question,
       p.name as process_name,
       step_count
ORDER BY step_count DESC
LIMIT 10
"""

with connector.driver.session(database=connector.database) as session:
    results1 = session.run(query1).data()

print(f"\nFound {len(results1)} FAQs with 'thanh toán' + 'hóa đơn':")
for i, r in enumerate(results1, 1):
    print(f"\n{i}. {r['faq_id']}: {r['question'][:80]}...")
    print(f"   Process: {r['process_name']}")
    print(f"   Steps: {r['step_count']}")

# Query 2: Search for FAQs with "thanh toán" + "điện"
print("\n" + "=" * 80)
print("FAQs with 'thanh toán' + 'điện':")
print("=" * 80)

query2 = """
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
WHERE toLower(faq.question) CONTAINS 'thanh toán'
  AND (toLower(faq.question) CONTAINS 'điện' OR toLower(faq.question) CONTAINS 'viễn thông')
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count
RETURN faq.id as faq_id,
       faq.question as question,
       p.name as process_name,
       step_count
ORDER BY step_count DESC
LIMIT 10
"""

with connector.driver.session(database=connector.database) as session:
    results2 = session.run(query2).data()

print(f"\nFound {len(results2)} FAQs:")
for i, r in enumerate(results2, 1):
    print(f"\n{i}. {r['faq_id']}: {r['question'][:80]}...")
    print(f"   Process: {r['process_name']}")
    print(f"   Steps: {r['step_count']}")

# Query 3: What is FAQ_497 that keeps matching?
print("\n" + "=" * 80)
print("CHECKING FAQ_497 (the wrong FAQ being matched)")
print("=" * 80)

query3 = """
MATCH (faq:FAQ {id: 'FAQ_497'})
OPTIONAL MATCH (faq)-[:DESCRIBES_PROCESS]->(p:Process)
OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count
RETURN faq.id as faq_id,
       faq.question as question,
       faq.answer as answer,
       p.name as process_name,
       step_count
"""

with connector.driver.session(database=connector.database) as session:
    result3 = session.run(query3).data()

if result3:
    r = result3[0]
    print(f"\nFAQ_497:")
    print(f"Question: {r['question']}")
    print(f"Answer (first 300 chars): {r['answer'][:300]}...")
    print(f"Process: {r['process_name']}")
    print(f"Steps: {r['step_count']}")
else:
    print("\nFAQ_497 not found!")

connector.close()

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("\nIssues found:")
print("1. Entity extraction only found 'Thanh toán' (generic)")
print("2. Need to check why FAQ_497 is matching instead of correct FAQ")
print("3. Confidence is 50% - right at LLM fallback threshold")
