# -*- coding: utf-8 -*-
"""
Debug Thanh toán hóa đơn viễn thông query
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine

print("=" * 80)
print("DEBUG: Thanh toán hóa đơn viễn thông")
print("=" * 80)

engine = Neo4jGraphRAGEngine()

query = "Làm thế nào để thanh toán hóa đơn viễn thông?"

print(f"\nQuery: {query}")
print("-" * 80)

result = engine.query(query)

print(f"\nStatus: {result.get('status')}")
print(f"Answer:\n{result.get('answer', 'No answer')}\n")

if result.get('steps'):
    print(f"Steps extracted: {len(result['steps'])}")
    for i, step in enumerate(result['steps'], 1):
        # Use step_text or step_title (not description/content)
        step_content = step.get('step_text', step.get('step_title', step.get('description', step.get('content', 'N/A'))))
        print(f"  {i}. {step_content}")
else:
    print("No steps extracted!")

# Check all_results to see actual FAQ
if result.get('all_results'):
    print(f"\nTop FAQ matched:")
    top_faq = result['all_results'][0]
    print(f"  Question: {top_faq.get('question', 'N/A')}")
    print(f"  Answer preview: {top_faq.get('answer', 'N/A')[:200]}...")

    # Check if FAQ has steps in Neo4j
    from neo4j_connector import Neo4jConnector
    conn = Neo4jConnector()

    faq_id = top_faq.get('faq_id')
    if faq_id:
        print(f"\n  Checking Neo4j for FAQ {faq_id} steps...")
        query_cypher = """
        MATCH (faq:FAQ {faq_id: $faq_id})-[:HAS_STEP]->(step:Step)
        RETURN step.step_number AS step_num, step.description AS desc
        ORDER BY step.step_number
        """
        steps_in_neo4j = conn.execute_query(query_cypher, {"faq_id": faq_id})

        if steps_in_neo4j:
            print(f"  ✅ Found {len(steps_in_neo4j)} steps in Neo4j:")
            for s in steps_in_neo4j:
                print(f"     Bước {s['step_num']}: {s['desc']}")
        else:
            print(f"  ❌ No steps found in Neo4j!")

    conn.close()
