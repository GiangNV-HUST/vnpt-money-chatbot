# -*- coding: utf-8 -*-
"""
Simple test to check next_steps structure
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager

# Test direct continuation handling
engine = Neo4jGraphRAGEngine()
manager = ConversationContextManager()

print("=" * 80)
print("STEP 1: Simulate initial query")
print("=" * 80)

# Simulate that user asked "Làm sao rút tiền" and got answer
initial_response = {
    "answer": """Để rút tiền từ ví VNPT Pay về ngân hàng:

Bước 1: Tại giao diện chính, chọn mục "Rút tiền".
Bước 2: Nhập số tiền cần rút và nhấn "Tiếp tục".
Bước 3: Màn hình Xác nhận giao dịch và nhấn "Rút tiền".
Bước 4: Màn hình nhập OTP.
Bước 5: Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả.""",
    "all_results": [{"question_id": "FAQ_RUT_TIEN"}],
    "related_entities": {"topics": ["rút tiền"]}
}

manager.add_turn("Làm sao rút tiền?", initial_response)

print(f"\nContext after initial query:")
print(f"  current_step: {manager.current_context.get('current_step')}")
print(f"  all_steps: {len(manager.current_context.get('all_steps', []))} steps")
print(f"  last_faq_id: {manager.current_context.get('last_faq_id')}")

print("\n" + "=" * 80)
print("STEP 2: User says '4 bước đầu'")
print("=" * 80)

# Get continuation context
query2 = "tôi đã làm xong 4 bước đầu"
continuation_context = manager.get_continuation_context(query2)

print(f"\nContinuation context:")
print(f"  completed_step: {continuation_context.get('completed_step')}")
print(f"  next_step: {continuation_context.get('next_step')}")
print(f"  faq_id: {continuation_context.get('faq_id')}")

# Call _handle_continuation directly
print(f"\nCalling _handle_continuation...")
result = engine._handle_continuation(query2, continuation_context)

print(f"\nResult keys: {result.keys()}")
print(f"  is_continuation: {result.get('is_continuation')}")
print(f"  next_steps: {result.get('next_steps')}")
print(f"  answer: {result.get('answer')[:100]}...")

# Check next_steps structure
next_steps = result.get('next_steps', [])
if next_steps:
    print(f"\nChecking next_steps structure:")
    for i, step in enumerate(next_steps):
        print(f"  Step {i}: {step}")
        if isinstance(step, dict):
            print(f"    Has 'number' key: {'number' in step}")
            print(f"    'number' value: {step.get('number', 'NOT FOUND')}")
else:
    print(f"\n❌ next_steps is empty!")

print("\n" + "=" * 80)
print("STEP 3: Add to context and check current_step")
print("=" * 80)

manager.add_turn(query2, result)

print(f"\nContext after continuation:")
print(f"  current_step: {manager.current_context.get('current_step')}")
print(f"  Expected: 5")

if manager.current_context.get('current_step') == 5:
    print(f"\n✅ SUCCESS: current_step correctly updated to 5")
else:
    print(f"\n❌ FAIL: current_step is {manager.current_context.get('current_step')}, not 5")

print("\n" + "=" * 80)
