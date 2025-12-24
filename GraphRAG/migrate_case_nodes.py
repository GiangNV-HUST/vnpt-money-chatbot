"""
Migrate Case nodes to Neo4j graph database
Adds Case nodes and relationships for conditional scenarios in FAQs
"""

import json
import sys
import io
from typing import List, Dict
from pathlib import Path
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv


class CaseNodeMigrator:
    """Migrate Case nodes to Neo4j"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.case_nodes = []
        self.stats = {
            'cases_added': 0,
            'relationships_created': 0,
            'faqs_updated': 0
        }

    def close(self):
        """Close Neo4j driver"""
        self.driver.close()

    def load_case_data(self, case_file: str):
        """Load extracted Case nodes from JSON"""
        with open(case_file, 'r', encoding='utf-8') as f:
            self.case_nodes = json.load(f)
        print(f"[OK] Loaded {len(self.case_nodes)} Case nodes from {case_file}")

    def _create_case_node_cypher(self, case: Dict) -> str:
        """
        Generate Cypher query to create a Case node

        Case node properties:
        - case_id: Unique identifier
        - case_type: 'status', 'if_then', or 'scenario'
        - description: Brief description
        - status: Status value (for status-based cases)
        - condition: Condition text (for if-then cases)
        - consequence: Consequence text (for if-then cases)
        - actions: List of action items
        - step_number: Step number in the FAQ (if applicable)
        """
        case_id = f"{case['question_id']}_case_{case.get('case_index', 0)}"
        case_type = case['case_type']
        description = case['description'].replace('"', '\\"').replace('\n', '\\n')
        actions = json.dumps(case['actions'], ensure_ascii=False)

        # Base properties
        properties = [
            f'case_id: "{case_id}"',
            f'case_type: "{case_type}"',
            f'description: "{description}"',
            f'actions: {actions}'
        ]

        # Add type-specific properties
        if case_type == 'status':
            status = case['status'].replace('"', '\\"')
            step_num = case.get('step_number', 0)
            properties.append(f'status: "{status}"')
            properties.append(f'step_number: {step_num}')

        elif case_type == 'if_then':
            condition = case['condition'].replace('"', '\\"').replace('\n', '\\n')
            consequence = case['consequence'].replace('"', '\\"').replace('\n', '\\n')
            properties.append(f'condition: "{condition}"')
            properties.append(f'consequence: "{consequence}"')

        elif case_type == 'scenario':
            title = case.get('title', '').replace('"', '\\"')
            step_num = case.get('step_number', 0)
            properties.append(f'title: "{title}"')
            properties.append(f'step_number: {step_num}')

        # Create node query
        props_str = ', '.join(properties)
        query = f"CREATE (c:Case {{{props_str}}})"

        return query

    def _link_case_to_faq_cypher(self, case: Dict) -> str:
        """
        Generate Cypher query to link Case node to FAQ node

        Creates relationship: (FAQ)-[:HAS_CASE]->(Case)
        """
        case_id = f"{case['question_id']}_case_{case.get('case_index', 0)}"
        question_text = case['question_text'].replace('"', '\\"')

        query = f"""
        MATCH (f:FAQ {{question: "{question_text}"}})
        MATCH (c:Case {{case_id: "{case_id}"}})
        CREATE (f)-[:HAS_CASE]->(c)
        """

        return query

    def _dry_run_migration(self) -> List[str]:
        """Generate all Cypher queries without executing (dry run)"""
        print("\n[DRY RUN] Generating Cypher queries...")

        queries = []

        # Group cases by FAQ
        cases_by_faq = {}
        for case in self.case_nodes:
            question = case['question_text']
            if question not in cases_by_faq:
                cases_by_faq[question] = []
            cases_by_faq[question].append(case)

        print(f"\n[INFO] Processing {len(cases_by_faq)} FAQs with cases")

        # Generate queries for each FAQ
        for question, cases in cases_by_faq.items():
            print(f"\nFAQ: {question[:80]}...")
            print(f"Cases: {len(cases)}")

            for case in cases:
                # Create Case node
                create_query = self._create_case_node_cypher(case)
                queries.append(create_query)

                # Link to FAQ
                link_query = self._link_case_to_faq_cypher(case)
                queries.append(link_query)

        print(f"\n[DRY RUN] Generated {len(queries)} Cypher queries")
        return queries

    def _execute_migration(self, dry_run: bool = True):
        """Execute migration to Neo4j"""
        if dry_run:
            queries = self._dry_run_migration()

            # Save queries to file
            output_file = Path(__file__).parent.parent / 'data' / 'case_migration_queries.cypher'
            with open(output_file, 'w', encoding='utf-8') as f:
                for query in queries:
                    f.write(query.strip() + ';\n\n')

            print(f"\n[OK] Saved queries to {output_file}")
            print("\n[DRY RUN] No changes made to database")
            print("[INFO] To execute migration, run with --execute flag")
            return

        # Execute actual migration
        print("\n[EXECUTE] Running migration to Neo4j...")

        with self.driver.session() as session:
            # Group cases by FAQ
            cases_by_faq = {}
            for case in self.case_nodes:
                question = case['question_text']
                if question not in cases_by_faq:
                    cases_by_faq[question] = []
                cases_by_faq[question].append(case)

            # Process each FAQ
            for question, cases in cases_by_faq.items():
                print(f"\n[MIGRATE] {question[:60]}... ({len(cases)} cases)")

                for case in cases:
                    try:
                        # Create Case node
                        create_query = self._create_case_node_cypher(case)
                        session.run(create_query)
                        self.stats['cases_added'] += 1

                        # Link to FAQ
                        link_query = self._link_case_to_faq_cypher(case)
                        session.run(link_query)
                        self.stats['relationships_created'] += 1

                    except Exception as e:
                        print(f"[ERROR] Failed to process case: {e}")
                        continue

                self.stats['faqs_updated'] += 1

        print("\n[COMPLETE] Migration finished")
        print(f"[STATS] Cases added: {self.stats['cases_added']}")
        print(f"[STATS] Relationships created: {self.stats['relationships_created']}")
        print(f"[STATS] FAQs updated: {self.stats['faqs_updated']}")

    def migrate(self, dry_run: bool = True):
        """Run migration (dry run by default)"""
        self._execute_migration(dry_run=dry_run)


def main():
    """Main execution"""
    # Fix console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Load environment from graphRAGChatBot/.env
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)

    # Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')

    # File paths
    case_file = Path(__file__).parent.parent / 'data' / 'extracted_case_nodes.json'

    # Check arguments
    dry_run = '--execute' not in sys.argv

    print("=" * 80)
    print("CASE NODE MIGRATION TO NEO4J")
    if dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    else:
        print("MODE: EXECUTE (will modify database)")
    print("=" * 80)

    # Create migrator
    migrator = CaseNodeMigrator(neo4j_uri, neo4j_user, neo4j_password)

    try:
        # Load data
        migrator.load_case_data(case_file)

        # Run migration
        migrator.migrate(dry_run=dry_run)

        print("\n" + "=" * 80)
        if dry_run:
            print("[DRY RUN COMPLETE]")
            print("To execute migration, run: python migrate_case_nodes.py --execute")
        else:
            print("[MIGRATION COMPLETE]")
        print("=" * 80)

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
