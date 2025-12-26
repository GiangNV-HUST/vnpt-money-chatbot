# -*- coding: utf-8 -*-
"""
Debug test for Mua vé máy bay process
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

print("=" * 80)
print("TEST: Mua vé máy bay (3 bước)")
print("=" * 80)

chatbot = GraphRAGChatbot()

# Query 1
print("\n1. User: Làm sao mua vé máy bay trên VNPT Money?")
print("-" * 80)
r1 = chatbot.chat("Làm sao mua vé máy bay trên VNPT Money?")
answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))
print(answer1[:300] + "...")
print()

# Query 2: Complete 2 steps
print("\n2. User: Tôi đã làm xong 2 bước đầu")
print("-" * 80)
r2 = chatbot.chat("Tôi đã làm xong 2 bước đầu")
answer2 = r2 if isinstance(r2, str) else r2.get('answer', str(r2))
print(answer2)
print()

# Query 3: Continue → should show step 3
print("\n3. User: tiếp tục (lần 1 - should show step 3)")
print("-" * 80)
r3 = chatbot.chat("tiếp tục")
answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))
print(answer3)

if "bước 3" in answer3.lower() or "bước tiếp theo" in answer3.lower():
    print("✅ Showing step 3")
else:
    print("⚠️ Not clear which step")
print()

# Query 4: Continue → should show completion
print("\n4. User: tiếp tục (lần 2 - should show COMPLETION)")
print("-" * 80)
r4 = chatbot.chat("tiếp tục")
answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))
print(f"\nAnswer: {answer4}")

if "hotline" in answer4.lower() and "1900" in answer4:
    print("\n✅ HAS COMPLETION MESSAGE")
elif "hoàn thành" in answer4.lower():
    print("\n✅ HAS COMPLETION MESSAGE")
else:
    print("\n❌ NO COMPLETION MESSAGE")
    print(f"   Got: {answer4[:150]}...")

print("\n" + "=" * 80)
