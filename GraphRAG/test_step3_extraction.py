# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from conversation_context_manager import ConversationContextManager

manager = ConversationContextManager()

answer = """Bước 3: Màn hình Xác nhận giao dịch và nhấn "Rút tiền"."""

steps = manager._extract_steps_from_answer(answer)

print(f"Extracted {len(steps)} steps")
for step in steps:
    print(f"\nStep {step['step_number']}:")
    print(f"  Title: {step['step_title']}")
    print(f"  Full text: {step['step_text']}")
    print(f"  Is completion: {step.get('is_completion_step', False)}")
