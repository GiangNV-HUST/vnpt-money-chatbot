# -*- coding: utf-8 -*-
"""
Test thêm các trường hợp khác để đảm bảo entity extraction fix không làm hỏng các case khác
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
    answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))
    print(f"✅ Got initial response (preview): {answer1[:150]}...")

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

    if has_completion:
        print(f"\n✅ SUCCESS: Shows completion message")
        return True
    else:
        print(f"\n❌ FAIL: No completion message")
        print(f"Got: {answer4[:200]}...")
        return False

print("=" * 80)
print("TESTING MORE EDGE CASES")
print("=" * 80)

results = {}

# Test 1: Liên kết ngân hàng (should have "liên kết" not just generic topic)
results["Liên kết ngân hàng"] = test_case(
    "Liên kết ngân hàng (5 bước)",
    "Tôi muốn liên kết ngân hàng với VNPT Money",
    4,
    5
)

# Test 2: Đổi mật khẩu (generic vs specific)
results["Đổi mật khẩu"] = test_case(
    "Đổi mật khẩu (4 bước)",
    "Làm sao để đổi mật khẩu trên VNPT Money?",
    3,
    4
)

# Test 3: Kiểm tra số dư (short process)
results["Kiểm tra số dư"] = test_case(
    "Kiểm tra số dư (2 bước)",
    "Tôi muốn kiểm tra số dư trong ví",
    1,
    2
)

# Test 4: Mua thẻ cào (should distinguish from other "mua" actions)
results["Mua thẻ cào"] = test_case(
    "Mua thẻ cào điện thoại (4 bước)",
    "Làm sao mua thẻ cào điện thoại trên app?",
    3,
    4
)

# Test 5: Rút tiền về thẻ (specific withdrawal type)
results["Rút tiền về thẻ"] = test_case(
    "Rút tiền về thẻ ATM (5 bước)",
    "Tôi muốn rút tiền về thẻ ATM",
    4,
    5
)

print(f"\n{'=' * 80}")
print("SUMMARY - MORE EDGE CASES")
print(f"{'=' * 80}")

passed = sum(1 for v in results.values() if v)
total = len(results)

for name, result in results.items():
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{name}: {status}")

print(f"\n{'=' * 80}")
print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
print(f"{'=' * 80}")

if passed == total:
    print(f"\n🎉 ALL EDGE CASE TESTS PASSED!")
else:
    print(f"\n⚠️ {total - passed} test(s) failed")
