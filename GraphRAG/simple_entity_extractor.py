# -*- coding: utf-8 -*-
"""
Simple Pattern-Based Entity Extractor for Short Queries
Faster and more reliable for short user queries than LLM extraction
"""

import re
from typing import Dict, List


class SimpleEntityExtractor:
    """Fast pattern-based entity extraction for user queries"""

    def __init__(self):
        """Initialize with entity patterns"""

        # Bank patterns
        self.banks = [
            "Vietinbank", "Vietcombank", "BIDV", "Techcombank", "ACB",
            "VPBank", "MB Bank", "Sacombank", "VIB", "HDBank",
            "TPBank", "OCB", "Agribank", "SeABank", "LienVietPostBank",
            "SHB", "VietABank", "PGBank", "BacABank", "Eximbank",
            "MSB", "NCB", "SCB", "ABBank", "VietBank", "Nam A Bank" 
        ]

        # Service patterns (must match entities in Neo4j database)
        self.services = [
            "VNPT Money", "VNPT Pay", "Mobile Banking", "Internet Banking",
            "Ví điện tử"
            # NOTE: "Ví VNPT" removed - not in database, use "VNPT Money" instead
        ]

        # Topic/Action patterns (common user queries)
        self.topics = {
            "Nạp tiền": ["nạp tiền", "nạp", "top up", "chuyển tiền vào ví"],
            "Rút tiền": ["rút tiền", "rút", "withdraw", "chuyển tiền ra"],
            "Phí rút tiền": ["phí rút tiền", "mất phí rút", "bị tính phí rút", "phí khi rút tiền"],
            "Liên kết ngân hàng": ["liên kết ngân hàng", "liên kết", "link bank", "kết nối ngân hàng"],
            "Chuyển tiền": ["chuyển tiền", "chuyển khoản", "transfer"],
            "Thanh toán": ["thanh toán", "payment", "trả", "đóng"],
            "Kiểm tra số dư": ["kiểm tra số dư", "xem số dư", "số dư", "balance"],
            "Lịch sử giao dịch": ["lịch sử", "history", "sao kê", "giao dịch"],
            "Quên mật khẩu": ["quên mật khẩu", "forgot password", "reset mật khẩu"],
            "Đổi mật khẩu": ["đổi mật khẩu", "thay đổi mật khẩu", "change password", "đặt lại mật khẩu"],
            "Định danh": ["định danh", "eKYC", "xác minh"],
            "Sinh trắc học": ["sinh trắc", "vân tay", "khuôn mặt", "face id", "touch id"],
            "OTP": ["otp", "mã xác thực", "mã xác nhận"],
            "Vé máy bay": ["vé máy bay", "vé bay", "flight ticket", "đặt vé máy bay"],
            "Biểu phí": ["biểu phí", "bảng phí", "chính sách phí", "phí dịch vụ"],
            # ACCOUNT MANAGEMENT TOPICS
            "Mở khóa tài khoản": ["mở khóa tài khoản", "mở khóa ví", "unlock account", "unlock ví"],
            "Khóa tài khoản": ["khóa tài khoản", "khóa ví", "lock account", "đóng tài khoản"],
            "Hủy tài khoản": ["hủy tài khoản", "xóa tài khoản", "đóng tài khoản", "close account"],
            "Mở khóa Mobile Money": ["mở khóa mobile money"],
            "Khóa Mobile Money": ["khóa mobile money"],
            # TROUBLESHOOTING TOPICS
            "Kiểm tra trạng thái giao dịch": ["kiểm tra trạng thái", "trạng thái giao dịch", "tra cứu giao dịch"],
            "Xử lý sự cố": ["xử lý sự cố", "troubleshoot", "giải quyết vấn đề"],
        }

        # Error patterns (EXPANDED for better problem detection)
        self.errors = [
            # Original errors
            "thông tin thẻ/tài khoản không hợp lệ",
            "không nhận được OTP",
            "quá hạn mức",
            "tài khoản không đủ số dư",
            "giao dịch thất bại",
            "ngày sinh không khớp",
            "định danh thất bại",
            # NEW: Money transfer issues
            "chưa nhận được tiền",
            "tiền chưa về",
            "chưa nhận được",
            "chưa có tiền",
            "không nhận được tiền",
            "không có tiền",
            "tài khoản thụ hưởng chưa nhận",
            "người nhận chưa nhận được",
            "bên nhận chưa có tiền",
            "chuyển tiền mà chưa nhận",
            "chuyển rồi mà chưa có",
            "chuyển tiền nhưng chưa nhận được",
            # Transaction status issues
            "giao dịch đang xử lý",
            "giao dịch chờ xác nhận",
            "giao dịch bị treo",
        ]

        # Feature patterns
        self.features = [
            "QR code", "QR đa năng", "NFC", "SmartOTP",
            "Tra soát", "Biểu phí"
        ]

        # Action patterns (IMPORTANT: Actions người dùng cần thực hiện)
        self.actions = {
            "Nạp tiền": ["nạp tiền", "nạp"],
            "Rút tiền": ["rút tiền", "rút"],
            "Chuyển tiền": ["chuyển tiền", "chuyển khoản"],
            "Liên kết ngân hàng": ["liên kết ngân hàng", "liên kết bank"],
            "Hủy liên kết": ["hủy liên kết", "hủy link", "gỡ liên kết"],
            "Liên kết lại": ["liên kết lại", "link lại"],
            "Kiểm tra trạng thái": ["kiểm tra trạng thái", "tra cứu trạng thái", "xem trạng thái"],
            "Kiểm tra số dư": ["kiểm tra số dư", "xem số dư"],
            "Liên hệ hỗ trợ": ["liên hệ hỗ trợ", "liên hệ hotline", "gọi hotline"],
            "Tra soát": ["tra soát", "yêu cầu tra soát"],
            "Đăng ký": ["đăng ký", "register"],
            "Cập nhật thông tin": ["cập nhật", "update"],
            "Định danh": ["định danh", "ekyc", "xác minh"],
        }

        # Status patterns (Trạng thái giao dịch/tài khoản)
        self.statuses = [
            "Thành công",
            "Đang xử lý",
            "Thất bại",
            "Chờ xác nhận",
            "Đã kích hoạt",
            "Chưa kích hoạt",
            "Hoàn thành",
            "Bị từ chối",
        ]

        # TimeFrame patterns (Khung thời gian)
        self.timeframes = [
            "2 ngày làm việc",
            "3 ngày làm việc",
            "45-60 ngày làm việc",
            "ngay lập tức",
            "trong vòng 24h",
            "trong ngày",
        ]

        # Document patterns (Giấy tờ)
        self.documents = [
            "CCCD", "CMND", "Hộ chiếu",
            "CCCD gắn chíp", "Căn cước công dân",
            "Chứng minh nhân dân", "Giấy tờ"
        ]

        # AccountType patterns (Loại tài khoản)
        self.account_types = [
            "Tài khoản ví",
            "Tài khoản ngân hàng",
            "Thẻ nội địa",
            "Số tài khoản",
            "Số thẻ",
            "Tài khoản Mobile Money",
        ]

        # UIElement patterns (Phần tử giao diện)
        self.ui_elements = [
            "Cá nhân", "Ngân hàng liên kết", "Chuyển tiền",
            "Trợ giúp", "Qua số tài khoản/số thẻ",
            "Lịch sử giao dịch", "Nạp tiền", "Rút tiền"
        ]

        # ContactChannel patterns (Kênh liên hệ)
        self.contact_channels = [
            "Hotline", "Trợ giúp", "Bộ phận hỗ trợ",
            "CSKH", "Chăm sóc khách hàng"
        ]

        # Fee patterns (Phí dịch vụ) - IMPORTANT!
        self.fee_keywords = [
            "phí", "biểu phí", "bảng phí", "chính sách phí",
            "phí dịch vụ", "chi phí", "mất phí", "tính phí"
        ]

        # Limit patterns (Hạn mức)
        self.limit_keywords = [
            "hạn mức", "giới hạn", "tối đa", "tối thiểu",
            "số tiền tối đa", "số lần", "hạn mức giao dịch"
        ]

        # Requirement patterns (Điều kiện)
        self.requirements = [
            "Đăng ký dịch vụ thanh toán trực tuyến",
            "Có số dư tối thiểu",
            "Thông tin trùng khớp",
            "Định danh thành công",
        ]

    def is_out_of_scope(self, query: str) -> bool:
        """
        Check if query is out of scope (not related to VNPT Money)

        Returns:
            True if query is clearly out of scope
        """
        query_lower = query.lower().strip()

        # Out-of-scope patterns (things NOT in VNPT Money service)
        out_of_scope_patterns = [
            "mua máy bay",       # Buy airplane (not flight ticket!)
            "mua ô tô",          # Buy car
            "mua nhà",           # Buy house
            "mua đất",           # Buy land
            "thuê xe",           # Rent car
            "đặt khách sạn",     # Book hotel
            "book hotel",
            "mua vàng",          # Buy gold
            "mua cổ phiếu",      # Buy stocks
        ]

        # Check for exact out-of-scope patterns
        for pattern in out_of_scope_patterns:
            if pattern in query_lower:
                return True

        return False

    def extract(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from user query using pattern matching

        Args:
            query: User query string

        Returns:
            Dict of entity types and extracted values (MATCHES document extraction structure)
        """
        query_lower = query.lower().strip()

        # Initialize with ALL entity types (same as LLM document extraction)
        entities = {
            "Topic": [],
            "Service": [],
            "Bank": [],
            "Error": [],
            "Action": [],
            "Requirement": [],
            "Feature": [],
            "TimeFrame": [],
            "Status": [],
            "Document": [],
            "AccountType": [],
            "UIElement": [],
            "ContactChannel": [],
            "Fee": [],
            "Limit": [],
            "out_of_scope": self.is_out_of_scope(query)  # Add flag
        }

        # Extract banks (case-insensitive)
        for bank in self.banks:
            if bank.lower() in query_lower:
                entities["Bank"].append(bank)

        # Extract services
        for service in self.services:
            if service.lower() in query_lower:
                entities["Service"].append(service)

        # Extract topics/actions (prioritize longer/more specific patterns)
        # Sort topics by pattern length (descending) to match specific patterns first
        sorted_topics = sorted(
            self.topics.items(),
            key=lambda x: max(len(p) for p in x[1]),
            reverse=True
        )

        for topic, patterns in sorted_topics:
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    entities["Topic"].append(topic)
                    break  # Only add once per topic

        # Extract errors
        for error in self.errors:
            if error.lower() in query_lower:
                entities["Error"].append(error)

        # Extract features
        for feature in self.features:
            if feature.lower() in query_lower:
                entities["Feature"].append(feature)

        # Extract actions (NEW!)
        sorted_actions = sorted(
            self.actions.items(),
            key=lambda x: max(len(p) for p in x[1]),
            reverse=True
        )
        for action, patterns in sorted_actions:
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    entities["Action"].append(action)
                    break

        # Extract statuses (NEW!)
        for status in self.statuses:
            if status.lower() in query_lower:
                entities["Status"].append(status)

        # Extract timeframes (NEW!)
        for timeframe in self.timeframes:
            if timeframe.lower() in query_lower:
                entities["TimeFrame"].append(timeframe)

        # Extract documents (NEW!)
        for doc in self.documents:
            if doc.lower() in query_lower:
                entities["Document"].append(doc)

        # Extract account types (NEW!)
        for account_type in self.account_types:
            if account_type.lower() in query_lower:
                entities["AccountType"].append(account_type)

        # Extract UI elements (NEW!)
        for ui_elem in self.ui_elements:
            if ui_elem.lower() in query_lower:
                entities["UIElement"].append(ui_elem)

        # Extract contact channels (NEW!)
        for channel in self.contact_channels:
            if channel.lower() in query_lower:
                entities["ContactChannel"].append(channel)

        # Extract requirements (NEW!)
        for req in self.requirements:
            if req.lower() in query_lower:
                entities["Requirement"].append(req)

        # Extract fees (NEW! - IMPORTANT)
        for fee_keyword in self.fee_keywords:
            if fee_keyword.lower() in query_lower:
                # Lấy toàn bộ context xung quanh keyword "phí"
                entities["Fee"].append(fee_keyword)
                break  # Chỉ thêm 1 lần

        # Extract limits (NEW!)
        for limit_keyword in self.limit_keywords:
            if limit_keyword.lower() in query_lower:
                entities["Limit"].append(limit_keyword)
                break  # Chỉ thêm 1 lần

        # Remove duplicates and empties (skip boolean out_of_scope flag)
        for key in entities:
            if key != "out_of_scope" and isinstance(entities[key], list):
                entities[key] = list(set(entities[key]))

        return entities


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    extractor = SimpleEntityExtractor()

    test_queries = [
        "vé máy bay",
        "máy bay",
        "nạp tiền từ Vietinbank",
        "lỗi thông tin thẻ không hợp lệ",
        "quên mật khẩu VNPT Money",
        "chuyển tiền",
        "liên kết Techcombank"
    ]

    print("=" * 60)
    print("SIMPLE PATTERN-BASED ENTITY EXTRACTION")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        entities = extractor.extract(query)

        # Show only non-empty
        non_empty = {k: v for k, v in entities.items() if v}
        if non_empty:
            for entity_type, entity_list in non_empty.items():
                print(f"  {entity_type}: {entity_list}")
        else:
            print("  (No entities)")
