# -*- coding: utf-8 -*-
"""
Check what Error entities exist in the database
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_connector import Neo4jConnector

def check_error_entities():
    """Check Error entities in database"""
    print("="*60)
    print("CHECKING ERROR ENTITIES IN DATABASE")
    print("="*60)

    conn = Neo4jConnector()

    # Get all Error entities
    cypher = """
    MATCH (e:Error)
    RETURN e.name as error_name
    ORDER BY e.name
    """

    results = conn.execute_query(cypher)

    print(f"\nFound {len(results)} Error entities:\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['error_name']}")

    # Check if "chuyển tiền nhầm" entity exists
    print("\n" + "="*60)
    print("SEARCHING FOR 'CHUYỂN TIỀN NHẦM' ERROR ENTITY")
    print("="*60)

    cypher_search = """
    MATCH (e:Error)
    WHERE toLower(e.name) CONTAINS 'nhầm'
       OR toLower(e.name) CONTAINS 'sai'
       OR toLower(e.name) CONTAINS 'lỡ'
    RETURN e.name as error_name
    """

    results_search = conn.execute_query(cypher_search)

    if results_search:
        print(f"\nFound {len(results_search)} Error entities related to 'nhầm/sai/lỡ':")
        for r in results_search:
            print(f"  - {r['error_name']}")
    else:
        print("\nNO Error entity found for 'nhầm/sai/lỡ' ❌")

    # Check FAQs connected to "chuyển tiền nhầm" topic
    print("\n" + "="*60)
    print("CHECKING FAQ_16 RELATIONSHIPS")
    print("="*60)

    cypher_faq = """
    MATCH (f:FAQ {id: 'FAQ_16'})
    OPTIONAL MATCH (f)-[r]->(e)
    RETURN f.question as question, type(r) as rel_type, labels(e)[0] as entity_type, e.name as entity_name
    """

    results_faq = conn.execute_query(cypher_faq)

    print(f"\nFAQ_16: {results_faq[0]['question']}\n")
    print("Relationships:")
    for r in results_faq:
        if r['rel_type']:
            print(f"  - {r['rel_type']} → {r['entity_type']}: {r['entity_name']}")

    conn.close()


if __name__ == "__main__":
    check_error_entities()
