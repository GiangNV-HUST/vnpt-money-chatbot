# -*- coding: utf-8 -*-
"""
Test RAW response from engine for Hủy nạp tiền tự động
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager

engine = Neo4jGraphRAGEngine()
manager = ConversationContextManager()

print("=" * 80)
print("RAW RESPONSE TEST: Hủy nạp tiền tự động")
print("=" * 80)

# Query directly to engine
result = engine.query("Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?")

print(f"\n1. RAW Answer from engine:")
print("=" * 80)
print(result['answer'])
print("=" * 80)

# Count steps
step_count = result['answer'].count("Bước")
print(f"\nRAW answer has {step_count} steps")

# Check steps field
if 'steps' in result:
    print(f"Steps field: {result['steps']}")

# Check all_results
if 'all_results' in result and result['all_results']:
    print(f"\nFAQ ID: {result['all_results'][0].get('question_id')}")
    print(f"Question: {result['all_results'][0].get('question', '')[:80]}...")
