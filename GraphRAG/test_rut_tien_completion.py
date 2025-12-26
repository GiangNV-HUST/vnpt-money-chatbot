"""
Test completion step detection for "Rút tiền" flow
"""
# -*- coding: utf-8 -*-

import sys
import io
from conversation_context_manager import ConversationContextManager

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_rut_tien():
    """Test rút tiền flow with completion step"""
    manager = ConversationContextManager()

    # Actual "Rút tiền" answer with 5 steps
    first_answer = """Để rút tiền từ ví VNPT Pay về tài khoản ngân hàng:

Bước 1: Tại giao diện chính, chọn mục "Rút tiền".
Bước 2: Nhập số tiền cần rút và nhấn "Tiếp tục".
Bước 3: Màn hình Xác nhận giao dịch và nhấn "Rút tiền".
Bước 4: Màn hình nhập OTP để xác thực giao dịch.
Bước 5: Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận."""

    first_response = {
        "answer": first_answer,
        "all_results": [{"question_id": "FAQ_RUT_TIEN"}],
        "related_entities": {"topics": ["rút tiền"]}
    }

    manager.add_turn("Làm sao rút tiền?", first_response)

    print("=" * 80)
    print("TEST: Rút tiền flow - Check completion step detection")
    print("=" * 80)

    all_steps = manager.current_context.get("all_steps", [])
    print(f"Total steps: {len(all_steps)}\n")

    for step in all_steps:
        is_completion = step.get("is_completion_step", False)
        status = "COMPLETION" if is_completion else "ACTION"
        print(f"Step {step['step_number']}: [{status}] {step['step_title']}")

    # Check step 5
    step_5 = [s for s in all_steps if s["step_number"] == 5]
    if step_5:
        if step_5[0].get("is_completion_step", False):
            print("\n✅ PASS: Step 5 correctly marked as COMPLETION")
            print(f"   Text: {step_5[0]['step_title']}")
        else:
            print("\n❌ FAIL: Step 5 should be COMPLETION but marked as ACTION")
            print(f"   Text: {step_5[0]['step_title']}")

    # Simulate user completing first 4 steps
    print("\n" + "=" * 80)
    print("User completes 4 steps and says 'tiếp tục'")
    print("=" * 80)

    # Simulate bot showed step 4
    second_response = {
        "answer": "Bước 4: Màn hình nhập OTP để xác thực giao dịch.",
        "is_continuation": True,
        "next_steps": [{"number": 4, "text": "Màn hình nhập OTP"}],
        "all_results": [{"question_id": "FAQ_RUT_TIEN"}],
        "related_entities": {"topics": ["rút tiền"]}
    }
    manager.add_turn("4 bước đầu", second_response)

    # Now user says "tiếp tục"
    query = "tiếp tục"
    continuation_context = manager.get_continuation_context(query)

    if continuation_context:
        print(f"Completed step: {continuation_context.get('completed_step')}")
        print(f"Next step: {continuation_context.get('next_step')}")
        print(f"All steps completed: {continuation_context.get('all_steps_completed', False)}")

        if continuation_context.get('all_steps_completed', False):
            print("\n✅ PASS: System recognizes step 5 is completion")
            print("   Bot will show completion message")
        else:
            print("\n❌ FAIL: System should recognize step 5 is completion")
            print(f"   Bot will show step {continuation_context.get('next_step')}")

    print("=" * 80)

if __name__ == "__main__":
    test_rut_tien()
