# -*- coding: utf-8 -*-
"""
Comprehensive test suite for all FAQ Case nodes
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j_connector import Neo4jConnector
from neo4j_rag_engine import Neo4jGraphRAGEngine
import json


class CaseNodeTester:
    """Test all Case nodes across FAQs"""

    def __init__(self):
        self.conn = Neo4jConnector()
        self.engine = Neo4jGraphRAGEngine()
        self.results = []

    def get_all_faqs_with_cases(self):
        """Get all FAQs that have Case nodes"""
        result = self.conn.execute_query('''
        MATCH (faq:FAQ)-[:HAS_CASE]->(c:Case)
        WITH faq, collect({
            name: c.name,
            description: c.description
        }) as cases
        WHERE size(cases) > 1
        RETURN faq.id as faq_id,
               faq.question as question,
               cases
        ORDER BY faq.id
        ''')

        return result

    def extract_case_keywords(self, case_name, case_desc):
        """Extract keywords from case name/description for testing"""
        text = (case_name or '') + ' ' + (case_desc or '')
        text_lower = text.lower()

        keywords = []

        # Pattern 1: "Nếu ... thì" conditions
        if 'nếu vnpt money đã nhận được tiền' in text_lower:
            keywords.append(('đã nhận được tiền', 'VNPT Money đã nhận được tiền'))
        if 'nếu vnpt money chưa nhận được tiền' in text_lower:
            keywords.append(('chưa nhận được tiền', 'VNPT Money chưa nhận được tiền'))
        if 'không thành công' in text_lower:
            keywords.append(('không thành công', 'giao dịch không thành công'))
        if 'đang xử lý' in text_lower:
            keywords.append(('đang xử lý', 'trạng thái đang xử lý'))
        if 'thành công' in text_lower and 'không thành công' not in text_lower:
            keywords.append(('thành công', 'trạng thái thành công'))

        # Pattern 2: Method names
        if 'chuyển khoản' in text_lower:
            keywords.append(('chuyển khoản', 'bằng chuyển khoản ngân hàng'))
        if 'liên kết' in text_lower:
            keywords.append(('liên kết', 'bằng tài khoản liên kết'))
        if 'qr' in text_lower:
            keywords.append(('qr', 'qua QR code'))

        return keywords

    def generate_test_query(self, base_question, keyword_phrase):
        """Generate test query from base question and keyword"""
        # Remove question mark and add keyword context
        base = base_question.rstrip('?').rstrip('.')

        # Add keyword context
        if keyword_phrase:
            # Insert keyword before last part
            return f"{base}, {keyword_phrase}"
        return base_question

    def test_faq_cases(self, faq_id, question, cases):
        """Test all cases for a specific FAQ"""
        print(f"\n{'='*80}")
        print(f"Testing {faq_id}: {question[:70]}...")
        print(f"Cases: {len(cases)}")
        print('-'*80)

        test_results = {
            'faq_id': faq_id,
            'question': question,
            'total_cases': len(cases),
            'tests': []
        }

        for i, case in enumerate(cases, 1):
            case_name = case.get('name') or f"Case {i}"
            case_desc = case.get('description', '')

            # Extract keywords for this case
            keywords = self.extract_case_keywords(case_name, case_desc)

            if not keywords:
                print(f"  {i}. {case_name[:60]}: No testable keywords")
                continue

            # Test with first keyword
            keyword, phrase = keywords[0]
            test_query = self.generate_test_query(question, phrase)

            print(f"  {i}. Testing: {case_name[:50]}")
            print(f"     Query: {test_query[:70]}...")

            # Run query
            result = self.engine.query(test_query)
            answer = result.get('answer', '')

            # Check if case matched
            # Consider it a match if:
            # 1. Case name appears in answer, OR
            # 2. Key parts of case description appear in answer, OR
            # 3. Answer doesn't contain OTHER case names

            case_name_match = case_name[:30] in answer if case_name else False
            keyword_match = keyword in answer.lower()

            # Check if other cases leaked into answer
            other_cases = [c for c in cases if c != case]
            other_case_leaked = False
            for other in other_cases:
                other_name = other.get('name', '')
                if other_name and len(other_name) > 20 and other_name[:30] in answer:
                    other_case_leaked = True
                    break

            success = (case_name_match or keyword_match) and not other_case_leaked

            status = '✅' if success else '❌'
            print(f"     Result: {status} (match={case_name_match or keyword_match}, no_leak={not other_case_leaked})")
            print(f"     Answer: {answer[:80]}...")

            test_results['tests'].append({
                'case_name': case_name,
                'keyword': keyword,
                'query': test_query,
                'success': success,
                'answer_preview': answer[:200]
            })

        self.results.append(test_results)

        # Summary for this FAQ
        successes = sum(1 for t in test_results['tests'] if t['success'])
        total = len(test_results['tests'])
        print(f"\nFAQ {faq_id} Summary: {successes}/{total} tests passed")

        return test_results

    def run_all_tests(self):
        """Run tests for all FAQs with cases"""
        print("="*80)
        print("COMPREHENSIVE CASE NODE TESTING")
        print("="*80)

        faqs = self.get_all_faqs_with_cases()

        print(f"\nFound {len(faqs)} FAQs with multiple Case nodes\n")

        for faq in faqs[:10]:  # Test first 10 to avoid timeout
            self.test_faq_cases(
                faq['faq_id'],
                faq['question'],
                faq['cases']
            )

        # Overall summary
        print("\n" + "="*80)
        print("OVERALL SUMMARY")
        print("="*80)

        total_faqs = len(self.results)
        total_tests = sum(len(r['tests']) for r in self.results)
        total_pass = sum(sum(1 for t in r['tests'] if t['success']) for r in self.results)

        print(f"FAQs tested: {total_faqs}")
        print(f"Total tests: {total_tests}")
        print(f"Tests passed: {total_pass}/{total_tests} ({total_pass*100//total_tests if total_tests else 0}%)")

        # Group failures by type
        failures = []
        for result in self.results:
            for test in result['tests']:
                if not test['success']:
                    failures.append({
                        'faq_id': result['faq_id'],
                        'case': test['case_name'],
                        'query': test['query']
                    })

        if failures:
            print(f"\n{len(failures)} Failed tests:")
            for fail in failures[:10]:  # Show first 10
                print(f"  - {fail['faq_id']}: {fail['case'][:50]}")

        return {
            'total_faqs': total_faqs,
            'total_tests': total_tests,
            'passed': total_pass,
            'failed': total_tests - total_pass,
            'pass_rate': f"{total_pass*100//total_tests if total_tests else 0}%"
        }


if __name__ == "__main__":
    tester = CaseNodeTester()
    summary = tester.run_all_tests()

    print("\n" + "="*80)
    print(f"FINAL RESULT: {summary['pass_rate']} pass rate")
    print("="*80)
