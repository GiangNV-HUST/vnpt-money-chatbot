# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager

engine = Neo4jGraphRAGEngine()
manager = ConversationContextManager()

# Simulate flow
initial_response = {
    "answer": """Để nạp tiền từ ngân hàng vào VNPT Money:

Bước 1: Tại giao diện chính, chọn mục "Nạp tiền".
Bước 2: Chọn "Từ ngân hàng".
Bước 3: Chọn ngân hàng và nhập số tiền.
Bước 4: Xác nhận giao dịch.
Bước 5: Nhập OTP để hoàn tất.""",
    "all_results": [{"question_id": "FAQ_129"}],
    "related_entities": {"topics": ["Nạp tiền"]}
}

manager.add_turn("Làm sao nạp tiền?", initial_response)

# User completed 4 steps
continuation_context = manager.get_continuation_context("Tôi đã làm xong 4 bước đầu")
print(f"Continuation context: {continuation_context.get('topic')}, completed={continuation_context.get('completed_step')}, next={continuation_context.get('next_step')}")

# Call engine directly
result = engine.query("Tôi đã làm xong 4 bước đầu", continuation_context=continuation_context)

print(f"\n1. Result answer:\n{result['answer'][:200]}")
print(f"   is_continuation: {result.get('is_continuation')}")

# Update context
manager.add_turn("Tôi đã làm xong 4 bước đầu", result)

# Continue again
continuation_context2 = manager.get_continuation_context("tiếp tục")
print(f"\n2. Continuation context: completed={continuation_context2.get('completed_step')}, next={continuation_context2.get('next_step')}")

result2 = engine.query("tiếp tục", continuation_context=continuation_context2)

print(f"\n2. Result answer:\n{result2['answer']}")
print(f"   is_continuation: {result2.get('is_continuation')}")
print(f"   is_completed: {result2.get('is_completed')}")

if 'hotline' in result2['answer'].lower() or 'hoàn thành' in result2['answer'].lower():
    print("\n✅ RAW RESPONSE HAS COMPLETION")
else:
    print("\n❌ RAW RESPONSE NO COMPLETION")
