# -*- coding: utf-8 -*-
"""
Debug what prompt LLM sees for completion message
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

chatbot = GraphRAGChatbot()

# Initial query
r1 = chatbot.chat("Làm sao mua vé máy bay trên VNPT Money?")

# Complete 2 steps
r2 = chatbot.chat("Tôi đã làm xong 2 bước đầu")

# Continue (show step 3)
r3 = chatbot.chat("tiếp tục")

# Continue again (should show completion)
# Patch the _build_prompt to print the prompt
original_build_prompt = chatbot._build_prompt

def debug_build_prompt(user_message, rag_result, continuation_context=None):
    prompt = original_build_prompt(user_message, rag_result, continuation_context)
    print("\n" + "=" * 80)
    print("LLM PROMPT:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    return prompt

chatbot._build_prompt = debug_build_prompt

r4 = chatbot.chat("tiếp tục")
print(f"\nFinal answer:\n{r4}")
