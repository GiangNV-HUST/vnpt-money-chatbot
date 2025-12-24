# coding: utf-8
"""
Migration script: Extract steps from FAQs and create Step nodes in Neo4j
"""

import json
import re
from typing import List, Dict
from neo4j_connector import Neo4jConnector
from step_tracker import StepTracker

def load_faqs_with_steps(json_path: str) -> List[Dict]:
    """Load all FAQs that contain steps"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter FAQs with steps
    faqs_with_steps = [
        d for d in data
        if 'Bước' in d['metadata']['answer']
    ]

    return faqs_with_steps


def identify_process_name(question: str, answer: str) -> str:
    """
    Identify process name from question/answer
    Returns a simplified process identifier like "deposit", "withdrawal", "transfer"
    """
    text = (question + " " + answer).lower()

    # Map keywords to process names
    process_keywords = {
        'nạp tiền': 'deposit',
        'rút tiền': 'withdrawal',
        'chuyển tiền': 'transfer',
        'liên kết ngân hàng': 'link_bank',
        'hủy liên kết': 'unlink_bank',
        'đăng ký': 'register',
        'đăng nhập': 'login',
        'quên mật khẩu': 'reset_password',
        'mua vé': 'buy_ticket',
        'thanh toán': 'payment',
        'tra cứu': 'lookup',
        'kiểm tra': 'check',
    }

    for keyword, process_name in process_keywords.items():
        if keyword in text:
            return process_name

    return 'general'


def extract_steps_from_answer(answer: str) -> List[Dict]:
    """
    Extract steps from answer using regex
    Returns: [{"number": 1, "text": "..."}, ...]
    """
    steps = []

    # Pattern: "Bước 1:", "Bước 2:", etc.
    step_pattern = r'Bước\s+(\d+):\s*(.+?)(?=Bước\s+\d+:|$|-\s*Nạp|$)'
    matches = re.finditer(step_pattern, answer, re.DOTALL | re.IGNORECASE)

    for match in matches:
        step_num = int(match.group(1))
        step_text = match.group(2).strip()

        # Clean up step text
        step_text = re.sub(r'\n+', ' ', step_text)  # Remove newlines
        step_text = re.sub(r'\s+', ' ', step_text)  # Normalize spaces
        step_text = step_text.strip()

        if step_text:
            steps.append({
                "number": step_num,
                "text": step_text
            })

    return steps


def create_migration_queries(faqs_with_steps: List[Dict]) -> List[str]:
    """
    Generate Cypher queries to create Step nodes and relationships
    """
    queries = []

    # Statistics
    total_steps = 0
    processes = {}

    # Write analysis to file instead of console
    analysis_file = open('_migration_analysis.txt', 'w', encoding='utf-8')
    analysis_file.write("="*80 + "\n")
    analysis_file.write("ANALYZING FAQs WITH STEPS\n")
    analysis_file.write("="*80 + "\n")

    for i, faq_data in enumerate(faqs_with_steps):
        metadata = faq_data['metadata']
        question = metadata['question']
        answer = metadata['answer']

        # Extract steps
        steps = extract_steps_from_answer(answer)

        if not steps:
            continue

        # Identify process
        process_name = identify_process_name(question, answer)
        processes[process_name] = processes.get(process_name, 0) + 1

        total_steps += len(steps)

        # Create unique process ID for this FAQ
        # Use combination of process_name + first 50 chars of question
        process_id = f"{process_name}_{question[:50].replace(' ', '_')}"

        # Write preview for first 10
        if i < 10:
            analysis_file.write(f"\n{i+1}. Question: {question[:80]}...\n")
            analysis_file.write(f"   Process: {process_name}\n")
            analysis_file.write(f"   Steps: {len(steps)}\n")
            for step in steps[:3]:
                analysis_file.write(f"     - Step {step['number']}: {step['text'][:60]}...\n")

        # Generate Cypher query for this FAQ
        query_parts = []

        # Escape quotes in question for Cypher
        question_escaped = question.replace('"', '\\"')
        process_id_escaped = process_id.replace('"', '\\"')

        # 1. Find the FAQ node
        query_parts.append(f"""
// FAQ {i+1}: {question[:60]}...
MATCH (faq:FAQ {{question: "{question_escaped}"}})
""")

        # 2. Create or merge Process node
        query_parts.append(f"""
