# -*- coding: utf-8 -*-
"""
Debug the 2 failed cases to see which FAQ is being matched
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

print("=" * 80)
print("DEBUG: Finding FAQs for failed cases")
print("=" * 80)

# Case 1: Hủy nạp tiền tự động
print("\n" + "=" * 80)
print("CASE 1: Hủy nạp tiền tự động")
print("=" * 80)

query1 = """
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
WHERE toLower(faq.question) CONTAINS 'hủy'
  AND toLower(faq.question) CONTAINS 'nạp tiền'
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count,
     CASE WHEN toLower(faq.question) CONTAINS 'tự động' THEN 1 ELSE 0 END +
     CASE WHEN toLower(faq.question) CONTAINS 'dịch vụ' THEN 1 ELSE 0 END as optional_score
RETURN faq.question as question,
       p.name as process_name,
       p.id as process_id,
       step_count,
       optional_score
ORDER BY optional_score DESC, step_count DESC
LIMIT 5
"""

with connector.driver.session(database=connector.database) as session:
    results1 = session.run(query1).data()

print(f"\nFound {len(results1)} matching FAQs:")
for i, r in enumerate(results1, 1):
    print(f"\n{i}. Question: {r['question'][:80]}...")
    print(f"   Process: {r['process_name']}")
    print(f"   Process ID: {r['process_id'][:60]}...")
    print(f"   Steps: {r['step_count']}")
    print(f"   Optional score: {r['optional_score']}")

# Case 2: Mua vé máy bay
print("\n\n" + "=" * 80)
print("CASE 2: Mua vé máy bay")
print("=" * 80)

query2 = """
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
WHERE toLower(faq.question) CONTAINS 'mua vé'
  AND toLower(faq.question) CONTAINS 'máy bay'
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count
RETURN faq.question as question,
       p.name as process_name,
       p.id as process_id,
       step_count
ORDER BY step_count DESC
LIMIT 5
"""

with connector.driver.session(database=connector.database) as session:
    results2 = session.run(query2).data()

print(f"\nFound {len(results2)} matching FAQs:")
for i, r in enumerate(results2, 1):
    print(f"\n{i}. Question: {r['question'][:80]}...")
    print(f"   Process: {r['process_name']}")
    print(f"   Process ID: {r['process_id'][:60]}...")
    print(f"   Steps: {r['step_count']}")

# Check what the actual step counts are
print("\n\n" + "=" * 80)
print("VERIFYING STEP COUNTS")
print("=" * 80)

# Get step count for "Hủy nạp tiền tự động" top match
if results1:
    process_id1 = results1[0]['process_id']
    query_verify1 = """
    MATCH (p:Process {id: $process_id})-[:HAS_STEP]->(s:Step)
    RETURN s.number as step_num, s.text as step_text
    ORDER BY s.number
    """

    with connector.driver.session(database=connector.database) as session:
        steps1 = session.run(query_verify1, {"process_id": process_id1}).data()

    print(f"\nHủy nạp tiền - Process has {len(steps1)} steps:")
    for step in steps1:
        print(f"  Bước {step['step_num']}: {step['step_text'][:60]}...")

# Get step count for "Mua vé máy bay" top match
if results2:
    process_id2 = results2[0]['process_id']
    query_verify2 = """
    MATCH (p:Process {id: $process_id})-[:HAS_STEP]->(s:Step)
    RETURN s.number as step_num, s.text as step_text
    ORDER BY s.number
    """

    with connector.driver.session(database=connector.database) as session:
        steps2 = session.run(query_verify2, {"process_id": process_id2}).data()

    print(f"\nMua vé máy bay - Process has {len(steps2)} steps:")
    for step in steps2:
        print(f"  Bước {step['step_num']}: {step['step_text'][:60]}...")

connector.close()
