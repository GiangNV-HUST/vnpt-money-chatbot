# -*- coding: utf-8 -*-
"""
Test single case: Thanh toán hóa đơn viễn thông
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

print("=" * 80)
print("TEST: Thanh toán hóa đơn viễn thông (Payment - 6 bước)")
print("=" * 80)

chatbot = GraphRAGChatbot()

# Query 1: Initial
print(f"\n1. User: Tôi muốn thanh toán hóa đơn viễn thông qua VNPT Money")
print("-" * 80)
r1 = chatbot.chat("Tôi muốn thanh toán hóa đơn viễn thông qua VNPT Money")
answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))
print(f"Answer: {answer1[:200]}...")

# Query 2: Complete N-1 steps
print(f"\n2. User: Tôi đã làm xong 5 bước đầu")
print("-" * 80)
r2 = chatbot.chat(f"Tôi đã làm xong 5 bước đầu")
answer2 = r2 if isinstance(r2, str) else r2.get('answer', str(r2))
print(f"Answer: {answer2[:200]}...")

# Query 3: Continue (should show next step)
print(f"\n3. User: tiếp tục (should show step 6)")
print("-" * 80)
r3 = chatbot.chat("tiếp tục")
answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))
print(f"Answer: {answer3[:200]}...")

# Query 4: Continue again (should show COMPLETION)
print(f"\n4. User: tiếp tục (should show COMPLETION)")
print("-" * 80)
r4 = chatbot.chat("tiếp tục")
answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

print(f"\nFull Answer 4:")
print("=" * 80)
print(answer4)
print("=" * 80)

# Check for completion
has_completion = (
    ("hotline" in answer4.lower() and "1900" in answer4) or
    ("hoàn thành" in answer4.lower() and "✅" in answer4)
)

if has_completion:
    print(f"\n✅ SUCCESS: Shows completion message")
else:
    print(f"\n❌ FAIL: No completion message")
    print(f"\nGot: {answer4[:300]}...")
