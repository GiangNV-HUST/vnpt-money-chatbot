# -*- coding: utf-8 -*-
"""
Test completion detection với flow Chuyển tiền (9 bước)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

print("=" * 80)
print("TEST: Chuyển tiền flow (9 bước) - Completion detection")
print("=" * 80)

chatbot = GraphRAGChatbot()

# Query 1
print("\n1. User: Làm sao chuyển tiền từ VNPT Money đến ngân hàng?")
print("-" * 80)
r1 = chatbot.chat("Làm sao chuyển tiền từ VNPT Money đến ngân hàng?")
answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))
print(answer1[:300] + "...")
print()

# Query 2: Complete 8 steps
print("\n2. User: Tôi đã làm xong 8 bước đầu")
print("-" * 80)
r2 = chatbot.chat("Tôi đã làm xong 8 bước đầu")
answer2 = r2 if isinstance(r2, str) else r2.get('answer', str(r2))
print(answer2)
print()

# Query 3: Continue → should show step 9
print("\n3. User: tiếp tục")
print("-" * 80)
r3 = chatbot.chat("tiếp tục")
answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))
print(answer3)

if "bước 9" in answer3.lower() or "bước tiếp theo" in answer3.lower():
    print("✅ Showing step 9")
else:
    print("❌ Not showing step 9")
print()

# Query 4: Continue → should show completion
print("\n4. User: tiếp tục (should show completion)")
print("-" * 80)
r4 = chatbot.chat("tiếp tục")
answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))
print(answer4)

if "hotline" in answer4.lower() and "1900" in answer4:
    print("\n✅ SUCCESS: Completion detected (has hotline)!")
elif "hoàn thành" in answer4.lower():
    print("\n✅ SUCCESS: Completion message shown!")
else:
    print("\n❌ FAIL: Completion not detected")
    print(f"   Got: {answer4[:100]}...")

print("\n" + "=" * 80)
