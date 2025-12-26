# -*- coding: utf-8 -*-
"""
Debug script to identify why graph-based completion detection isn't working
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_graph_query():
    """Test if graph query returns total_steps_in_process"""
    print("=" * 80)
    print("TEST 1: Check if graph query returns total_steps_in_process")
    print("=" * 80)

    engine = Neo4jGraphRAGEngine()

    # Test with "Rút tiền" FAQ
    faq_id = "FAQ_RUT_TIEN"

    # Query step 1 (should exist)
    print(f"\n1. Query step 1 for {faq_id}:")
    result = engine._query_steps_by_faq_id(faq_id, from_step=1, only_next_step=True)
    if result:
        print(f"   ✅ Found step 1")
        print(f"   Total steps: {result.get('total_steps', 0)}")
        print(f"   Total steps in process: {result.get('total_steps_in_process', 'NOT FOUND')}")
    else:
        print(f"   ❌ No result returned")

    # Query step 5 (should exist)
    print(f"\n2. Query step 5 for {faq_id}:")
    result = engine._query_steps_by_faq_id(faq_id, from_step=5, only_next_step=True)
    if result:
        print(f"   ✅ Found step 5")
        print(f"   Total steps: {result.get('total_steps', 0)}")
        print(f"   Total steps in process: {result.get('total_steps_in_process', 'NOT FOUND')}")
        if result.get('steps'):
            print(f"   Step text: {result['steps'][0].get('step_text', '')[:100]}...")
    else:
        print(f"   ❌ No result returned")

    # Query step 6 (should NOT exist if process only has 5 steps)
    print(f"\n3. Query step 6 for {faq_id} (should not exist):")
    result = engine._query_steps_by_faq_id(faq_id, from_step=6, only_next_step=True)
    if result:
        total_in_process = result.get('total_steps_in_process', 0)
        found_steps = result.get('total_steps', 0)
        print(f"   Total steps found: {found_steps}")
        print(f"   Total steps in process: {total_in_process}")

        if found_steps == 0 and total_in_process > 0:
            print(f"   ✅ CORRECT: No step 6, but process has {total_in_process} steps total")
            print(f"   This should trigger completion message!")
        elif found_steps > 0:
            print(f"   ❌ WRONG: Step 6 exists (process may have more than 5 steps)")
        else:
            print(f"   ❌ WRONG: No total_steps_in_process returned")
    else:
        print(f"   ❌ No result returned (should still return total_steps_in_process)")

    engine.close()

def test_continuation_logic():
    """Test continuation context detection"""
    print("\n" + "=" * 80)
    print("TEST 2: Check continuation context logic")
    print("=" * 80)

    manager = ConversationContextManager()

    # Simulate "Rút tiền" initial answer
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

    print(f"\n1. After initial answer:")
    print(f"   Current step: {manager.current_context.get('current_step')}")
    print(f"   All steps count: {len(manager.current_context.get('all_steps', []))}")
    print(f"   Last FAQ ID: {manager.current_context.get('last_faq_id')}")

    # Simulate showing step 4
    second_response = {
        "answer": "Bước 4: Màn hình nhập OTP để xác thực giao dịch.",
        "is_continuation": True,
        "next_steps": [{"number": 4, "text": "Màn hình nhập OTP"}],
        "all_results": [{"question_id": "FAQ_RUT_TIEN"}],
        "related_entities": {"topics": ["rút tiền"]}
    }
    manager.add_turn("4 bước đầu", second_response)

    print(f"\n2. After showing step 4:")
    print(f"   Current step: {manager.current_context.get('current_step')}")
    print(f"   All steps count: {len(manager.current_context.get('all_steps', []))} (should still be 5)")
    print(f"   Last FAQ ID: {manager.current_context.get('last_faq_id')}")

    # Simulate showing step 5
    third_response = {
        "answer": "Bước 5: Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận.",
        "is_continuation": True,
        "next_steps": [{"number": 5, "text": "Giao dịch của bạn sẽ được xử lý"}],
        "all_results": [{"question_id": "FAQ_RUT_TIEN"}],
        "related_entities": {"topics": ["rút tiền"]}
    }
    manager.add_turn("tiếp tục", third_response)

    print(f"\n3. After showing step 5:")
    print(f"   Current step: {manager.current_context.get('current_step')}")
    print(f"   Last FAQ ID: {manager.current_context.get('last_faq_id')}")

    # Now user says "tiếp tục" again
    print(f"\n4. User says 'tiếp tục' again:")
    continuation_context = manager.get_continuation_context("tiếp tục")

    if continuation_context:
        print(f"   Completed step: {continuation_context.get('completed_step')}")
        print(f"   Next step: {continuation_context.get('next_step')}")
        print(f"   FAQ ID: {continuation_context.get('faq_id')}")
        print(f"   Topic: {continuation_context.get('topic')}")

        if continuation_context.get('completed_step') == 5:
            print(f"   ✅ Correctly detected step 5 completed")
        else:
            print(f"   ❌ Wrong completed_step")

        if continuation_context.get('next_step') == 6:
            print(f"   ✅ Next step should be 6 (which doesn't exist)")
        else:
            print(f"   ❌ Wrong next_step")
    else:
        print(f"   ❌ No continuation context detected!")

def test_end_to_end():
    """Test full end-to-end flow with RAG engine"""
    print("\n" + "=" * 80)
    print("TEST 3: End-to-end with RAG engine")
    print("=" * 80)

    engine = Neo4jGraphRAGEngine()

    # Simulate continuation query after step 5
    print("\nSimulating: User completed step 5, says 'tiếp tục'")

    continuation_context = {
        'completed_step': 5,
        'next_step': 6,
        'faq_id': 'FAQ_RUT_TIEN',
        'topic': 'rút tiền'
    }

    # This should trigger the graph query and completion check
    print("\nCalling _handle_continuation with context:")
    print(f"  completed_step: {continuation_context['completed_step']}")
    print(f"  next_step: {continuation_context['next_step']}")
    print(f"  faq_id: {continuation_context['faq_id']}")

    # We need to check what _handle_continuation returns
    # Let's manually check the logic

    faq_id = continuation_context['faq_id']
    next_step = continuation_context['next_step']
    completed_step = continuation_context['completed_step']

    graph_result = engine._query_steps_by_faq_id(faq_id, from_step=next_step, only_next_step=True)

    print(f"\nGraph query result:")
    if graph_result:
        print(f"  total_steps: {graph_result.get('total_steps', 0)}")
        print(f"  total_steps_in_process: {graph_result.get('total_steps_in_process', 'NOT FOUND')}")

        total_from_graph = graph_result.get('total_steps_in_process', 0)
        if total_from_graph > 0:
            print(f"\n  Checking: {completed_step} >= {total_from_graph}?")
            if completed_step >= total_from_graph:
                print(f"  ✅ YES - Should show completion message!")
            else:
                print(f"  ❌ NO - Should show next step")
        else:
            print(f"  ❌ total_steps_in_process not available from graph")
    else:
        print(f"  ❌ No graph result returned")

    engine.close()

if __name__ == "__main__":
    print("DEBUGGING GRAPH-BASED COMPLETION DETECTION")
    print("=" * 80)

    try:
        test_graph_query()
        test_continuation_logic()
        test_end_to_end()

        print("\n" + "=" * 80)
        print("DEBUGGING COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
