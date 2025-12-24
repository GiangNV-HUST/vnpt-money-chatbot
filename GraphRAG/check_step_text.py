"""Check step text format in database"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

# Query first 3 steps of transfer process
cypher = """
MATCH (p:Process)-[:HAS_STEP]->(s:Step)
WHERE toLower(p.name) CONTAINS 'transfer'
RETURN s.number as step_num, s.text as step_text
ORDER BY s.number
LIMIT 5
"""

results = connector.execute_query(cypher)

print("=" * 80)
print("Step Text Format in Database")
print("=" * 80)

for r in results:
    print(f"\nBước {r['step_num']}:")
    print(f"Text: '{r['step_text']}'")
    print(f"Length: {len(r['step_text'])}")
    print(f"Has newlines: {chr(10) in r['step_text']}")
    if chr(10) in r['step_text']:
        lines = r['step_text'].split('\n')
        print(f"Number of lines: {len(lines)}")
        for idx, line in enumerate(lines, 1):
            print(f"  Line {idx}: '{line.strip()}'")

connector.close()
