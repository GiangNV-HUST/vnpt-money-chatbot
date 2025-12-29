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
                    continue

            # Pattern 4: FAQ có bullet points (•, -, +) - ANY bullets
            bullet_count = len(re.findall(r'\n\s*[•\-+]\s+', answer))

            if bullet_count >= 3:  # At least 3 bullet points
                cases = self._parse_bullet_conditions(answer)

                if cases:
                    self.faqs_to_process.append({
                        'question': question,
                        'type': 'condition',
                        'cases': cases,
                        'original_answer': answer
                    })
                    continue

            # Pattern 5: FAQ có numbered steps với bullets bên trong
            numbered_bullets = re.search(r'\d+\.\s+[^\n]+\n\s*[-+•]\s+', answer)

            if numbered_bullets and bullet_count >= 2:
                cases = self._parse_numbered_with_bullets(answer)

                if cases:
                    self.faqs_to_process.append({
                        'question': question,
                        'type': 'condition',
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

            # Remove trailing colon from name if present
            if method_name.endswith(':'):
                method_name = method_name[:-1].strip()

            cases.append({
                'name': method_name,
                'description': section,  # ✅ FIXED: Keep full text (was section[:200])
                'full_content': section,
                'case_type': 'method',
                'keywords': self._extract_case_keywords(method_name, section)
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

                # Extract case name (first sentence or up to 80 chars)
                name_match = re.match(r'^([^:\n.]+)', content)
                if name_match:
                    case_name = name_match.group(1).strip()
                    # Limit name length
                    if len(case_name) > 80:
                        case_name = case_name[:80] + '...'
                else:
                    case_name = f'{keyword} {case_num}'

                cases.append({
                    'name': case_name,
                    'description': content,  # ✅ FIXED: Keep full text (was content[:200])
                    'full_content': content,
                    'case_type': 'condition',
                    'keywords': self._extract_case_keywords(case_name, content)
                })

        return cases

    def _parse_if_then(self, answer):
        """Parse answer có cấu trúc If-Then - Enhanced to handle multiple formats"""
        cases = []

        # Strategy 1: Split by "Nếu" at line start (existing)
        if_sections = re.split(r'\n+(?=Nếu\s+)', answer, flags=re.IGNORECASE)

        for section in if_sections:
            if not section.strip().lower().startswith('nếu'):
                continue

            # Extract condition (first sentence up to 80 chars)
            condition_match = re.match(r'Nếu\s+(.+?)(?:\s+thì|\s*:|\.|,)', section, re.IGNORECASE | re.DOTALL)

            if condition_match:
                condition = condition_match.group(1).strip()

                # Create concise name
                if len(condition) > 80:
                    case_name = f'Nếu {condition[:77]}...'
                else:
                    case_name = f'Nếu {condition}'

                cases.append({
                    'name': case_name,
                    'description': section,
                    'full_content': section,
                    'case_type': 'if_then',
                    'keywords': self._extract_case_keywords(case_name, section)
                })

        # Strategy 2: Split by "- Nếu" or "+ Nếu" (for bullet/dash format)
        if len(cases) < 2:
            dash_sections = re.split(r'\n\s*[-+•]\s*(?=Nếu\s+)', answer, flags=re.IGNORECASE)

            temp_cases = []
            for section in dash_sections:
                section = section.strip()
                if not section.lower().startswith('nếu'):
                    continue

                condition_match = re.match(r'Nếu\s+(.+?)(?:\s+thì|\s*:|\.|,)', section, re.IGNORECASE | re.DOTALL)

                if condition_match:
                    condition = condition_match.group(1).strip()

                    if len(condition) > 80:
                        case_name = f'Nếu {condition[:77]}...'
                    else:
                        case_name = f'Nếu {condition}'

                    temp_cases.append({
                        'name': case_name,
                        'description': section,
                        'full_content': section,
                        'case_type': 'if_then',
                        'keywords': self._extract_case_keywords(case_name, section)
                    })

            if len(temp_cases) >= len(cases):
                cases = temp_cases

        # Strategy 3: Split by numbered "1. Trường hợp" format with "Nếu" inside
        if len(cases) < 2:
            numbered_sections = re.split(r'\n\s*(\d+)\.\s*Trường hợp', answer, flags=re.IGNORECASE)

            temp_cases = []
            for i in range(2, len(numbered_sections), 2):
                if i < len(numbered_sections):
                    case_num = numbered_sections[i-1]
                    content = numbered_sections[i].strip()

                    # Extract "Nếu..." from content
                    if_match = re.search(r'(Nếu\s+.+?)(?:\n|$)', content, re.IGNORECASE)

                    if if_match:
                        condition = if_match.group(1).strip()

                        # Clean up condition
                        condition = re.sub(r'\s+thì.*', '', condition, flags=re.IGNORECASE)
                        condition = re.sub(r'^Nếu\s+', '', condition, flags=re.IGNORECASE)

                        if len(condition) > 80:
                            case_name = f'Nếu {condition[:77]}...'
                        else:
                            case_name = f'Nếu {condition}'

                        temp_cases.append({
                            'name': case_name,
                            'description': content,
                            'full_content': content,
                            'case_type': 'if_then',
                            'keywords': self._extract_case_keywords(case_name, content)
                        })

            if len(temp_cases) >= len(cases):
                cases = temp_cases

        return cases

    def _parse_bullet_conditions(self, answer):
        """Parse answer có bullet points (•, -, +) với conditions"""
        # Split by bullet points
        sections = re.split(r'\n\s*([•\-+])\s+', answer)

        cases = []
        for i in range(1, len(sections), 2):  # Pairs of (bullet, content)
            if i + 1 >= len(sections):
                break

            bullet = sections[i]
            content = sections[i + 1].strip()

            # Skip if too short (likely not a case)
            if len(content) < 20:
                continue

            # Extract case name (first line or condition)
            name_match = re.match(r'^([^:\n.]+(?:[:.])?)', content)

            if name_match:
                case_name = name_match.group(1).strip()

                # Remove trailing punctuation
                case_name = re.sub(r'[:.,;]+$', '', case_name)

                # Limit length
                if len(case_name) > 80:
                    case_name = case_name[:80] + '...'

                cases.append({
                    'name': case_name,
                    'description': content,
                    'full_content': content,
                    'case_type': 'condition',
                    'keywords': self._extract_case_keywords(case_name, content)
                })

        return cases if len(cases) >= 2 else []

    def _parse_numbered_with_bullets(self, answer):
        """Parse FAQs có numbered sections với bullets bên trong (e.g., Bước 1: ... - item)"""
        # This handles cases like:
        # Bước 1: Title
        # - Bullet 1
        # - Bullet 2
        # Bước 2: Title
        # - Bullet 3

        # First try: Split by "Bước N:"
        step_sections = re.split(r'\n+(?=Bước\s+\d+:)', answer, flags=re.IGNORECASE)

        if len(step_sections) >= 2:
            cases = []
            for section in step_sections:
                section = section.strip()
                if not section or len(section) < 20:
                    continue

                # Extract step name
                step_match = re.match(r'(Bước\s+\d+[^:\n]*)', section, re.IGNORECASE)

                if step_match:
                    case_name = step_match.group(1).strip()

                    # Remove trailing colon
                    case_name = re.sub(r':$', '', case_name)

                    cases.append({
                        'name': case_name,
                        'description': section,
                        'full_content': section,
                        'case_type': 'condition',
                        'keywords': self._extract_case_keywords(case_name, section)
                    })

            if len(cases) >= 2:
                return cases

        # Second try: Return bullet points as cases (fallback)
        return self._parse_bullet_conditions(answer)

    def _extract_case_keywords(self, name, description):
        """Extract matching keywords from case name and description"""
        keywords = []
        text_lower = (name + ' ' + description).lower()

        # Method keywords
        method_keywords = [
            'chuyển khoản', 'liên kết', 'ngân hàng liên kết', 'tài khoản liên kết',
            'qr', 'qr code', 'qr đa năng', 'mã qr',
            'ví điện tử', 'tài khoản ví', 'ví',
            'thẻ', 'thẻ ngân hàng', 'thẻ atm'
        ]

        # Status keywords
        status_keywords = [
            'thành công', 'thất bại', 'không thành công',
            'đang xử lý', 'đang chờ', 'chờ xử lý',
            'đã nhận được tiền', 'đã nhận tiền', 'nhận được tiền',
            'chưa nhận được tiền', 'chưa nhận tiền'
        ]

        # Conditional keywords
        conditional_keywords = [
            'nếu', 'trường hợp', 'điều kiện',
            'khi', 'lúc', 'thì'
        ]

        all_keywords = method_keywords + status_keywords + conditional_keywords

        for kw in all_keywords:
            if kw in text_lower:
                keywords.append(kw)

        return keywords

    def _detect_case_type_and_status(self, name, description, default_type):
        """Detect case type and status values from content"""
        text_lower = (name + ' ' + description).lower()

        # Detect type
        if 'nếu' in text_lower[:10]:  # "Nếu" at start
            case_type = 'if_then'
        elif any(word in text_lower for word in ['chuyển khoản', 'liên kết', 'qr', 'ví']):
            case_type = 'method'
        elif any(word in text_lower for word in ['thành công', 'thất bại', 'đang xử lý']):
            case_type = 'status'
        else:
            case_type = default_type

        # Detect status values
        status_values = []
        if 'thành công' in text_lower and 'không thành công' not in text_lower:
            status_values.append('thành công')
        if 'thất bại' in text_lower or 'không thành công' in text_lower:
            status_values.append('thất bại')
        if 'đang xử lý' in text_lower or 'chờ xử lý' in text_lower:
            status_values.append('đang xử lý')
        if 'đã nhận được tiền' in text_lower or 'đã nhận tiền' in text_lower:
            status_values.append('đã nhận tiền')
        if 'chưa nhận được tiền' in text_lower or 'chưa nhận tiền' in text_lower:
            status_values.append('chưa nhận tiền')

        return case_type, status_values

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

                    # Detect refined case_type and status_values
                    refined_type, status_values = self._detect_case_type_and_status(
                        case['name'],
                        case['description'],
                        case['case_type']
                    )

                    create_case_query = '''
                    MATCH (faq:FAQ)
                    WHERE faq.question = $question
                    CREATE (case:Case {
                        case_id: $case_id,
                        name: $name,
                        description: $description,
                        case_type: $case_type,
                        keywords: $keywords,
                        status_values: $status_values
                    })
                    CREATE (faq)-[:HAS_CASE]->(case)
                    RETURN case.name as case_name
                    '''

                    params = {
                        'question': question,
                        'case_id': case_id,
                        'name': case['name'],
                        'description': case['description'],
                        'case_type': refined_type,
                        'keywords': case.get('keywords', []),
                        'status_values': status_values
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
