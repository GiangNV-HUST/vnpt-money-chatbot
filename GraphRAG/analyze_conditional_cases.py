"""
Analyze paraphrase_documents.json to identify FAQs with conditional cases
This script finds all answers that contain multiple conditional scenarios
"""

import json
import re
from typing import List, Dict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConditionalCaseAnalyzer:
    """Analyze FAQs to find conditional cases (status-based, if-then, etc.)"""

    def __init__(self, data_path: str):
        """Initialize analyzer with data path"""
        self.data_path = Path(data_path)
        self.faqs = []
        self.conditional_faqs = []

    def load_data(self):
        """Load FAQ data from JSON"""
        logger.info(f"Loading data from {self.data_path}")
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.faqs = json.load(f)
        logger.info(f"Loaded {len(self.faqs)} FAQs")

    def analyze_all(self):
        """Analyze all FAQs to find conditional cases"""
        logger.info("Analyzing FAQs for conditional cases...")

        status_based = []
        if_then_based = []
        case_based = []
        numbered_scenarios = []

        for idx, faq in enumerate(self.faqs):
            metadata = faq.get('metadata', {})
            answer = metadata.get('answer', '')
            question = metadata.get('question', '')

            # Skip if no answer
            if not answer:
                continue

            # Check for different types of conditional patterns
            analysis = self._analyze_answer(answer)

            if analysis['has_conditionals']:
                faq_data = {
                    'index': idx,
                    'question': question,
                    'answer': answer,
                    'type': analysis['type'],
                    'cases': analysis['cases'],
                    'num_cases': len(analysis['cases'])
                }

                self.conditional_faqs.append(faq_data)

                # Categorize by type
                if analysis['type'] == 'status_based':
                    status_based.append(faq_data)
                elif analysis['type'] == 'if_then':
                    if_then_based.append(faq_data)
                elif analysis['type'] == 'case_based':
                    case_based.append(faq_data)
                elif analysis['type'] == 'numbered_scenarios':
                    numbered_scenarios.append(faq_data)

        # Summary
        logger.info("=" * 80)
        logger.info("ANALYSIS RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Total FAQs: {len(self.faqs)}")
        logger.info(f"FAQs with conditional cases: {len(self.conditional_faqs)}")
        logger.info(f"  - Status-based (trạng thái): {len(status_based)}")
        logger.info(f"  - If-then (Nếu...thì): {len(if_then_based)}")
        logger.info(f"  - Case-based (Trường hợp): {len(case_based)}")
        logger.info(f"  - Numbered scenarios: {len(numbered_scenarios)}")

        return {
            'total': len(self.faqs),
            'conditional': len(self.conditional_faqs),
            'status_based': status_based,
            'if_then': if_then_based,
            'case_based': case_based,
            'numbered_scenarios': numbered_scenarios
        }

    def _analyze_answer(self, answer: str) -> Dict:
        """Analyze a single answer for conditional patterns"""
        result = {
            'has_conditionals': False,
            'type': None,
            'cases': []
        }

        answer_lower = answer.lower()

        # Pattern 1: Status-based conditionals
        # "Nếu trạng thái là 'Thành công'", "Trường hợp trạng thái 'Đang xử lý'"
        status_pattern = r'(nếu\s+|trường\s+hợp\s+)?trạng\s+thái\s+(là|bào|hiển\s+thị)?\s*["\']?(thành\s+công|đang\s+xử\s+lý|thất\s+bại)["\']?'
        status_matches = list(re.finditer(status_pattern, answer_lower))

        if len(status_matches) >= 2:
            result['has_conditionals'] = True
            result['type'] = 'status_based'

            # Extract each status case
            for match in status_matches:
                status = match.group(3).strip()
                # Find the full case text (until next status or end)
                start_pos = match.start()

                # Try to find where this case ends
                remaining_text = answer[start_pos:]
                next_case = re.search(r'\n\s*\d+\.|nếu\s+trạng\s+thái|trường\s+hợp',
                                     remaining_text[100:], re.IGNORECASE)

                if next_case:
                    case_text = remaining_text[:100 + next_case.start()]
                else:
                    case_text = remaining_text[:500]  # Cap at 500 chars

                result['cases'].append({
                    'condition_type': 'status',
                    'status': status,
                    'text_preview': case_text[:200].strip()
                })

            return result

        # Pattern 2: If-then conditionals
        # "Nếu...thì...", "Nếu A: ...", multiple "Nếu" statements
        if_then_pattern = r'nếu\s+[^:]+:'
        if_then_matches = list(re.finditer(if_then_pattern, answer_lower))

        if len(if_then_matches) >= 2:
            result['has_conditionals'] = True
            result['type'] = 'if_then'

            for match in if_then_matches:
                condition = match.group(0).replace('nếu', '').replace(':', '').strip()
                result['cases'].append({
                    'condition_type': 'if_then',
                    'condition': condition,
                    'text_preview': answer[match.start():match.start()+150].strip()
                })

            return result

        # Pattern 3: Explicit "Trường hợp" (Case) mentions
        case_pattern = r'trường\s+hợp\s+\d+|trường\s+hợp\s+[^:\n]{5,50}:'
        case_matches = list(re.finditer(case_pattern, answer_lower))

        if len(case_matches) >= 2:
            result['has_conditionals'] = True
            result['type'] = 'case_based'

            for match in case_matches:
                case_desc = match.group(0).strip()
                result['cases'].append({
                    'condition_type': 'case',
                    'description': case_desc,
                    'text_preview': answer[match.start():match.start()+150].strip()
                })

            return result

        # Pattern 4: Numbered scenarios with different outcomes
        # Look for pattern like "1. ... 2. ... 3. ..." where each describes different scenario
        numbered_pattern = r'^\d+\.\s+[^\n]+(?:trạng\s+thái|nếu|trường\s+hợp)'
        numbered_matches = list(re.finditer(numbered_pattern, answer_lower, re.MULTILINE))

        if len(numbered_matches) >= 2:
            result['has_conditionals'] = True
            result['type'] = 'numbered_scenarios'

            for match in numbered_matches:
                result['cases'].append({
                    'condition_type': 'numbered',
                    'text_preview': answer[match.start():match.start()+150].strip()
                })

            return result

        return result

    def print_samples(self, category: str = 'status_based', limit: int = 3):
        """Print sample FAQs from a category"""
        results = self.analyze_all()
        samples = results.get(category, [])

        logger.info(f"\n{'=' * 80}")
        logger.info(f"SAMPLES: {category.upper()} (showing {min(limit, len(samples))} of {len(samples)})")
        logger.info(f"{'=' * 80}")

        for i, faq in enumerate(samples[:limit]):
            logger.info(f"\nSample {i+1}:")
            logger.info(f"Question: {faq['question'][:100]}...")
            logger.info(f"Number of cases: {faq['num_cases']}")
            logger.info("Cases found:")
            for j, case in enumerate(faq['cases'], 1):
                logger.info(f"  {j}. {case}")
            logger.info("-" * 80)

    def export_results(self, output_path: str):
        """Export analysis results to JSON"""
        results = self.analyze_all()

        output = {
            'summary': {
                'total_faqs': results['total'],
                'conditional_faqs': results['conditional'],
                'by_type': {
                    'status_based': len(results['status_based']),
                    'if_then': len(results['if_then']),
                    'case_based': len(results['case_based']),
                    'numbered_scenarios': len(results['numbered_scenarios'])
                }
            },
            'conditional_faqs': self.conditional_faqs
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"\nResults exported to: {output_path}")
        return output_path


if __name__ == "__main__":
    # Path to data
    data_path = Path(__file__).parent.parent / "data" / "paraphrase_documents.json"

    # Initialize analyzer
    analyzer = ConditionalCaseAnalyzer(data_path)

    # Load data
    analyzer.load_data()

    # Analyze
    results = analyzer.analyze_all()

    # Print samples from each category
    for category in ['status_based', 'if_then', 'case_based', 'numbered_scenarios']:
        if results[category]:
            analyzer.print_samples(category, limit=2)

    # Export results
    output_path = Path(__file__).parent / "data" / "conditional_cases_analysis.json"
    analyzer.export_results(output_path)

    logger.info("\n✅ Analysis complete!")
