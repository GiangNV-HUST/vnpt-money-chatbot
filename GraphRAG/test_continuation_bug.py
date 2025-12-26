"""
Test script to debug continuation query bug
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine

# Initialize engine
engine = Neo4jGraphRAGEngine()

print('='*80)
print('DEBUGGING: Continuation Query Bug')
print('='*80)

# Simulate 3 queries
queries = [
    ("Query 1", "Tôi có thể rút tiền từ tài khoản Mobile Money về tài khoản ngân hàng như thế nào?"),
    ("Query 2", "tôi đã làm xong 3 bước đầu thì làm gì tiếp theo"),
    ("Query 3", "tiếp tục")
]

for label, query in queries:
    print(f'\n{"="*80}')
    print(f'{label}: {query}')
    print('='*80)

    result = engine.query(query)

    print(f'\nStatus: {result["status"]}')
    print(f'Confidence: {result.get("confidence", 0):.0%}')

    # Show which FAQ was retrieved
    if result.get('all_results'):
        faq_id = result['all_results'][0].get('question_id', 'NO_ID')
        faq_q = result['all_results'][0].get('question', 'NO_QUESTION')
        print(f'\nFAQ Retrieved:')
        print(f'  ID: {faq_id}')
        print(f'  Question: {faq_q[:100]}...')

    # Show answer preview
    answer = result.get('answer', '')
    print(f'\nAnswer Preview (first 200 chars):')
    print(f'  {answer[:200]}...')

    # Show if this was a continuation query
    if result.get('is_continuation'):
        print(f'\n✅ Detected as CONTINUATION query')
        print(f'  completed_step: {result.get("completed_step")}')
        print(f'  next_steps count: {len(result.get("next_steps", []))}')

    # Check entities
    entities = result.get('related_entities', {})
    if entities.get('topics'):
        print(f'\nTopics: {entities["topics"]}')

print(f'\n{"="*80}')
print('Test Complete')
print('='*80)

engine.close()
