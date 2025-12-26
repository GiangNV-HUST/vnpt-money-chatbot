# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

from chatbot import GraphRAGChatbot

chatbot = GraphRAGChatbot()

print("=" * 80)
print("TEST: Nạp tiền - Debug completion")
print("=" * 80)

print("\n1. User: Làm sao nạp tiền từ ngân hàng vào VNPT Money?")
r1 = chatbot.chat("Làm sao nạp tiền từ ngân hàng vào VNPT Money?")

print("\n2. User: Tôi đã làm xong 4 bước đầu")
r2 = chatbot.chat("Tôi đã làm xong 4 bước đầu")

print("\n3. User: tiếp tục (lần 1 - should show step 5)")
r3 = chatbot.chat("tiếp tục")
answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))
print(f"\nAnswer: {answer3[:250]}")

print("\n4. User: tiếp tục (lần 2 - should show COMPLETION)")
r4 = chatbot.chat("tiếp tục")
answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))
print(f"\nAnswer: {answer4[:250]}")

if 'hotline' in answer4.lower() or 'hoàn thành' in answer4.lower():
    print('\n✅ HAS COMPLETION MESSAGE')
else:
    print('\n❌ NO COMPLETION MESSAGE')
