"""
Test script to verify completion step detection
Ensures that "Bước 9: Màn hình xác nhận giao dịch thành công" is treated as completion, not action
"""
# -*- coding: utf-8 -*-

import sys
import io
from conversation_context_manager import ConversationContextManager

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_completion_step_detection():
    """Test that completion steps are correctly identified"""
    manager = ConversationContextManager()

    # Simulate first query with 9 steps (step 9 is completion)
    first_answer = """Để chuyển tiền từ VNPT Money đến ngân hàng:

Bước 1: Tại giao diện chính, chọn mục "Chuyển tiền".
Bước 2: Chọn chuyển "Đến ngân hàng".
Bước 3: Chọn "Qua số tài khoản/số thẻ".
Bước 4: Chọn ngân hàng cần chuyển.
Bước 5: Nhập số tài khoản/số thẻ và ấn Kiểm tra.
Bước 6: Nhập số tiền cần chuyển, nội dung chuyển tiền và ấn 'Tiếp tục'.
Bước 7: Xác nhận giao dịch và ấn "Chuyển tiền".
Bước 8: Nhập OTP.
Bước 9: Màn hình xác nhận giao dịch Chuyển tiền thành công."""

    first_response = {
        "answer": first_answer,
        "all_results": [{"question_id": "FAQ_123"}],
        "related_entities": {"topics": ["chuyển tiền"]}
    }

    # Add first turn
    manager.add_turn("Làm sao chuyển tiền từ VNPT Money đến ngân hàng?", first_response)

    print("=" * 80)
    print("TEST 1: Check step extraction and completion detection")
    print("=" * 80)

    all_steps = manager.current_context.get("all_steps", [])
    print(f"Total steps extracted: {len(all_steps)}")

    for step in all_steps:
        is_completion = step.get("is_completion_step", False)
        status = "COMPLETION" if is_completion else "ACTION"
        print(f"  Step {step['step_number']}: [{status}] {step['step_title'][:60]}")

    # Check if step 9 is marked as completion
    step_9 = [s for s in all_steps if s["step_number"] == 9]
    if step_9 and step_9[0].get("is_completion_step", False):
        print("\n✅ PASS: Step 9 correctly marked as COMPLETION step")
    else:
        print("\n❌ FAIL: Step 9 should be marked as COMPLETION step")

    print()

    # Simulate user completing first 7 steps
    print("=" * 80)
    print("TEST 2: User says 'I completed 7 steps'")
    print("=" * 80)

    query2 = "tôi đã làm xong 7 bước đầu"
    continuation_context = manager.get_continuation_context(query2)

    if continuation_context:
        print(f"Completed step: {continuation_context.get('completed_step')}")
        print(f"Next step to show: {continuation_context.get('next_step')}")

        if continuation_context.get('next_step') == 8:
            print("✅ PASS: Will show Step 8 (Nhập OTP)")
        else:
            print(f"❌ FAIL: Should show Step 8, but will show Step {continuation_context.get('next_step')}")

    # Simulate bot showing step 8
    second_answer = "Bước tiếp theo:\n\nBước 8: Nhập OTP"
    second_response = {
        "answer": second_answer,
        "is_continuation": True,
        "next_steps": [{"number": 8, "text": "Nhập OTP"}],
        "all_results": [{"question_id": "FAQ_123"}],
        "related_entities": continuation_context.get("entities", {}) if continuation_context else {}
    }

    manager.add_turn(query2, second_response)
    print()

    # Simulate user saying "continue" after step 8
    print("=" * 80)
    print("TEST 3: User says 'continue' after Step 8")
    print("=" * 80)

    query3 = "tiếp tục"
    continuation_context3 = manager.get_continuation_context(query3)

    if continuation_context3:
        print(f"Completed step: {continuation_context3.get('completed_step')}")
        print(f"Next step: {continuation_context3.get('next_step')}")
        print(f"All steps completed flag: {continuation_context3.get('all_steps_completed', False)}")

        if continuation_context3.get('all_steps_completed', False):
            print("\n✅ PASS: System recognizes Step 9 is completion, no more action steps")
            print("   Bot should show completion message instead of Step 9")
        else:
            print(f"\n❌ FAIL: System should recognize Step 9 is completion")
            print(f"   Instead, it will try to show Step {continuation_context3.get('next_step')}")

    print("=" * 80)

if __name__ == "__main__":
    test_completion_step_detection()
