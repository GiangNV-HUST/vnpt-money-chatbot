# Fix Neo4j property from faq_id to id
import re

with open('neo4j_rag_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all instances of {faq_id: $faq_id} with {id: $faq_id}
content = content.replace('{faq_id: $faq_id}', '{id: $faq_id}')
content = content.replace('{{faq_id: $faq_id}}', '{{id: $faq_id}}')

with open('neo4j_rag_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed: faq_id -> id in Neo4j queries')
