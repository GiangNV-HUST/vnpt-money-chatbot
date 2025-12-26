# -*- coding: utf-8 -*-
"""
Test thêm các câu có step khác để đảm bảo entity extraction fix hoạt động tốt
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_case(name, question, completed_steps, total_steps):
    """Test a single case"""
    print(f"\n{'=' * 80}")
    print(f"TEST: {name} ({total_steps} bước)")
    print(f"{'=' * 80}")

    chatbot = GraphRAGChatbot()

    # Query 1: Initial
    print(f"\n1. User: {question}")
    print("-" * 80)
    r1 = chatbot.chat(question)
    answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))

    # Count steps
    step_count = answer1.count("Bước")
    print(f"📝 Answer shows {step_count} steps")
    print(f"Preview: {answer1[:150]}...")

    # Check context
    all_steps = chatbot.context_manager.current_context.get('all_steps', [])
    topic = chatbot.context_manager.current_context.get('topic')
    faq_id = chatbot.context_manager.current_context.get('last_faq_id')

    print(f"\n📊 Context: {len(all_steps)} steps tracked, Topic: '{topic}', FAQ: {faq_id}")

    # Query 2: Complete N-1 steps
    print(f"\n2. User: Tôi đã làm xong {completed_steps} bước đầu")
    print("-" * 80)
    r2 = chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")
    answer2 = r2 if isinstance(r2, str) else r2.get('answer', str(r2))
    print(f"Response: {answer2[:100]}...")

    # Query 3: Continue (should show next step)
    print(f"\n3. User: tiếp tục (expect step {completed_steps + 1})")
    print("-" * 80)
    r3 = chatbot.chat("tiếp tục")
    answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))

    if f"Bước {completed_steps + 1}" in answer3 or f"bước {completed_steps + 1}" in answer3.lower():
        print(f"✅ Shows step {completed_steps + 1}")
    else:
        print(f"⚠️ Expected step {completed_steps + 1}, got: {answer3[:100]}...")

    # Query 4: Continue again (should show COMPLETION)
    print(f"\n4. User: tiếp tục (expect COMPLETION)")
    print("-" * 80)
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    # Check for completion
    has_completion = (
        ("hotline" in answer4.lower() and "1900" in answer4) or
        ("hoàn thành" in answer4.lower() and "✅" in answer4)
    )

    if has_completion:
        print(f"✅ SUCCESS: Shows completion message")
        print(f"Preview: {answer4[:150]}...")
        return True
    else:
        print(f"❌ FAIL: No completion message")
        print(f"Got: {answer4[:200]}...")
        return False

print("=" * 80)
print("TESTING ADDITIONAL STEP-BASED PROCESSES")
print("=" * 80)

results = {}

# Test các loại giao dịch khác nhau

# 1. Thanh toán các loại hóa đơn
print("\n" + "=" * 80)
print("CATEGORY: THANH TOÁN HÓA ĐƠN")
print("=" * 80)

results["Thanh toán hóa đơn điện"] = test_case(
    "Thanh toán hóa đơn điện",
    "Tôi muốn thanh toán hóa đơn tiền điện qua VNPT Money",
    4, 5
)

results["Thanh toán hóa đơn nước"] = test_case(
    "Thanh toán hóa đơn nước",
    "Làm sao thanh toán tiền nước trên app VNPT Money?",
    4, 5
)

results["Thanh toán hóa đơn internet"] = test_case(
    "Thanh toán hóa đơn internet",
    "Tôi muốn thanh toán cước internet VNPT qua VNPT Money",
    5, 6
)

# 2. Các loại nạp tiền khác
print("\n" + "=" * 80)
print("CATEGORY: NẠP TIỀN")
print("=" * 80)

results["Nạp tiền game"] = test_case(
    "Nạp tiền game",
    "Làm sao nạp tiền vào game qua VNPT Money?",
    3, 4
)

results["Nạp tiền ví điện tử"] = test_case(
    "Nạp tiền ví điện tử",
    "Tôi muốn nạp tiền vào ví MoMo từ VNPT Money",
    4, 5
)

# 3. Đăng ký dịch vụ
print("\n" + "=" * 80)
print("CATEGORY: ĐĂNG KÝ DỊCH VỤ")
print("=" * 80)

results["Đăng ký rút tiền tự động"] = test_case(
    "Đăng ký rút tiền tự động",
    "Tôi muốn đăng ký dịch vụ rút tiền tự động",
    4, 5
)

results["Đăng ký SMS Banking"] = test_case(
    "Đăng ký SMS Banking",
    "Làm sao đăng ký SMS Banking trên VNPT Money?",
    3, 4
)

# 4. Kiểm tra và tra cứu
print("\n" + "=" * 80)
print("CATEGORY: KIỂM TRA & TRA CỨU")
print("=" * 80)

results["Kiểm tra lịch sử giao dịch"] = test_case(
    "Kiểm tra lịch sử giao dịch",
    "Tôi muốn xem lịch sử giao dịch của mình",
    1, 2
)

results["Tra cứu mã giao dịch"] = test_case(
    "Tra cứu mã giao dịch",
    "Làm sao tra cứu thông tin giao dịch bằng mã GD?",
    2, 3
)

# 5. Quản lý tài khoản
print("\n" + "=" * 80)
print("CATEGORY: QUẢN LÝ TÀI KHOẢN")
print("=" * 80)

results["Cập nhật thông tin cá nhân"] = test_case(
    "Cập nhật thông tin cá nhân",
    "Tôi muốn cập nhật thông tin cá nhân trên VNPT Money",
    3, 4
)

results["Đổi số điện thoại"] = test_case(
    "Đổi số điện thoại",
    "Làm sao đổi số điện thoại đăng ký tài khoản?",
    4, 5
)

# Summary
print(f"\n{'=' * 80}")
print("DETAILED SUMMARY BY CATEGORY")
print(f"{'=' * 80}")

categories = {
    "Thanh toán hóa đơn": [
        "Thanh toán hóa đơn điện",
        "Thanh toán hóa đơn nước",
        "Thanh toán hóa đơn internet"
    ],
    "Nạp tiền": [
        "Nạp tiền game",
        "Nạp tiền ví điện tử"
    ],
    "Đăng ký dịch vụ": [
        "Đăng ký rút tiền tự động",
        "Đăng ký SMS Banking"
    ],
    "Kiểm tra & Tra cứu": [
        "Kiểm tra lịch sử giao dịch",
        "Tra cứu mã giao dịch"
    ],
    "Quản lý tài khoản": [
        "Cập nhật thông tin cá nhân",
        "Đổi số điện thoại"
    ]
}

for category, test_names in categories.items():
    passed = sum(1 for name in test_names if results.get(name, False))
    total = len(test_names)
    rate = passed / total * 100 if total > 0 else 0

    status = "✅" if rate == 100 else "⚠️" if rate >= 50 else "❌"
    print(f"\n{status} {category}: {passed}/{total} ({rate:.0f}%)")

    for name in test_names:
        result = results.get(name, False)
        symbol = "  ✅" if result else "  ❌"
        print(f"{symbol} {name}")

# Overall summary
print(f"\n{'=' * 80}")
print("OVERALL SUMMARY")
print(f"{'=' * 80}")

passed = sum(1 for v in results.values() if v)
total = len(results)
rate = passed / total * 100

print(f"\nTotal: {passed}/{total} tests passed ({rate:.0f}%)")

if rate >= 90:
    print("🎉 EXCELLENT - System performs very well across diverse processes!")
elif rate >= 75:
    print("✅ GOOD - System works well for most process types")
elif rate >= 50:
    print("⚠️ FAIR - Some process types need improvement")
else:
    print("❌ NEEDS WORK - Significant issues across multiple process types")

print(f"\n{'=' * 80}")
