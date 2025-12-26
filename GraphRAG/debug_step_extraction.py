# -*- coding: utf-8 -*-
"""
Debug step extraction - why descriptions show as N/A
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from step_tracker import StepTracker

print("=" * 80)
print("DEBUG: Step Extraction for Thanh toán hóa đơn viễn thông")
print("=" * 80)

engine = Neo4jGraphRAGEngine()
tracker = StepTracker()

query = "Làm thế nào để thanh toán hóa đơn viễn thông?"

print(f"\nQuery: {query}")
print("-" * 80)

# Get the answer
result = engine.query(query)
answer = result.get('answer', '')

print("\n1. RAW ANSWER:")
print("-" * 80)
print(answer)
print()

# Extract steps using StepTracker
print("\n2. STEP TRACKER EXTRACTION:")
print("-" * 80)

extracted_steps = tracker.extract_steps(answer)
print(f"Extracted {len(extracted_steps)} steps\n")

for i, step in enumerate(extracted_steps, 1):
    print(f"Step {i}:")
    print(f"  step_number: {step.get('step_number', 'N/A')}")
    print(f"  step_title: {step.get('step_title', 'N/A')}")
    print(f"  step_text: {step.get('step_text', 'N/A')}")
    print(f"  description: {step.get('description', 'N/A')}")
    print(f"  content: {step.get('content', 'N/A')}")
    print()

# Check what's in result['steps']
print("\n3. RESULT['STEPS'] FROM ENGINE:")
print("-" * 80)

result_steps = result.get('steps', [])
print(f"Found {len(result_steps)} steps in result\n")

for i, step in enumerate(result_steps, 1):
    print(f"Step {i}:")
    for key, value in step.items():
        print(f"  {key}: {value}")
    print()

# Manual regex test
print("\n4. MANUAL REGEX TEST:")
print("-" * 80)

import re
pattern = r'Bước\s+(\d+):\s*(.+?)(?=Bước\s+\d+:|$)'
matches = re.findall(pattern, answer, re.DOTALL)

print(f"Found {len(matches)} matches with pattern: {pattern}\n")

for i, match in enumerate(matches, 1):
    step_num, step_content = match
    print(f"Match {i}:")
    print(f"  Number: {step_num}")
    print(f"  Content: {step_content[:100]}...")
    print()

# Check Neo4j for this FAQ's steps
print("\n5. NEO4J STEPS CHECK:")
print("-" * 80)

if result.get('all_results'):
    top_faq = result['all_results'][0]
    faq_id = top_faq.get('faq_id')

    if faq_id:
        from neo4j_connector import Neo4jConnector
        conn = Neo4jConnector()

        query_cypher = """
        MATCH (faq:FAQ {faq_id: $faq_id})-[:HAS_STEP]->(step:Step)
        RETURN step.step_number AS step_num, step.description AS desc
        ORDER BY step.step_number
        """
        steps_in_neo4j = conn.execute_query(query_cypher, {"faq_id": faq_id})

        print(f"FAQ ID: {faq_id}")
        print(f"Steps in Neo4j: {len(steps_in_neo4j)}\n")

        for s in steps_in_neo4j:
            print(f"Bước {s['step_num']}: {s['desc']}")

        conn.close()
    else:
        print("No FAQ ID found")
else:
    print("No FAQ results found")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print("""
Checking:
1. Is the answer formatted correctly with "Bước X: ..." pattern?
2. Does StepTracker.extract_steps() extract the content correctly?
3. Are the steps being returned with proper field names (description vs content vs step_text)?
4. Is there a mismatch between what's stored vs what's displayed?
""")
