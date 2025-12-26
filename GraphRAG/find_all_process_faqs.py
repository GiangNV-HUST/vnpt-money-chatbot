# -*- coding: utf-8 -*-
"""
Find all FAQs that have process steps in Neo4j
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

# Query to find all processes with their FAQs and step counts
query = """
MATCH (p:Process)-[:HAS_STEP]->(s:Step)
WITH p, count(s) as step_count
OPTIONAL MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p)
RETURN p.name as process_name,
       p.id as process_id,
       step_count,
       collect(DISTINCT {
           question: faq.question,
           answer_preview: substring(faq.answer, 0, 100)
       }) as faqs
ORDER BY step_count DESC
"""

# Execute query using session
if connector.driver is None:
    print("❌ Neo4j driver not initialized")
    sys.exit(1)

with connector.driver.session(database=connector.database) as session:
    results = session.run(query).data()

print("=" * 80)
print("TẤT CẢ CÁC QUY TRÌNH CÓ STEPS TRONG NEO4J")
print("=" * 80)

total_processes = 0
for record in results:
    total_processes += 1
    process_name = record['process_name']
    process_id = record['process_id']
    step_count = record['step_count']
    faqs = record['faqs']

    print(f"\n{total_processes}. Process: {process_name}")
    print(f"   ID: {process_id}")
    print(f"   Steps: {step_count}")

    # Show associated FAQs
    valid_faqs = [f for f in faqs if f['question']]
    if valid_faqs:
        print(f"   FAQs ({len(valid_faqs)}):")
        for i, faq in enumerate(valid_faqs[:3], 1):  # Show first 3 FAQs
            question = faq['question'][:80] + "..." if len(faq['question']) > 80 else faq['question']
            print(f"      {i}. {question}")
        if len(valid_faqs) > 3:
            print(f"      ... và {len(valid_faqs) - 3} FAQs khác")
    else:
        print(f"   ⚠️  Không có FAQ nào liên kết với process này")

print(f"\n{'=' * 80}")
print(f"TỔNG CỘNG: {total_processes} processes có steps")
print(f"{'=' * 80}")

connector.close()
