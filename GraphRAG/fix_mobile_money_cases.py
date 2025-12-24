"""
Fix FAQ "Tôi có thể nạp tiền từ ngân hàng vào tài khoản Mobile Money như thế nào?"
Tách thành 2 Case nodes riêng biệt:
- Case 1: Nạp tiền từ ngân hàng liên kết trực tiếp (5 bước)
- Case 2: Nạp bằng Chuyển khoản ngân hàng (QR code)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector


def create_case_nodes():
    """Tạo 2 Case nodes cho FAQ nạp tiền Mobile Money"""

    connector = Neo4jConnector()

    # FAQ question
    faq_question = "Tôi có thể nạp tiền từ ngân hàng vào tài khoản Mobile Money như thế nào?"

    print('='*80)
    print('Cập nhật 2 Case nodes cho FAQ:')
    print(f'"{faq_question}"')
    print('='*80)

    # Bước 1: Kiểm tra FAQ node có tồn tại không
    check_query = '''
    MATCH (faq:FAQ)
    WHERE faq.question = $question
    RETURN faq.question as question, faq.answer as answer
    '''

    result = connector.execute_query(check_query, {'question': faq_question})

    if not result:
        print('❌ Không tìm thấy FAQ node!')
        connector.close()
        return

    print(f'✅ Tìm thấy FAQ node')

    # Bước 2: Xóa các Case nodes cũ nếu có
    delete_old_cases = '''
    MATCH (faq:FAQ)-[:HAS_CASE]->(case:Case)
    WHERE faq.question = $question
    DETACH DELETE case
    '''

    connector.execute_query(delete_old_cases, {'question': faq_question}, write=True)
    print('✅ Đã xóa các Case nodes cũ (nếu có)')

    # Bước 3: Tạo Case 1 - Nạp tiền từ ngân hàng liên kết trực tiếp
    create_case1 = '''
    MATCH (faq:FAQ)
    WHERE faq.question = $question
    CREATE (case1:Case {
        case_id: "mobile_money_deposit_case_1",
        name: "Nạp tiền từ ngân hàng liên kết trực tiếp",
        description: "Nạp tiền vào tài khoản Mobile Money từ ngân hàng đã liên kết trực tiếp trên ứng dụng VNPT Money",
        case_type: "method",
        method: "bank_linked"
    })
    CREATE (faq)-[:HAS_CASE]->(case1)
    RETURN case1.name as case_name
    '''

    result1 = connector.execute_query(create_case1, {'question': faq_question}, write=True)
    print(f'✅ Đã tạo Case 1: {result1[0]["case_name"]}')

    # Bước 4: Link 5 Step nodes hiện có vào Case 1
    link_steps_to_case1 = '''
    MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(process:Process)-[:HAS_STEP]->(step:Step)
    WHERE faq.question = $question
    MATCH (case1:Case {case_id: "mobile_money_deposit_case_1"})
    CREATE (case1)-[:HAS_STEP]->(step)
    RETURN count(step) as steps_linked
    '''

    result_steps = connector.execute_query(link_steps_to_case1, {'question': faq_question}, write=True)
    print(f'✅ Đã link {result_steps[0]["steps_linked"]} Steps vào Case 1')

    # Bước 5: Tạo Case 2 - Nạp bằng Chuyển khoản ngân hàng (QR)
    create_case2 = '''
    MATCH (faq:FAQ)
    WHERE faq.question = $question
    CREATE (case2:Case {
        case_id: "mobile_money_deposit_case_2",
        name: "Nạp bằng Chuyển khoản ngân hàng",
        description: "Nạp tiền vào Mobile Money bằng cách chuyển khoản qua mã QR từ ứng dụng ngân hàng",
        case_type: "method",
        method: "bank_transfer_qr"
    })
    CREATE (faq)-[:HAS_CASE]->(case2)
    RETURN case2.name as case_name
    '''

    result2 = connector.execute_query(create_case2, {'question': faq_question}, write=True)
    print(f'✅ Đã tạo Case 2: {result2[0]["case_name"]}')

    # Bước 6: Tạo Step cho Case 2
    create_step_case2 = '''
    MATCH (case2:Case {case_id: "mobile_money_deposit_case_2"})
    CREATE (step:Step {
        id: "mobile_money_deposit_case_2_step_1",
        number: 1,
        text: "Bạn chọn ngân hàng cần nạp, sau đó lưu mã QR và thực hiện chuyển khoản qua QR đa năng bằng ứng dụng ngân hàng.",
        process_id: "deposit_qr"
    })
    CREATE (case2)-[:HAS_STEP]->(step)
    RETURN step.text as step_text
    '''

    result_step2 = connector.execute_query(create_step_case2, write=True)
    print(f'✅ Đã tạo Step cho Case 2')

    # Bước 7: Cập nhật FAQ answer để chỉ giữ phần mở đầu
    update_faq_answer = '''
    MATCH (faq:FAQ)
    WHERE faq.question = $question
    SET faq.answer = "Để thực hiện nạp tiền vào tài khoản Mobile Money có 2 hình thức: Nạp tiền từ ngân hàng liên kết trực tiếp hoặc Nạp bằng Chuyển khoản ngân hàng (QR code)."
    RETURN faq.answer as new_answer
    '''

    result_update = connector.execute_query(update_faq_answer, {'question': faq_question}, write=True)
    print(f'✅ Đã cập nhật FAQ answer')

    # Bước 8: Kiểm tra kết quả
    verify_query = '''
    MATCH (faq:FAQ)-[:HAS_CASE]->(case:Case)
    WHERE faq.question = $question
    OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
    RETURN case.case_id as case_id,
           case.name as case_name,
           count(step) as step_count
    ORDER BY case_id
    '''

    verify_results = connector.execute_query(verify_query, {'question': faq_question})

    print('\n' + '='*80)
    print('Kết quả kiểm tra:')
    print('='*80)
    for record in verify_results:
        print(f'  • {record["case_name"]}: {record["step_count"]} steps')

    print('\n✅ Hoàn thành cập nhật 2 Case nodes!')

    connector.close()


if __name__ == '__main__':
    create_case_nodes()
