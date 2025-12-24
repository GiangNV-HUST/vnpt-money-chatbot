"""
Extract Case nodes from FAQs with conditional scenarios
Reads paraphrase_documents.json and extracts individual Case objects
"""

import json
import re
from typing import List, Dict, Optional
from pathlib import Path


class CaseNodeExtractor:
    """Extract Case nodes from FAQ answers with conditional scenarios"""

    def __init__(self, data_file: str):
        self.data_file = Path(data_file)
        self.faqs = []
        self.case_nodes = []

    def load_data(self):
        """Load FAQ data from JSON file"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            self.faqs = json.load(f)
        print(f"[OK] Loaded {len(self.faqs)} FAQs from {self.data_file}")

    def _extract_cases_from_answer(self, answer: str) -> List[Dict]:
        """
        Extract individual case objects from an answer

        Patterns to detect:
        1. Status-based: "Trường hợp trạng thái 'Thành công':"
        2. If-then: "Nếu... thì..."
        3. Numbered scenarios: "1. Scenario A", "2. Scenario B"
        """
        cases = []

        # Pattern 1: Status-based cases
        # Example: "2. Trường hợp trạng thái là \"Thành công\":\n• Điều này có nghĩa là..."
        # Also matches: "2. Trường hợp trạng thái \"Thành công\":" (without "là")
        status_pattern = r'(\d+)\.\s+Trường\s+hợp\s+trạng\s+thái\s+(?:là\s+)?["\']([^"\']+)["\']\s*:\s*\n((?:•.+?\n?)+)'
        for match in re.finditer(status_pattern, answer, re.IGNORECASE):
            step_num = match.group(1)
            status = match.group(2).strip()
            content = match.group(3).strip()

            # Extract actions (bullet points)
            actions = [
                action.strip('• ').strip()
                for action in content.split('\n')
                if action.strip().startswith('•')
            ]

            cases.append({
                'case_type': 'status',
                'step_number': int(step_num),
                'status': status,
                'description': f"Trường hợp trạng thái \"{status}\"",
                'actions': actions,
                'content': content
            })

        # Pattern 2: If-then cases (Nếu... thì...)
        # Example: "Nếu VNPT Money đã nhận được tiền: Số tiền sẽ được cộng..."
        ifthen_pattern = r'(Nếu|NẾU)\s+([^:]+):\s*([^\n]+(?:\n(?!Nếu|NẾU)[^\n]+)*)'
        for match in re.finditer(ifthen_pattern, answer):
            condition = match.group(2).strip()
            consequence = match.group(3).strip()

            cases.append({
                'case_type': 'if_then',
                'condition': condition,
                'consequence': consequence,
                'description': f"Nếu {condition}",
                'actions': [consequence]
            })

        # Pattern 3: Numbered scenarios WITHOUT "Trường hợp"
        # Example: "1. Kiểm tra...\n2. Trường hợp A...\n3. Trường hợp B..."
        # Only extract if answer has multiple "Trường hợp" sections
        if answer.count('Trường hợp') >= 2:
            # These are already captured by Pattern 1
            pass
        elif answer.count('\n\n') >= 2:
            # Check for numbered list with multiple scenarios
            numbered_pattern = r'^(\d+)\.\s+([^\n:]+):\s*\n((?:•.+?\n?)+)'
            matches = list(re.finditer(numbered_pattern, answer, re.MULTILINE))

            if len(matches) >= 2:
                for match in matches:
                    step_num = match.group(1)
                    title = match.group(2).strip()
                    content = match.group(3).strip()

                    # Extract actions
                    actions = [
                        action.strip('• ').strip()
                        for action in content.split('\n')
                        if action.strip().startswith('•')
                    ]

                    cases.append({
                        'case_type': 'scenario',
                        'step_number': int(step_num),
                        'title': title,
                        'description': title,
                        'actions': actions,
                        'content': content
                    })

        return cases

    def extract_all_cases(self) -> List[Dict]:
        """Extract Case nodes from all FAQs"""
        print("\n[EXTRACT] Extracting Case nodes from FAQs...")

        faq_with_cases = 0
        total_cases = 0

        for faq in self.faqs:
            metadata = faq.get('metadata', {})
            question = metadata.get('question', '')
            answer = metadata.get('answer', '')

            if not answer:
                continue

            # Extract cases from this answer
            cases = self._extract_cases_from_answer(answer)

            if cases:
                faq_with_cases += 1
                total_cases += len(cases)

                # Add FAQ context to each case
                for idx, case in enumerate(cases):
                    case['case_index'] = idx  # Unique index within this FAQ
                    case['question_id'] = f"faq_{faq_with_cases}"
                    case['question_text'] = question
                    case['section'] = metadata.get('section', 'Unknown')
                    case['source'] = metadata.get('source', 'Unknown')

                self.case_nodes.extend(cases)

        print(f"\n[RESULTS] Extraction Results:")
        print(f"   FAQs with cases: {faq_with_cases}")
        print(f"   Total Case nodes: {total_cases}")

        # Group by case type
        by_type = {}
        for case in self.case_nodes:
            case_type = case['case_type']
            by_type[case_type] = by_type.get(case_type, 0) + 1

        print(f"\n[STATS] Cases by type:")
        for case_type, count in by_type.items():
            print(f"   {case_type}: {count}")

        return self.case_nodes

    def save_cases(self, output_file: str):
        """Save extracted Case nodes to JSON file"""
        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.case_nodes, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Saved {len(self.case_nodes)} Case nodes to {output_path}")

    def print_sample_cases(self, limit: int = 5):
        """Print sample extracted cases"""
        print(f"\n[SAMPLES] Sample extracted cases (showing {min(limit, len(self.case_nodes))} of {len(self.case_nodes)}):")

        for i, case in enumerate(self.case_nodes[:limit], 1):
            print(f"\n--- Case {i} ---")
            print(f"Type: {case['case_type']}")
            print(f"Question: {case['question_text'][:80]}...")
            print(f"Description: {case['description']}")

            if case['case_type'] == 'status':
                print(f"Status: {case['status']}")
                print(f"Step: {case['step_number']}")
            elif case['case_type'] == 'if_then':
                print(f"Condition: {case['condition'][:60]}...")
                print(f"Consequence: {case['consequence'][:60]}...")

            print(f"Actions ({len(case['actions'])}):")
            for action in case['actions'][:3]:
                print(f"  • {action[:80]}...")


def main():
    """Main execution"""
    import sys
    import io

    # Fix console encoding for Vietnamese text
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    data_file = r"c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\VNPT_Media_Software\Chatbot\data\paraphrase_documents.json"
    output_file = r"c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\VNPT_Media_Software\Chatbot\data\extracted_case_nodes.json"

    print("=" * 80)
    print("CASE NODE EXTRACTION")
    print("=" * 80)

    extractor = CaseNodeExtractor(data_file)
    extractor.load_data()

    # Extract all cases
    cases = extractor.extract_all_cases()

    # Print samples
    extractor.print_sample_cases(limit=5)

    # Save to file
    extractor.save_cases(output_file)

    print("\n" + "=" * 80)
    print("[COMPLETE] EXTRACTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
