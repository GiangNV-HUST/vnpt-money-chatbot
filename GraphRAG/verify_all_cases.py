"""
Verify all Case nodes created in Neo4j
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector


def verify_cases():
    """Verify all Case nodes"""
    connector = Neo4jConnector()

    # Query all FAQs with Case nodes (split to avoid nested aggregation)
    query1 = """
    MATCH (faq:FAQ)-[:HAS_CASE]->(case:Case)
    RETURN faq.question as question,
           count(DISTINCT case) as case_count
    ORDER BY faq.question
    """

    query2 = """
    MATCH (faq:FAQ)-[:HAS_CASE]->(case:Case)
    WHERE faq.question = $question
    OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
    RETURN case.case_id as case_id,
           case.name as name,
           case.case_type as type,
           count(step) as step_count
    ORDER BY case_id
    """

    faq_results = connector.execute_query(query1)

    # Get case details for each FAQ
    results = []
    for faq_record in faq_results:
        question = faq_record['question']
        case_results = connector.execute_query(query2, {'question': question})

        results.append({
            'question': question,
            'case_count': faq_record['case_count'],
            'cases': [{'name': c['name'], 'type': c['type'], 'step_count': c['step_count']}
                      for c in case_results]
        })

    print('='*80)
    print('TẤT CẢ FAQs VỚI CASE NODES')
    print('='*80)
    print(f'\nTổng số FAQs có Case nodes: {len(results)}\n')

    for i, record in enumerate(results, 1):
        question = record['question']
        case_count = record['case_count']
        cases = record['cases']

        print(f'{i}. {question[:70]}...')
        print(f'   Số Cases: {case_count}')

        for j, case in enumerate(cases, 1):
            case_name = case["name"] if case["name"] else "[No name]"
            case_type = case["type"] if case["type"] else "[No type]"
            print(f'   └─ Case {j}: {case_name[:60]}...')
            print(f'      Type: {case_type}, Steps: {case["step_count"]}')
        print()

    # Summary statistics
    total_cases = sum(r['case_count'] for r in results)
    print('='*80)
    print(f'TỔNG KẾT:')
    print(f'  - Tổng FAQs có Case nodes: {len(results)}')
    print(f'  - Tổng số Case nodes: {total_cases}')
    print('='*80)

    connector.close()


if __name__ == '__main__':
    verify_cases()
