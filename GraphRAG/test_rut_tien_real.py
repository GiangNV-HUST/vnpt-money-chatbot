# -*- coding: utf-8 -*-
"""
Test real chatbot flow: Rút tiền (5 steps) with completion detection
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_rut_tien_completion():
    """Test rút tiền flow with completion message"""
    print("=" * 80)
    print("TEST: Rút tiền flow - Check completion detection works")
    print("=" * 80)

    chatbot = GraphRAGChatbot()

    # Query 1: Initial question
    print("\n1. User: Làm sao rút tiền từ ví VNPT Pay về ngân hàng?")
    print("-" * 80)
    response1 = chatbot.chat("Làm sao rút tiền từ ví VNPT Pay về ngân hàng?")
    answer1 = response1 if isinstance(response1, str) else response1.get('answer', str(response1))
    print(answer1)
    print()

    # Query 2: User completed 4 steps
    print("\n2. User: Tôi đã làm xong 4 bước đầu")
    print("-" * 80)
    response2 = chatbot.chat("Tôi đã làm xong 4 bước đầu")
    answer2 = response2 if isinstance(response2, str) else response2.get('answer', str(response2))
    print(answer2)
    print()

    # Query 3: User says "tiếp tục" → should show step 5
    print("\n3. User: tiếp tục")
    print("-" * 80)
    response3 = chatbot.chat("tiếp tục")
    answer3 = response3 if isinstance(response3, str) else response3.get('answer', str(response3))
    print(answer3)
    print()

    # Query 4: User says "tiếp tục" again → should show COMPLETION MESSAGE
    print("\n4. User: tiếp tục (again)")
    print("-" * 80)
    response4 = chatbot.chat("tiếp tục")
    answer4 = response4 if isinstance(response4, str) else response4.get('answer', str(response4))
    print(answer4)
    print()

    # Check if completion message was shown
    if "tất cả các bước đã hoàn thành" in answer4.lower():
        print("✅ SUCCESS: Completion message was shown!")
    elif "hotline" in answer4.lower() and "1900" in answer4:
        print("✅ SUCCESS: Contact info shown (completion detected)!")
    else:
        print("❌ FAIL: Completion message NOT shown")
        print(f"   Instead got: {answer4[:100]}...")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_rut_tien_completion()
