"""
Check FAQ answer for Mobile Money deposit
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector


def check_faq():
    """Check FAQ answer"""
    connector = Neo4jConnector()

    question = "Tôi có thể nạp tiền từ ngân hàng vào tài khoản Mobile Money như thế nào?"

    query = """
    MATCH (faq:FAQ)
    WHERE faq.question = $question
    RETURN faq.question as question, faq.answer as answer
    """

    result = connector.execute_query(query, {'question': question})

    if result:
        print('='*80)
        print('FAQ ANSWER CHECK')
        print('='*80)
        print(f'\nQuestion: {result[0]["question"]}')
        print(f'\nCurrent Answer:\n{result[0]["answer"]}')
        print('\n' + '='*80)
    else:
        print('❌ FAQ not found')

    connector.close()


if __name__ == '__main__':
    check_faq()
