"""
Tự động tạo Case nodes cho các FAQ có nhiều phương thức/điều kiện
"""

import sys
import json
import re
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector
from pathlib import Path


class AutoCaseNodeCreator:
    """Tự động phân tích và tạo Case nodes"""

    def __init__(self):
        self.connector = Neo4jConnector()
        self.documents = []
        self.faqs_to_process = []

    def load_documents(self):
        """Đọc paraphrase_documents.json"""
        doc_path = Path(__file__).parent.parent / 'data' / 'paraphrase_documents.json'

        with open(doc_path, 'r', encoding='utf-8') as f:
            self.documents = json.load(f)

        print(f'✅ Đã load {len(self.documents)} documents')

    def analyze_faqs(self):
        """Phân tích các FAQ cần tạo Case nodes"""

        for doc in self.documents:
            meta = doc.get('metadata', {})
            answer = meta.get('answer', '')
            question = meta.get('question', '')

            # Skip variants
            if meta.get('is_variant'):
                continue

            # Pattern 1: FAQ có "X hình thức"
            method_pattern = re.search(r'có\s+(\d+)\s+(hình thức|cách)', answer, re.IGNORECASE)

            if method_pattern:
                num_methods = int(method_pattern.group(1))
                cases = self._parse_methods(answer, num_methods)

                if cases:
                    self.faqs_to_process.append({
                        'question': question,
                        'type': 'method',
                        'cases': cases,
                        'original_answer': answer
                    })
                    continue

            # Pattern 2: FAQ có nhiều "Trường hợp"
            case_pattern = len(re.findall(r'\n\s*\d+\.\s*Trường hợp', answer, re.IGNORECASE))

            if case_pattern >= 2:
                cases = self._parse_conditions(answer, 'Trường hợp')

                if cases:
                    self.faqs_to_process.append({
                        'question': question,
                        'type': 'condition',
                        'cases': cases,
                        'original_answer': answer
                    })
                    continue

            # Pattern 3: FAQ có "Nếu...thì"
            if_pattern = len(re.findall(r'Nếu\s+.+?thì|Nếu\s+.+?:', answer, re.IGNORECASE))

            if if_pattern >= 2:
                cases = self._parse_if_then(answer)

                if cases:
                    self.faqs_to_process.append({
                        'question': question,
                        'type': 'if_then',
                        'cases': cases,
                        'original_answer': answer
                    })

        print(f'\n✅ Phân tích xong: {len(self.faqs_to_process)} FAQs cần tạo Case nodes')

        # Group by type
        by_type = {}
        for faq in self.faqs_to_process:
            faq_type = faq['type']
            by_type[faq_type] = by_type.get(faq_type, 0) + 1

        for faq_type, count in by_type.items():
            print(f'   - {faq_type}: {count} FAQs')

    def _parse_methods(self, answer, num_methods):
        """Parse answer có nhiều phương thức"""
        # Split by dash
        sections = re.split(r'\n\s*-\s+', answer)

        if len(sections) < num_methods + 1:  # +1 for intro
            return []

        cases = []
        for i in range(1, num_methods + 1):
            section = sections[i].strip()

            # Extract method name (before colon or newline)
            name_match = re.match(r'^([^:\n]+)', section)
            method_name = name_match.group(1).strip() if name_match else f'Phương thức {i}'

            cases.append({
                'name': method_name,
                'description': section[:200],
                'full_content': section,
                'case_type': 'method'
            })

        return cases

    def _parse_conditions(self, answer, keyword):
        """Parse answer có điều kiện đánh số"""
        # Split by numbered sections
        sections = re.split(r'\n\s*(\d+)\.\s*' + keyword, answer, flags=re.IGNORECASE)

        cases = []
        for i in range(2, len(sections), 2):  # Skip intro, take pairs of (number, content)
            if i < len(sections):
                case_num = sections[i-1]
                content = sections[i].strip()

                # Extract case name
                name_match = re.match(r'^([^:\n]+)', content)
                case_name = name_match.group(1).strip() if name_match else f'{keyword} {case_num}'

                cases.append({
                    'name': case_name,
                    'description': content[:200],
                    'full_content': content,
                    'case_type': 'condition'
                })

        return cases

    def _parse_if_then(self, answer):
        """Parse answer có cấu trúc If-Then"""
        # Find all "Nếu...thì" patterns
        if_sections = re.split(r'\n+(?=Nếu\s+)', answer, flags=re.IGNORECASE)

        cases = []
        for section in if_sections:
            if not section.strip().lower().startswith('nếu'):
                continue

            # Extract condition
            condition_match = re.match(r'Nếu\s+(.+?)(?:\s+thì|\s*:|\n)', section, re.IGNORECASE | re.DOTALL)

            if condition_match:
                condition = condition_match.group(1).strip()

                cases.append({
                    'name': f'Nếu {condition[:50]}...',
                    'description': section[:200],
                    'full_content': section,
                    'case_type': 'if_then'
                })

        return cases

    def create_case_nodes(self, dry_run=True):
        """Tạo Case nodes trong Neo4j"""

        if dry_run:
            print('\n' + '='*80)
            print('DRY RUN MODE - Chỉ hiển thị preview, không thay đổi database')
            print('='*80)
        else:
            print('\n' + '='*80)
            print('EXECUTE MODE - Đang tạo Case nodes vào Neo4j...')
            print('='*80)

        created_count = 0

        for faq in self.faqs_to_process:
            question = faq['question']
            cases = faq['cases']

            print(f'\n📝 FAQ: {question}')
            print(f'   Type: {faq["type"]}')
            print(f'   Số Cases: {len(cases)}')

            if dry_run:
                for i, case in enumerate(cases, 1):
                    print(f'   └─ Case {i}: {case["name"]}')
                    print(f'      Description: {case["description"][:100]}...')
                continue

            # Execute: Tạo Case nodes
            try:
                # Xóa Case nodes cũ
                delete_query = '''
                MATCH (faq:FAQ)-[:HAS_CASE]->(case:Case)
                WHERE faq.question = $question
                DETACH DELETE case
                '''

                self.connector.execute_query(delete_query, {'question': question}, write=True)

                # Tạo Case nodes mới
                for i, case in enumerate(cases, 1):
                    case_id = f"faq_{question[:20].replace(' ', '_')}_{i}"

                    create_case_query = '''
                    MATCH (faq:FAQ)
                    WHERE faq.question = $question
                    CREATE (case:Case {
                        case_id: $case_id,
                        name: $name,
                        description: $description,
                        case_type: $case_type
                    })
                    CREATE (faq)-[:HAS_CASE]->(case)
                    RETURN case.name as case_name
                    '''

                    params = {
                        'question': question,
                        'case_id': case_id,
                        'name': case['name'],
                        'description': case['description'],
                        'case_type': case['case_type']
                    }

                    result = self.connector.execute_query(create_case_query, params, write=True)

                    if result:
                        print(f'   ✅ Created Case: {result[0]["case_name"]}')
                        created_count += 1

            except Exception as e:
                print(f'   ❌ Error: {e}')

        if not dry_run:
            print(f'\n✅ Tổng số Case nodes đã tạo: {created_count}')

        return created_count

    def show_summary(self):
        """Hiển thị tóm tắt"""
        print('\n' + '='*80)
        print('TÓM TẮT PHÂN TÍCH')
        print('='*80)

        print(f'\nTổng số FAQs cần xử lý: {len(self.faqs_to_process)}')

        # Show top 10
        print('\nTop 10 FAQs sẽ được tạo Case nodes:')
        for i, faq in enumerate(self.faqs_to_process[:10], 1):
            print(f'\n{i}. {faq["question"]}')
            print(f'   Type: {faq["type"]}, Cases: {len(faq["cases"])}')
            for j, case in enumerate(faq['cases'], 1):
                print(f'   └─ {j}. {case["name"][:60]}...')

    def close(self):
        """Đóng kết nối"""
        self.connector.close()


def main():
    """Main execution"""
    import sys

    dry_run = '--execute' not in sys.argv

    creator = AutoCaseNodeCreator()

    try:
        print('='*80)
        print('AUTO CREATE CASE NODES FOR FAQs')
        print('='*80)

        # Step 1: Load documents
        creator.load_documents()

        # Step 2: Analyze FAQs
        creator.analyze_faqs()

        # Step 3: Show summary
        creator.show_summary()

        # Step 4: Create Case nodes
        if dry_run:
            print('\n' + '='*80)
            print('⚠️  DRY RUN MODE - Không có thay đổi nào được thực hiện')
            print('   Để tạo Case nodes, chạy: python auto_create_case_nodes.py --execute')
            print('='*80)
            creator.create_case_nodes(dry_run=True)
        else:
            confirm = input('\n⚠️  Bạn có chắc muốn tạo Case nodes? (yes/no): ')
            if confirm.lower() == 'yes':
                creator.create_case_nodes(dry_run=False)
            else:
                print('Đã hủy.')

    finally:
        creator.close()


if __name__ == '__main__':
    main()
