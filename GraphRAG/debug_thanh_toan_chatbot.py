# -*- coding: utf-8 -*-
"""
Debug why chatbot returns only 3 steps for Thanh toán hóa đơn viễn thông
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Suppress logs
import logging
logging.getLogger().setLevel(logging.ERROR)

from chatbot import GraphRAGChatbot

chatbot = GraphRAGChatbot()

question = "Làm thế nào để thanh toán hóa đơn viễn thông?"

result = chatbot.chat(question)

# Get answer
answer = result.get('answer', str(result)) if isinstance(result, dict) else str(result)

# Count steps in answer
import re
steps_found = re.findall(r'Bước\s+(\d+):', answer)
print(f"\n{len(steps_found)} steps in chatbot answer")
print(answer[:500])
print("\n...")

# Compare with direct engine call
from neo4j_rag_engine import Neo4jGraphRAGEngine
engine = Neo4jGraphRAGEngine()
engine_result = engine.query(question)
engine_answer = engine_result.get('answer', '')
engine_steps_found = re.findall(r'Bước\s+(\d+):', engine_answer)

print(f"\n{len(engine_steps_found)} steps in engine answer")
print(engine_answer[:500])
print("\n...")

print(f"\nStep count comparison:")
print(f"  Chatbot answer: {len(steps_found)} steps")
print(f"  Engine answer: {len(engine_steps_found)} steps")
print(f"  Engine result['steps']: {len(engine_result.get('steps', []))} steps")
