# -*- coding: utf-8 -*-
"""
Test Hủy nạp tiền tự động with detailed logging
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')

from chatbot import GraphRAGChatbot

print("=" * 80)
print("TEST: Hủy nạp tiền tự động (with detailed logging)")
print("=" * 80)

chatbot = GraphRAGChatbot()

# Query 1: Initial
print("\n1. User: Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?")
print("-" * 80)
r1 = chatbot.chat("Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?")
answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))

# Count steps in answer
step_count = answer1.count("Bước")
print(f"\n📝 Answer 1 has {step_count} steps (Bước)")
print(f"Answer preview:\n{answer1[:500]}...")

# Check context
print(f"\n📊 Context after Q1:")
print(f"   all_steps count: {len(chatbot.context_manager.current_context.get('all_steps', []))}")
all_steps = chatbot.context_manager.current_context.get('all_steps', [])
if all_steps:
    print(f"   Steps: {[s['step_number'] for s in all_steps]}")
print(f"   last_faq_id: {chatbot.context_manager.current_context.get('last_faq_id')}")
print(f"   topic: {chatbot.context_manager.current_context.get('topic')}")

# Query 2: Complete 5 steps
print("\n2. User: Tôi đã làm xong 5 bước đầu")
print("-" * 80)
r2 = chatbot.chat("Tôi đã làm xong 5 bước đầu")

print(f"\n📊 Context after Q2:")
print(f"   all_steps count: {len(chatbot.context_manager.current_context.get('all_steps', []))}")
print(f"   current_step: {chatbot.context_manager.current_context.get('current_step')}")
print(f"   last_faq_id: {chatbot.context_manager.current_context.get('last_faq_id')}")

# Query 3: Continue (should show step 6)
print("\n3. User: tiếp tục")
print("-" * 80)
r3 = chatbot.chat("tiếp tục")
answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))

print(f"\n📊 Context after Q3:")
print(f"   all_steps count: {len(chatbot.context_manager.current_context.get('all_steps', []))}")
print(f"   current_step: {chatbot.context_manager.current_context.get('current_step')}")

print(f"\n📝 Answer 3 preview:")
print(answer3[:300])

# Query 4: Continue (should show COMPLETION)
print("\n4. User: tiếp tục (SHOULD SHOW COMPLETION)")
print("-" * 80)
r4 = chatbot.chat("tiếp tục")
answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

print(f"\n📊 Context after Q4:")
print(f"   all_steps count: {len(chatbot.context_manager.current_context.get('all_steps', []))}")
print(f"   current_step: {chatbot.context_manager.current_context.get('current_step')}")

print(f"\n📝 Answer 4 (FULL):")
print(answer4)

# Check for completion
has_completion = (
    ("hotline" in answer4.lower() and "1900" in answer4) or
    ("hoàn thành" in answer4.lower() and "✅" in answer4)
)

print(f"\n{'=' * 80}")
if has_completion:
    print("✅ SUCCESS: Shows completion message")
else:
    print("❌ FAIL: No completion message")
    print(f"\nExpected: ✅ Bạn đã hoàn thành tất cả 6 bước!")
    print(f"Got: {answer4[:150]}...")
