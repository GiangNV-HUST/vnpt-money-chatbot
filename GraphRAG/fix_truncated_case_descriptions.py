# -*- coding: utf-8 -*-
"""
Fix truncated Case.description fields in Neo4j

The Case nodes were created with description[:200] truncation.
This script updates them with full descriptions.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector


def fix_faq_0_cases():
    """Fix FAQ_0 Case descriptions"""
    conn = Neo4jConnector()

    # Case 1: Nạp tiền từ ngân hàng liên kết (currently truncated at 200 chars)
    case1_full_desc = """Nạp tiền từ ngân hàng liên kết:
Bước 1: Tại giao diện chính, chọn mục "Nạp tiền".
Bước 2: Nhập số tiền cần nạp và nhấn "Nạp tiền".
Bước 3: Màn hình Xác nhận giao dịch và nhấn "Nạp tiền"
Bước 4: Màn hình nhập OTP
Bước 5: Màn hình xác nhận giao dịch Nạp tiền thành công"""

    # Case 2: Nạp bằng Chuyển khoản ngân hàng (this one is okay, only 143 chars)
    case2_full_desc = """Nạp bằng Chuyển khoản ngân hàng: Bạn chọn ngân hàng cần nạp, sau đó Lưu mã QR và thực hiện chuyển khoản qua QR đa năng bằng ứng dụng ngân hàng."""

    print("Fixing truncated Case descriptions for FAQ_0...")
    print("=" * 80)

    # Update Case 1
    result1 = conn.execute_query("""
        MATCH (c:Case {name: "Nạp tiền từ ngân hàng liên kết"})
        SET c.description = $desc
        RETURN c.name as name, c.description as description
    """, {"desc": case1_full_desc}, write=True)

    for record in result1:
        print(f"\n✅ Updated: {record['name']}")
        print(f"Description length: {len(record['description'])} chars")
        print(f"Description:\n{record['description']}")

    # Update Case 2 (for consistency)
    result2 = conn.execute_query("""
        MATCH (c:Case {name: "Nạp bằng Chuyển khoản ngân hàng"})
        SET c.description = $desc
        RETURN c.name as name, c.description as description
    """, {"desc": case2_full_desc}, write=True)

    for record in result2:
        print(f"\n✅ Updated: {record['name']}")
        print(f"Description length: {len(record['description'])} chars")
        print(f"Description:\n{record['description']}")

    print("\n" + "=" * 80)
    print("Done! Case descriptions have been updated with full text.")


def verify_fix():
    """Verify the fix worked"""
    conn = Neo4jConnector()

    print("\n" + "=" * 80)
    print("VERIFICATION: Checking updated Case nodes")
    print("=" * 80)

    result = conn.execute_query("""
        MATCH (faq:FAQ {id: "FAQ_0"})-[:HAS_CASE]->(c:Case)
        RETURN c.name as name,
               length(c.description) as desc_length,
               c.description as description
        ORDER BY c.name
    """)

    for record in result:
        print(f"\nCase: {record['name']}")
        print(f"Length: {record['desc_length']} chars")
        print(f"Description:\n{record['description']}")


if __name__ == "__main__":
    fix_faq_0_cases()
    verify_fix()
