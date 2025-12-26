# -*- coding: utf-8 -*-
"""
Check what FAQs actually exist in the Neo4j graph
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

# Query all FAQs in the graph
query = """
MATCH (faq:FAQ)
RETURN faq.question_id as question_id,
       faq.question as question,
       faq.answer as answer
ORDER BY faq.question_id
LIMIT 20
"""

print("=" * 80)
print("FAQs in Neo4j Graph:")
print("=" * 80)

results = connector.execute_query(query, {})

if results:
    for i, result in enumerate(results, 1):
        print(f"\n{i}. FAQ ID: {result.get('question_id')}")
        question = result.get('question', '')
        if len(question) > 100:
            question = question[:100] + "..."
        print(f"   Question: {question}")
else:
    print("❌ No FAQs found in graph!")

# Check which FAQs have processes and steps
print("\n" + "=" * 80)
print("FAQs with Processes and Steps:")
print("=" * 80)

query2 = """
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as step_count
RETURN faq.question_id as question_id,
       faq.question as question,
       p.name as process_name,
       step_count
ORDER BY faq.question_id
"""

results2 = connector.execute_query(query2, {})

if results2:
    for i, result in enumerate(results2, 1):
        print(f"\n{i}. FAQ ID: {result.get('question_id')}")
        print(f"   Process: {result.get('process_name')}")
        print(f"   Steps: {result.get('step_count')}")
        question = result.get('question', '')
        if len(question) > 100:
            question = question[:100] + "..."
        print(f"   Question: {question}")
else:
    print("❌ No FAQs with processes found!")

# Search for "rút tiền" related FAQs
print("\n" + "=" * 80)
print("FAQs containing 'rút tiền':")
print("=" * 80)

query3 = """
MATCH (faq:FAQ)
WHERE toLower(faq.question) CONTAINS 'rút tiền'
   OR toLower(faq.answer) CONTAINS 'rút tiền'
   OR toLower(faq.question_id) CONTAINS 'rut'
RETURN faq.question_id as question_id,
       faq.question as question
"""

results3 = connector.execute_query(query3, {})

if results3:
    for i, result in enumerate(results3, 1):
        print(f"\n{i}. FAQ ID: {result.get('question_id')}")
        print(f"   Question: {result.get('question')}")
else:
    print("❌ No FAQs about 'rút tiền' found!")

connector.close()
print("\n" + "=" * 80)
