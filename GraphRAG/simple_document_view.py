# -*- coding: utf-8 -*-
"""
Simple view of one document processing result
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from neo4j_connector import Neo4jConnector

connector = Neo4jConnector()

# Pick the same FAQ we've been testing
cypher = """
MATCH (f:FAQ {id: 'FAQ_18'})
RETURN f
"""

faq_result = connector.execute_query(cypher)
faq = faq_result[0]['f']

print("\n" + "=" * 80)
print("📄 ORIGINAL DOCUMENT")
print("=" * 80)
print(f"\nID: {faq['id']}")
print(f"\n📝 Question:")
print(f"{faq['question']}")
print(f"\n💬 Answer (first 500 chars):")
print(f"{faq['answer'][:500]}...")
print(f"\n✓ Full answer length: {len(faq['answer'])} characters")
print(f"✓ Has embedding: Yes ({len(faq.get('embedding', []))} dimensions)")

# Get entities
cypher_entities = """
MATCH (f:FAQ {id: 'FAQ_18'})-[r]->(e)
RETURN type(r) as rel_type, labels(e)[0] as entity_type, e.name as entity_name
ORDER BY rel_type, entity_type
"""

entities = connector.execute_query(cypher_entities)

print("\n" + "=" * 80)
print("🔗 EXTRACTED STRUCTURE (Entities & Relationships)")
print("=" * 80)

# Group by relationship type
from collections import defaultdict
grouped = defaultdict(list)
for ent in entities:
    grouped[ent['rel_type']].append(f"{ent['entity_type']}: {ent['entity_name']}")

for rel_type, entity_list in sorted(grouped.items()):
    print(f"\n{rel_type}:")
    for entity in entity_list[:5]:  # Show max 5 per type
        print(f"  → {entity}")
    if len(entity_list) > 5:
        print(f"  ... and {len(entity_list) - 5} more")

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print(f"""
✅ ORIGINAL CONTENT: PRESERVED
   - Question: {len(faq['question'])} chars
   - Answer: {len(faq['answer'])} chars (FULL TEXT)
   - Total: {len(faq['question']) + len(faq['answer'])} chars

✅ STRUCTURE ADDED (NOT REPLACED):
   - {len(entities)} entity connections
   - {len(grouped)} relationship types
   - Embedding: {len(faq.get('embedding', []))} dimensions

💡 KEY INSIGHT:
   Entities are METADATA that helps find this document.
   The FULL CONTENT is still here for the answer!
""")

print("\n" + "=" * 80)
print("🎯 HOW IT WORKS IN PRACTICE")
print("=" * 80)
print("""
User asks: "Chuyển tiền mà chưa nhận được"

STEP 1: Extract entities
  → Error: "chưa nhận được"
  → Topic: "Chuyển tiền"

STEP 2: Graph traversal
  FAQ_18 -[DESCRIBES_ERROR]-> Error("chưa nhận được") ✓
  FAQ_18 -[ABOUT]-> Topic("Chuyển tiền") ✓

STEP 3: Retrieve FULL ANSWER
  Return all 1259 characters of the answer!

RESULT: User gets complete, accurate answer
""")

connector.close()
