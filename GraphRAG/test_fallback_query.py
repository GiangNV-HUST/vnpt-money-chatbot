# -*- coding: utf-8 -*-
"""
Test fallback query to see what it's matching
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

# Test the exact query being used
process_name = "withdrawal"
keywords = ["rút tiền", "ví", "ngân hàng"]
from_step = 6

keyword_conditions = " OR ".join([f"toLower(faq.question) CONTAINS '{kw}'" for kw in keywords])

cypher = f"""
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {{name: $process_name}})
WHERE {keyword_conditions}
MATCH (p)-[:HAS_STEP]->(all_s:Step)
WITH faq, p, count(all_s) as total_count
MATCH (p)-[:HAS_STEP]->(s:Step)
WHERE s.number = $from_step
RETURN faq.question as faq_question,
       p.name as process_name,
       p.id as process_id,
       s.number as step_num,
       s.text as step_text,
       total_count as total_steps_in_process
ORDER BY s.number
LIMIT 5
"""

params = {
    "process_name": process_name,
    "from_step": from_step
}

print("=" * 80)
print("Testing fallback query for 'Rút tiền' step 6")
print("=" * 80)
print(f"Process: {process_name}")
print(f"Keywords: {keywords}")
print(f"From step: {from_step}")
print()

results = connector.execute_query(cypher, params)

if results:
    print(f"Found {len(results)} matches:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Total steps in process: {result.get('total_steps_in_process')}")
        print(f"   Process ID: {result.get('process_id')}")
        print(f"   FAQ: {result.get('faq_question')[:80]}...")
        print()
else:
    print("❌ No results found")

# Now try count query
print("=" * 80)
print("Testing count query (when step not found)")
print("=" * 80)

count_cypher = f"""
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {{name: $process_name}})
WHERE {keyword_conditions}
MATCH (p)-[:HAS_STEP]->(s:Step)
WITH p, count(s) as step_count
RETURN p.id as process_id, step_count as total_count
ORDER BY step_count
"""

count_results = connector.execute_query(count_cypher, {"process_name": process_name})

if count_results:
    print(f"Found {len(count_results)} processes:\n")
    for i, result in enumerate(count_results, 1):
        print(f"{i}. Process ID: {result.get('process_id')}")
        print(f"   Total steps: {result.get('total_count')}")
else:
    print("❌ No processes found")

connector.close()