MERGE (p:Process {{
    id: "{process_id_escaped}",
    name: "{process_name}",
    description: "{question_escaped}"
}})
""")

        # 3. Create Step nodes and relationships
        for step in steps:
            step_id = f"{process_id}_step_{step['number']}"
            step_id_escaped = step_id.replace('"', '\\"')
            step_text_escaped = step['text'].replace('"', '\\"')  # Escape quotes

            query_parts.append(f"""
MERGE (s{step['number']}:Step {{
    id: "{step_id_escaped}",
    number: {step['number']},
    text: "{step_text_escaped}",
    process_id: "{process_id_escaped}"
}})
""")

        # 4. Create relationships: FAQ -> Process, Process -> Steps, Step -> Next Step
        query_parts.append("""
MERGE (faq)-[:DESCRIBES_PROCESS]->(p)
""")

        for step in steps:
            query_parts.append(f"""
MERGE (p)-[:HAS_STEP]->(s{step['number']})
""")

        # Create NEXT_STEP relationships
        for j in range(len(steps) - 1):
            query_parts.append(f"""
MERGE (s{steps[j]['number']})-[:NEXT_STEP]->(s{steps[j+1]['number']})
""")

        # Combine all parts
        full_query = "\n".join(query_parts)
        queries.append(full_query)

    # Write summary to file
    analysis_file.write("\n" + "="*80 + "\n")
    analysis_file.write("MIGRATION SUMMARY\n")
    analysis_file.write("="*80 + "\n")
    analysis_file.write(f"Total FAQs with steps: {len(faqs_with_steps)}\n")
    analysis_file.write(f"Total steps to create: {total_steps}\n")
    analysis_file.write(f"\nProcesses breakdown:\n")
    for process, count in sorted(processes.items(), key=lambda x: -x[1]):
        analysis_file.write(f"  - {process}: {count} FAQs\n")

    analysis_file.close()

    print(f"\nAnalysis written to _migration_analysis.txt")
    print(f"Total FAQs: {len(faqs_with_steps)}, Total steps: {total_steps}")

    return queries


def preview_migration(queries: List[str], num_preview: int = 3):
    """Preview first N queries - write to file"""
    with open('_migration_preview.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"PREVIEW: First {num_preview} Migration Queries\n")
        f.write("="*80 + "\n")

        for i, query in enumerate(queries[:num_preview]):
            f.write(f"\n--- Query {i+1} ---\n")
            f.write(query[:800] + "...\n" if len(query) > 800 else query + "\n")

    print(f"\nPreview written to _migration_preview.txt")


def execute_migration(queries: List[str], batch_size: int = 10):
    """Execute migration queries in batches"""
    conn = Neo4jConnector()

    print("\n" + "="*80)
    print("EXECUTING MIGRATION")
    print("="*80)

    total = len(queries)
    success = 0
    failed = 0

    for i in range(0, total, batch_size):
        batch = queries[i:i+batch_size]
        batch_num = i // batch_size + 1

        print(f"\nBatch {batch_num}/{(total + batch_size - 1) // batch_size}: Processing {len(batch)} queries...")

        for j, query in enumerate(batch):
            try:
                conn.execute_query(query, write=True)
                success += 1
                if (success % 10) == 0:
                    print(f"  Processed {success}/{total} queries")
            except Exception as e:
                failed += 1
                print(f"  Query {i+j+1} failed: {str(e)[:100]}")

    print("\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)
    print(f"Success: {success}/{total}")
    print(f"Failed: {failed}/{total}")

    return success, failed


if __name__ == "__main__":
    print("="*80)
    print("NEO4J STEP MIGRATION TOOL")
    print("="*80)

    # Load FAQs
    json_path = "../data/paraphrase_documents.json"
    print(f"\nLoading FAQs from: {json_path}")

    faqs_with_steps = load_faqs_with_steps(json_path)
    print(f"Found {len(faqs_with_steps)} FAQs with steps")

    # Generate migration queries
    print("\nGenerating migration queries...")
    queries = create_migration_queries(faqs_with_steps)

    # Preview
    preview_migration(queries, num_preview=2)

    # Ask for confirmation
    print("\n" + "="*80)
    response = input("Do you want to execute the migration? (yes/no): ").strip().lower()

    if response == 'yes':
        execute_migration(queries, batch_size=10)
    else:
        print("\nMigration cancelled. Queries saved to preview only.")

        # Save queries to file for manual review
        with open('_migration_queries.cypher', 'w', encoding='utf-8') as f:
            for i, query in enumerate(queries):
                f.write(f"// Query {i+1}\n")
                f.write(query)
                f.write("\n\n")

        print("Queries saved to _migration_queries.cypher for manual review")
