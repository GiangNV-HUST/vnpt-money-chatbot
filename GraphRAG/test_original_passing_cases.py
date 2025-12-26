# -*- coding: utf-8 -*-
"""
Test lại các cases đã PASS từ trước để đảm bảo fix không làm hỏng
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
    r1 = chatbot.chat(question)

    # Query 2: Complete N-1 steps
    print(f"2. User: Tôi đã làm xong {completed_steps} bước đầu")
    r2 = chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")

    # Query 3: Continue
    print(f"3. User: tiếp tục")
    r3 = chatbot.chat("tiếp tục")

    # Query 4: Continue again (should show COMPLETION)
    print(f"4. User: tiếp tục (expect COMPLETION)")
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    # Check for completion
    has_completion = (
        ("hotline" in answer4.lower() and "1900" in answer4) or
        ("hoàn thành" in answer4.lower() and "✅" in answer4)
    )

    status = "✅ PASS" if has_completion else "❌ FAIL"
    print(f"Result: {status}")
    return has_completion

print("=" * 80)
print("RE-TESTING ORIGINALLY PASSING CASES")
print("=" * 80)

# Test lại 10 cases đã PASS từ comprehensive test
results = {}

results["Chuyển tiền đến ngân hàng"] = test_case(
    "Chuyển tiền đến ngân hàng (9 bước)",
    "Làm sao chuyển tiền từ VNPT Money đến ngân hàng?",
    8, 9
)

results["Nạp tiền từ ngân hàng"] = test_case(
    "Nạp tiền từ ngân hàng (5 bước)",
    "Tôi muốn nạp tiền từ ngân hàng vào VNPT Money",
    4, 5
)

results["Rút tiền về ngân hàng"] = test_case(
    "Rút tiền về ngân hàng (5 bước)",
    "Làm sao rút tiền về ngân hàng từ VNPT Money?",
    4, 5
)

results["Nạp tiền điện thoại"] = test_case(
    "Nạp tiền điện thoại (4 bước)",
    "Tôi muốn nạp tiền điện thoại qua VNPT Money",
    3, 4
)

results["Mua vé tàu"] = test_case(
    "Mua vé tàu (3 bước)",
    "Làm sao mua vé tàu trên VNPT Money?",
    2, 3
)

print(f"\n{'=' * 80}")
print("SUMMARY - REGRESSION TEST")
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
    print(f"\n🎉 NO REGRESSION - All originally passing cases still pass!")
else:
    print(f"\n⚠️ REGRESSION DETECTED - {total - passed} previously passing test(s) now fail")
