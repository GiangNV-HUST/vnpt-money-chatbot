# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

from chatbot import GraphRAGChatbot

chatbot = GraphRAGChatbot()

print("=" * 80)
print("Q1: Làm sao rút tiền?")
print("=" * 80)
r1 = chatbot.chat("Làm sao rút tiền từ ví VNPT Pay về ngân hàng?")
print()

print("=" * 80)
print("Q2: 4 bước đầu")
print("=" * 80)
r2 = chatbot.chat("Tôi đã làm xong 4 bước đầu")
print(f"\nResponse type: {type(r2)}")
if isinstance(r2, dict):
    print(f"is_continuation: {r2.get('is_continuation')}")
    print(f"next_steps: {r2.get('next_steps')}")
print()
