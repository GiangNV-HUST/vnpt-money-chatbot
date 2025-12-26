# -*- coding: utf-8 -*-
"""
Test the 2 previously failed cases with improved fallback
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_case(name, question, completed_steps, total_steps):
    """Test a single case"""
    print(f"\n{'=' * 80}")
    print(f"TEST: {name}")
    print(f"{'=' * 80}")

    chatbot = GraphRAGChatbot()

    # Query 1: Initial
    print(f"\n1. User: {question}")
    print("-" * 80)
    r1 = chatbot.chat(question)
    print(f"✅ Got initial response")

    # Query 2: Complete N-1 steps
    print(f"\n2. User: Tôi đã làm xong {completed_steps} bước đầu")
    print("-" * 80)
    r2 = chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")

    # Query 3: Continue (should show next step)
    print(f"\n3. User: tiếp tục (should show step {completed_steps + 1})")
    print("-" * 80)
    r3 = chatbot.chat("tiếp tục")

    # Query 4: Continue again (should show COMPLETION)
    print(f"\n4. User: tiếp tục (should show COMPLETION)")
    print("-" * 80)
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    # Check for completion
    has_completion = (
        ("hotline" in answer4.lower() and "1900" in answer4) or
        ("hoàn thành" in answer4.lower() and "✅" in answer4)
    )

    print(f"\nAnswer preview: {answer4[:200]}...")

    if has_completion:
        print(f"\n✅ SUCCESS: Shows completion message")
        return True
    else:
        print(f"\n❌ FAIL: No completion message")
        return False

print("=" * 80)
print("TESTING PREVIOUSLY FAILED CASES")
print("=" * 80)

# Test Case 1: Hủy nạp tiền tự động
result1 = test_case(
    "Hủy nạp tiền tự động (6 bước)",
    "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?",
    5,
    6
)

# Test Case 2: Mua vé máy bay
result2 = test_case(
    "Mua vé máy bay (3 bước)",
    "Làm sao mua vé máy bay trên VNPT Money?",
    2,
    3
)

print(f"\n{'=' * 80}")
print("SUMMARY")
print(f"{'=' * 80}")
print(f"1. Hủy nạp tiền tự động: {'✅ PASS' if result1 else '❌ FAIL'}")
print(f"2. Mua vé máy bay: {'✅ PASS' if result2 else '❌ FAIL'}")

if result1 and result2:
    print(f"\n🎉 BOTH TESTS PASSED!")
else:
    print(f"\n⚠️ Some tests still failing")
