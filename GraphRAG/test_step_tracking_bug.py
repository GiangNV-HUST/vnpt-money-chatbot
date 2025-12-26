"""
Test script to reproduce the step tracking bug
where "tiep tuc" after showing Step 7 incorrectly jumps to contact info
"""
# -*- coding: utf-8 -*-

import sys
import io
from conversation_context_manager import ConversationContextManager

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_step_tracking():
    """Test that step tracking correctly handles continuation"""
    manager = ConversationContextManager()

    # Simulate first query
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
        "related_entities": {"topics": ["chuyen tien"]}
    }

    # Add first turn
    manager.add_turn("How to transfer money from VNPT Money to bank?", first_response)

    print("=" * 60)
    print("AFTER FIRST QUERY:")
    print(f"Current step tracked: {manager.current_context.get('current_step')}")
    print(f"Total steps extracted: {len(manager.current_context.get('all_steps', []))}")
    print(f"Last FAQ ID: {manager.current_context.get('last_faq_id')}")
    if manager.current_context.get('current_step') is None:
        print("GOOD: current_step is None (user hasn't completed any steps yet)")
    else:
        print(f"BAD: current_step should be None, not {manager.current_context.get('current_step')}")
    print()

    # Simulate second query (using Vietnamese pattern that the system recognizes)
    query2 = "6 buoc dau"  # Simpler pattern
    continuation_context = manager.get_continuation_context(query2)

    print("=" * 60)
    print("AFTER USER SAYS 'completed 6 steps':")
    print(f"Continuation context detected: {continuation_context is not None}")
    if continuation_context:
        print(f"Completed step: {continuation_context.get('completed_step')}")
        print(f"Next step to show: {continuation_context.get('next_step')}")
        print(f"Topic: {continuation_context.get('topic')}")
        print(f"Last FAQ ID: {continuation_context.get('last_faq_id')}")
    print()

    # Simulate bot response showing Step 7
    second_answer = "Next step:\n\nBước 7: Xác nhận giao dịch và ấn 'Chuyển tiền'"
    second_response = {
        "answer": second_answer,
        "is_continuation": True,
        "next_steps": [{"number": 7, "text": "Xác nhận giao dịch"}],
        "all_results": [{"question_id": "FAQ_123"}],
        "related_entities": continuation_context.get("entities", {}) if continuation_context else {}
    }

    # Add second turn
    manager.add_turn(query2, second_response)

    print("=" * 60)
    print("AFTER BOT SHOWS STEP 7:")
    print(f"Current step tracked: {manager.current_context.get('current_step')}")
    if manager.current_context.get('current_step') == 7:
        print("GOOD: current_step is 7 (we just showed Step 7)")
    else:
        print(f"BAD: current_step should be 7, not {manager.current_context.get('current_step')}")
    print()

    # Simulate third query (using Vietnamese "tiep tuc")
    query3 = "tiep tuc"
    continuation_context3 = manager.get_continuation_context(query3)

    print("=" * 60)
    print("AFTER USER SAYS 'continue':")
    print(f"Continuation context detected: {continuation_context3 is not None}")
    if continuation_context3:
        print(f"Completed step: {continuation_context3.get('completed_step')}")
        print(f"Next step to show: {continuation_context3.get('next_step')}")
        print()

        # Check if the next step is correct
        if continuation_context3.get('next_step') == 8:
            print("PASS: Will show Step 8 (Nhap OTP)")
        else:
            print(f"FAIL: Will show Step {continuation_context3.get('next_step')} instead of Step 8")

    print("=" * 60)

if __name__ == "__main__":
    test_step_tracking()
