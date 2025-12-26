# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from conversation_context_manager import ConversationContextManager

manager = ConversationContextManager()

step3_text = 'Màn hình Xác nhận giao dịch và nhấn "Rút tiền".'
print(f"Testing: {step3_text}")
print(f"Lower: {step3_text.lower()}")

result = manager._is_final_completion_step(step3_text)
print(f"\nResult: {result}")
print(f"Expected: False (because it has action verb 'nhấn')")

if result == False:
    print("\n✅ CORRECT")
else:
    print("\n❌ WRONG - should be False")
