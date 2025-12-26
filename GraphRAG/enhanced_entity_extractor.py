# -*- coding: utf-8 -*-
"""
Enhanced Entity Extractor với Regex & Confidence Scoring
Cải tiến từ SimpleEntityExtractor
"""

import re
import logging
from typing import Dict, List, Tuple
from simple_entity_extractor import SimpleEntityExtractor

# Setup logger
logger = logging.getLogger(__name__)


class EnhancedEntityExtractor(SimpleEntityExtractor):
    """
    Enhanced version với:
    1. Regex patterns cho flexibility
    2. Confidence scoring
    3. Validation layer
    """

    def __init__(self):
        super().__init__()

        # THÊM: Regex patterns cho error detection
        # IMPORTANT: Error names MUST match Neo4j Error node names exactly!
        self.error_patterns_regex = [
            # "tài khoản thụ hưởng chưa nhận được tiền" - MAIN ERROR for transfer/payment issues
            # Pattern 1: Direct "không nhận được tiền"
            (r"(chưa|không|ko)\s+(nhận|có|thấy)\s+(được\s+)?tiền", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 2: "không nhận được" + context about recipient/phone
            (r"(thuê bao|điện thoại|tài khoản|người nhận|bên nhận|thụ hưởng).*(chưa|không|ko)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 3: "nạp/chuyển/rút tiền" + "không nhận được"
            (r"(nạp|chuyển|rút)\s+(tiền|khoản).*(chưa|không|ko)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 4: Existing pattern for "tiền chưa về"
            (r"tiền\s+(chưa|không|ko)\s+(về|tới|đến)", "tài khoản thụ hưởng chưa nhận được tiền"),
            # Pattern 5: "thành công nhưng không nhận được" (for your specific case)
            (r"(thành công|đã.*trừ).*(nhưng|mà).*(chưa|không)\s+(nhận|có|thấy)\s+(được)?", "tài khoản thụ hưởng chưa nhận được tiền"),

            # "Thông tin giao dịch không nhận được" - For when transaction shows success but recipient didn't receive
            # This matches FAQ_72! Priority: Check this BEFORE generic patterns
            (r"(nạp|chuyển).*(thành công).*(thuê bao|điện thoại|người nhận|bên nhận).*(không|chưa)\s+nhận", "Thông tin giao dịch không nhận được"),
            # Alternative pattern: "thành công" but carrier/bank confirms not received
            (r"(thành công).*(nhà mạng|ngân hàng).*(khẳng định|xác nhận).*(không|chưa)", "Thông tin giao dịch không nhận được"),

            # Giao dịch thất bại patterns
            (r"giao\s*dịch\s+(thất\s*bại|lỗi|fail)", "giao dịch thất bại"),
            (r"(không|chưa)\s+(chuyển|nạp|rút)\s+được", "giao dịch thất bại"),
            (r"(không|chưa)\s+(thành công)", "giao dịch thất bại"),
            # Pattern: "đã trừ tiền nhưng ... chưa có/nhận"
            (r"(đã|bị)\s+trừ\s+tiền.*(chưa|không)\s+(có|nhận)", "tài khoản thụ hưởng chưa nhận được tiền"),
            (r"(chưa|không)\s+(có|nhận).*(đã|bị)\s+trừ\s+tiền", "tài khoản thụ hưởng chưa nhận được tiền"),

            # Đang xử lý nhưng đã trừ tiền (CRITICAL)
            (r"(đang\s+xử\s+lý|processing).*(đã|bị).*(trừ|mất)\s+tiền", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"(đã|bị).*(trừ|mất)\s+tiền.*(đang\s+xử\s+lý|processing)", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"(nạp|chuyển|rút)\s+tiền.*(đang\s+xử\s+lý|báo.*đang).*(đã|bị)\s+trừ", "giao dịch đang xử lý nhưng đã trừ tiền"),
            (r"trạng\s+thái.*(đang\s+xử\s+lý).*(đã|bị)\s+trừ", "giao dịch đang xử lý nhưng đã trừ tiền"),

            # OTP patterns
            (r"(không|chưa)\s+nhận\s+(được\s+)?(otp|mã)", "không nhận được OTP"),

            # Account/Card invalid
            (r"(thẻ|tài\s*khoản)\s+(không\s+)?hợp\s*lệ", "thông tin thẻ/tài khoản không hợp lệ"),

            # Over limit
            (r"(quá|vượt)\s+(hạn\s*mức|giới\s*hạn)", "quá hạn mức"),

            # Wrong transfer patterns (CRITICAL for "chuyển tiền nhầm")
            (r"(chuyển|nạp|rút)\s+(tiền\s+)?(nhầm|sai|lỡ)", "chuyển tiền nhầm"),
            (r"(nhầm|sai|lỡ)\s+(chuyển|nạp)", "chuyển tiền nhầm"),
            (r"chuyển\s+nhầm", "chuyển tiền nhầm"),

            # Biometric error patterns (CRITICAL for biometric issues)
            (r"sinh\s*trắc\s*(học)?.*(báo|hiện|thông\s*báo|xuất\s*hiện).*(lỗi|sai)", "lỗi sinh trắc học"),
            (r"(hệ\s*thống|app).*(báo|hiện|thông\s*báo).*(lỗi|sai).*(sinh\s*trắc|ekyc)", "lỗi sinh trắc học"),
            (r'báo\s*lỗi.*[\"\'].*ngày\s*sinh.*[\"\']', "lỗi ngày sinh không khớp"),
            (r'báo\s*lỗi.*[\"\'].*định\s*danh.*[\"\']', "lỗi định danh không khớp"),
            (r"ngày\s*sinh.*(không\s*khớp|không\s*đúng|sai)", "lỗi ngày sinh không khớp"),
            (r"định\s*danh.*(không\s*khớp|không\s*đúng|sai)", "lỗi định danh không khớp"),
            (r"(cmnd|cccd|căn\s*cước).*(không\s*khớp|không\s*đúng|sai)", "lỗi định danh không khớp"),
            (r"(sinh\s*trắc|ekyc).*(thất\s*bại|không\s*thành\s*công)", "sinh trắc học thất bại"),
            (r"(không|chưa).*(sinh\s*trắc|ekyc).*(được|thành\s*công)", "sinh trắc học thất bại"),
        ]

        # THÊM: Regex patterns cho topic detection
        self.topic_patterns_regex = [
            # CRITICAL FIX: Thanh toán hóa đơn patterns (SPECIFIC patterns first!)
            (r"thanh\s*toán\s+(hóa\s*đơn\s+)?(tiền\s+)?(điện|nước|gas)", "Thanh toán hóa đơn"),
            (r"thanh\s*toán\s+hóa\s*đơn\s+(viễn\s*thông|internet|cước)", "Thanh toán hóa đơn viễn thông"),
            (r"thanh\s*toán\s+(cước\s+)?(viễn\s*thông|internet)", "Thanh toán hóa đơn viễn thông"),
            (r"thanh\s*toán\s+hóa\s*đơn", "Thanh toán hóa đơn"),

            # Generic topics that LLM often extracts
            (r"chuyển\s+tiền", "Chuyển tiền"),
            (r"nạp\s+tiền", "Nạp tiền"),
            (r"rút\s+tiền", "Rút tiền"),
            (r"cài\s+đặt", "Cài đặt"),
            (r"hủy\s+dịch\s+vụ", "Hủy dịch vụ"),
            (r"mở\s+tài\s+khoản", "Mở tài khoản"),
            (r"định\s+danh", "Định danh"),
            (r"liên\s+kết\s+ngân\s+hàng", "Liên kết ngân hàng"),
            # Context-based Topic patterns
            (r"nhập\s+số\s+tiền\s+cần\s+chuyển", "Chuyển tiền"),  # From context

            # Mở khóa patterns
            (r"mở\s*khóa\s+(tài\s*khoản|ví)", "Mở khóa tài khoản"),
            (r"unlock\s+(account|ví)", "Mở khóa tài khoản"),

            # Khóa patterns
            (r"khóa\s+(tài\s*khoản|ví)", "Khóa tài khoản"),
            (r"lock\s+(account|ví)", "Khóa tài khoản"),

            # Đổi mật khẩu patterns
            (r"đổi\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"thay\s*đổi\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"đặt\s*lại\s+(mật\s*khẩu|password)", "Đổi mật khẩu"),
            (r"change\s+password", "Đổi mật khẩu"),
        ]

        # THÊM: Regex patterns cho Action detection (NEW!)
        self.action_patterns_regex = [
            (r"hủy\s+(liên\s*kết)", "Hủy liên kết"),
            (r"liên\s*kết\s+(lại|lại\s+ngân\s*hàng)", "Liên kết lại"),
            (r"kiểm\s*tra\s+trạng\s*thái", "Kiểm tra trạng thái"),
            (r"tra\s*cứu\s+trạng\s*thái", "Kiểm tra trạng thái"),
            (r"liên\s*hệ\s+(hỗ\s*trợ|hotline)", "Liên hệ hỗ trợ"),
            (r"gọi\s+hotline", "Liên hệ hỗ trợ"),
            (r"tra\s*soát", "Tra soát"),
            (r"yêu\s*cầu\s+tra\s*soát", "Tra soát"),

            # Common actions from LLM gaps
            (r"mở\s+tài\s+khoản", "Mở tài khoản"),
            (r"xem\s+lịch\s+sử\s+giao\s+dịch", "Xem lịch sử giao dịch"),
            (r"bấm\s+vào\s+nút\s+xác\s+nhận", "Bấm vào nút Xác nhận"),
        ]

        # THÊM: Regex patterns cho Status detection (NEW!)
        self.status_patterns_regex = [
            (r"đang\s+xử\s+lý", "Đang xử lý"),
            (r"chờ\s+xác\s+nhận", "Chờ xác nhận"),
            (r"thất\s+bại", "Thất bại"),
            (r"thành\s+công", "Thành công"),
        ]

        # THÊM: Regex patterns cho Fee detection (NEW! - IMPORTANT)
        self.fee_patterns_regex = [
            (r"phí\s+(rút\s+tiền|chuyển\s+tiền|nạp\s+tiền|dịch\s+vụ)", "phí"),
            (r"biểu\s+phí", "biểu phí"),
            (r"bảng\s+phí", "bảng phí"),
            (r"mất\s+phí", "phí"),
            (r"tính\s+phí", "phí"),
        ]

        # THÊM: Regex patterns cho Limit detection (NEW!)
        self.limit_patterns_regex = [
            (r"hạn\s+mức", "hạn mức"),
            (r"giới\s+hạn", "giới hạn"),
            (r"số\s+tiền\s+tối\s+đa", "hạn mức"),
            (r"tối\s+đa", "tối đa"),
        ]

        # THÊM: Regex patterns cho Requirement detection (NEW! - PRIORITY 1)
        self.requirement_patterns_regex = [
            (r"cần\s+(có|gì|phải|làm|những gì)", "điều kiện cần thiết"),
            (r"yêu\s*cầu", "yêu cầu"),
            (r"phải\s+có", "điều kiện"),
            (r"điều\s*kiện", "điều kiện"),
            (r"bắt\s+buộc", "bắt buộc"),
            (r"cần\s+thiết", "cần thiết"),
            (r"đòi\s+hỏi", "yêu cầu"),
            (r"có\s+(cccd|cmnd)", "Có CCCD"),  # From LLM gaps
        ]

        # THÊM: Regex patterns cho Feature detection (NEW! - PRIORITY 1)
        self.feature_patterns_regex = [
            (r"\bqr\b", "QR"),
            (r"mã\s+qr", "QR"),
            (r"\bnfc\b", "NFC"),
            (r"\botp\b", "OTP"),
            (r"mã\s+otp", "OTP"),
            (r"tra\s*soát", "tra soát"),
            (r"lịch\s+sử\s+(giao\s+dịch|nạp\s+tiền)", "lịch sử giao dịch"),
            (r"sinh\s*trắc\s*học", "sinh trắc học"),
            (r"ekyc", "eKYC"),
            (r"xác\s+thực\s+2\s+lớp", "2FA"),
            (r"2fa", "2FA"),
            (r"thông\s+báo\s+push", "push notification"),
            (r"vân\s+tay", "vân tay"),
            (r"khuôn\s+mặt", "nhận diện khuôn mặt"),
        ]

        # THÊM: Regex patterns cho UIElement detection (NEW! - PRIORITY 1 - CRITICAL!)
        self.ui_element_patterns_regex = [
            # Menu tabs
            (r"(tab|mục)\s+cá\s+nhân", "Cá nhân"),
            (r"(tab|mục)\s+ngân\s+hàng\s+liên\s+kết", "Ngân hàng liên kết"),
            (r"(tab|mục)\s+chuyển\s+tiền", "Chuyển tiền"),
            (r"(tab|mục)\s+nạp\s+tiền", "Nạp tiền"),
            (r"(tab|mục)\s+rút\s+tiền", "Rút tiền"),
            (r"(tab|mục)\s+thanh\s+toán", "Thanh toán"),
            (r"(tab|mục)\s+lịch\s+sử", "Lịch sử"),
            (r"(tab|mục)\s+cài\s+đặt", "Cài đặt"),
            (r"(tab|mục)\s+trợ\s+giúp", "Trợ giúp"),

            # Buttons (specific)
            (r"nút\s+xác\s+nhận", "Xác nhận"),  # From LLM gaps
            (r"nút\s+(chuyển\s+tiền|nạp\s+tiền|rút\s+tiền|xác\s+nhận|hủy)", "nút"),
            (r"(nhấn|bấm|chọn)\s+vào", "action button"),

            # Generic references
            (r"\bmục\b", "Mục"),  # From LLM gaps

            # Fields
            (r"(ô|trường)\s+nhập", "input field"),
            (r"nhập\s+(số\s+tiền|số\s+điện\s+thoại|tài\s+khoản)", "input field"),

            # Icons
            (r"biểu\s+tượng", "icon"),
            (r"icon", "icon"),
        ]

        # THÊM: Regex patterns cho TimeFrame detection (NEW! - PRIORITY 2)
        self.timeframe_patterns_regex = [
            (r"ngày\s+làm\s+việc", "ngày làm việc"),
            (r"ngay\s+lập\s+tức", "ngay lập tức"),
            (r"trong\s+vòng\s+\d+\s+(ngày|giờ|phút)", "trong vòng"),
            (r"24\s*\/\s*7", "24/7"),
            (r"(hàng\s+ngày|mỗi\s+ngày)", "hàng ngày"),
            (r"cuối\s+tuần", "cuối tuần"),
            (r"(thứ\s+[2-7]|chủ\s+nhật)", "ngày trong tuần"),
            (r"(sáng|chiều|tối)", "khung giờ trong ngày"),
        ]

        # THÊM: Regex patterns cho Document detection (NEW! - PRIORITY 2)
        self.document_patterns_regex = [
            (r"\bcccd\b", "CCCD"),
            (r"căn\s+cước\s+công\s+dân", "CCCD"),
            (r"cccd\s+gắn\s+chip", "CCCD gắn chip"),
            (r"\bcmnd\b", "CMND"),
            (r"chứng\s+minh\s+nhân\s+dân", "CMND"),
            (r"hộ\s+chiếu", "Hộ chiếu"),
            (r"passport", "Hộ chiếu"),
            (r"giấy\s+tờ\s+tùy\s+thân", "giấy tờ tùy thân"),
            (r"bằng\s+lái\s+xe", "bằng lái xe"),
        ]

        # THÊM: Regex patterns cho AccountType detection (NEW! - PRIORITY 2)
        self.account_type_patterns_regex = [
            (r"tài\s+khoản\s+ví", "tài khoản ví"),
            (r"ví\s+điện\s+tử", "ví điện tử"),
            (r"tài\s+khoản\s+ngân\s+hàng", "tài khoản ngân hàng"),
            (r"thẻ\s+nội\s+địa", "thẻ nội địa"),
            (r"thẻ\s+atm", "thẻ ATM"),
            (r"thẻ\s+tín\s+dụng", "thẻ tín dụng"),
            (r"thẻ\s+ghi\s+nợ", "thẻ ghi nợ"),
            (r"tài\s+khoản\s+thanh\s+toán", "tài khoản thanh toán"),
        ]

        # THÊM: Regex patterns cho ContactChannel detection (NEW! - PRIORITY 3)
        self.contact_channel_patterns_regex = [
            (r"hotline", "Hotline"),
            (r"(gọi|điện)\s+(hỗ\s+trợ|tổng\s+đài)", "Hotline"),
            (r"trợ\s+giúp", "Trợ giúp"),
            (r"hỗ\s+trợ\s+trực\s+tuyến", "hỗ trợ trực tuyến"),
            (r"chat\s+(hỗ\s+trợ|support)", "chat support"),
            (r"email\s+(hỗ\s+trợ|support)", "email support"),
            (r"trung\s+tâm\s+hỗ\s+trợ", "trung tâm hỗ trợ"),
        ]

        # THÊM: Expanded Service patterns (IMPROVE EXISTING - specific patterns)
        self.service_patterns_regex = [
            (r"vnpt\s+money", "VNPT Money"),
            (r"vnpt\s+pay", "VNPT Pay"),
            (r"mobile\s+banking", "Mobile Banking"),
            (r"internet\s+banking", "Internet Banking"),
            (r"ví\s+điện\s+tử", "Ví điện tử"),
            (r"app\s+vnpt", "VNPT Money"),
            (r"ứng\s+dụng\s+vnpt", "VNPT Money"),
        ]

        # THÊM: Expanded Bank patterns (IMPROVE EXISTING - specific patterns for major banks)
        self.bank_patterns_regex = [
            (r"vietinbank", "Vietinbank"),
            (r"vietcombank", "Vietcombank"),
            (r"\bbidv\b", "BIDV"),
            (r"techcombank", "Techcombank"),
            (r"\bacb\b", "ACB"),
            (r"vpbank", "VPBank"),
            (r"mb\s+bank", "MB Bank"),
            (r"sacombank", "Sacombank"),
            (r"\bvib\b", "VIB"),
            (r"hdbank", "HDBank"),
            (r"tpbank", "TPBank"),
            (r"\bocb\b", "OCB"),
            (r"agribank", "Agribank"),
            (r"seabank", "SeABank"),
            (r"lienvietpostbank", "LienVietPostBank"),
            (r"\bshb\b", "SHB"),
        ]

        # THÊM: Expanded Action patterns (IMPROVE EXISTING - more common actions)
        # Note: self.action_patterns_regex already exists, so we'll add to it
        self.action_patterns_regex.extend([
            (r"nhập\s+số\s+tiền", "Nhập số tiền"),
            (r"chọn\s+ngân\s+hàng", "Chọn ngân hàng"),
            (r"chọn\s+(loại|dịch\s+vụ)", "Chọn dịch vụ"),
            (r"xác\s+nhận\s+giao\s+dịch", "Xác nhận giao dịch"),
            (r"nhập\s+mã\s+otp", "Nhập mã OTP"),
            (r"nhập\s+số\s+điện\s+thoại", "Nhập số điện thoại"),
            (r"nhập\s+tài\s+khoản", "Nhập tài khoản"),
            (r"bấm\s+(nút|chọn)", "Bấm nút"),
            (r"vào\s+mục", "Vào mục"),
            (r"chuyển\s+sang\s+(tab|mục)", "Chuyển tab"),
        ])

        # THÊM: Contextual rules
        self.contextual_rules = {
            # Nếu có "chuyển tiền" + "chưa" → Error: chưa nhận được
            ("chuyển tiền", "chưa"): ("Error", "chưa nhận được tiền"),
            ("nạp tiền", "thất bại"): ("Error", "giao dịch thất bại"),

            # Nếu có "mở khóa" + "tài khoản" → Topic: Mở khóa tài khoản
            ("mở khóa", "tài khoản"): ("Topic", "Mở khóa tài khoản"),
            ("mở khóa", "ví"): ("Topic", "Mở khóa tài khoản"),
        }

    def extract_with_confidence(self, query: str) -> Tuple[Dict[str, List[str]], float]:
        """
        HYBRID extraction with strategy selection:
        - LLM-First Strategy (if USE_LLM_FIRST_STRATEGY = True): Always use LLM, regex for augmentation
        - Pattern-First Strategy (default): Pattern first, LLM fallback

        Returns:
            (entities_dict, confidence_score)
        """
        import config

        # Check which strategy to use
        if getattr(config, 'USE_LLM_FIRST_STRATEGY', False):
            # NEW: LLM-First Strategy (80% LLM, 20% Regex)
            return self._extract_llm_first(query)
        else:
            # OLD: Pattern-First Strategy (Regex first, LLM fallback)
            return self._extract_pattern_first(query)

    def _extract_pattern_first(self, query: str) -> Tuple[Dict[str, List[str]], float]:
        """
        Original Pattern-First Strategy: Pattern-first, LLM fallback
        """
        import config

        # Step 1: Pattern-based extraction (from parent)
        entities = self.extract(query)

        # Step 2: Enhanced regex extraction
        regex_entities = self._extract_with_regex(query)

        # Step 3: Merge results
        entities = self._merge_entities(entities, regex_entities)

        # Step 4: Apply contextual rules
        entities = self._apply_contextual_rules(query, entities)

        # Step 5: Validate
        entities = self._validate_entities(query, entities)

        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(query, entities)

        # Step 7: HYBRID - LLM fallback if needed
        if config.ENABLE_LLM_FALLBACK:
            should_use_llm, reason = self._should_use_llm_fallback(query, entities, confidence)

            if should_use_llm:
                logger.info(f"🤖 LLM fallback triggered: {reason}")
                logger.info(f"   Pattern confidence: {confidence:.2%}")

                try:
                    llm_entities = self._extract_with_llm(query)

                    if llm_entities:
                        # Merge LLM results with pattern results (LLM takes priority)
                        entities = self._merge_llm_results(entities, llm_entities)
                        confidence = 0.95  # High confidence from LLM
                        logger.info(f"   ✅ LLM extraction successful")
                        logger.info(f"   LLM entities: {llm_entities}")
                except Exception as e:
                    logger.error(f"   ❌ LLM fallback failed: {e}")
                    logger.info(f"   → Using pattern-based results (confidence: {confidence:.2%})")

        return entities, confidence

    def _extract_llm_first(self, query: str) -> Tuple[Dict[str, List[str]], float]:
        """
        NEW: LLM-First Strategy (80% LLM, 20% Regex)

        Always use LLM for semantic understanding, regex for augmentation/validation
        This provides best accuracy at higher cost
        """
        import config

        logger.info(f"🎯 LLM-First Strategy: Using LLM for primary extraction")

        # Step 1: LLM extraction (PRIMARY - 80% weight)
        try:
            llm_entities = self._extract_with_llm(query)
            llm_success = True
            logger.info(f"   ✅ LLM extraction successful")
            logger.info(f"   LLM entities: {llm_entities}")
        except Exception as e:
            logger.error(f"   ❌ LLM extraction failed: {e}")
            logger.info(f"   → Falling back to regex-only")
            llm_entities = {}
            llm_success = False

        # Step 2: Regex extraction (SECONDARY - 20% weight, for augmentation)
        regex_entities = self._extract_with_regex(query)
        logger.info(f"   📋 Regex entities (for augmentation): {regex_entities}")

        # Step 3: Intelligent merge (LLM priority)
        if llm_success:
            # Merge with LLM priority (80% LLM, 20% Regex)
            entities = self._merge_llm_priority(llm_entities, regex_entities)
            confidence = 0.95
            logger.info(f"   ✅ Final entities (LLM-first): {entities}")
        else:
            # Fallback to regex-only if LLM fails
            entities = regex_entities
            confidence = self._calculate_confidence(query, entities)
            logger.info(f"   ⚠️ Using regex-only (LLM failed)")

        # Step 4: Validation (optional)
        if getattr(config, 'LLM_FIRST_VALIDATION', True):
            entities = self._validate_with_regex(query, entities)

        return entities, confidence

    def _extract_with_regex(self, query: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns (EXPANDED for all entity types)"""
        entities = {
            "Error": [],
            "Topic": [],
            "Action": [],
            "Status": [],
            "Fee": [],
            "Limit": [],
            "Requirement": [],
            "Feature": [],
            "UIElement": [],
            "TimeFrame": [],
            "Document": [],
            "AccountType": [],
            "ContactChannel": [],
            "Service": [],
            "Bank": []
        }

        query_lower = query.lower()

        # Check error regex patterns
        for pattern, error_name in self.error_patterns_regex:
            if re.search(pattern, query_lower):
                if error_name not in entities["Error"]:
                    entities["Error"].append(error_name)

        # Check topic regex patterns
        for pattern, topic_name in self.topic_patterns_regex:
            if re.search(pattern, query_lower):
                if topic_name not in entities["Topic"]:
                    entities["Topic"].append(topic_name)

        # Check action regex patterns (NEW!)
        for pattern, action_name in self.action_patterns_regex:
            if re.search(pattern, query_lower):
                if action_name not in entities["Action"]:
                    entities["Action"].append(action_name)

        # Check status regex patterns (NEW!)
        for pattern, status_name in self.status_patterns_regex:
            if re.search(pattern, query_lower):
                if status_name not in entities["Status"]:
                    entities["Status"].append(status_name)

        # Check fee regex patterns (NEW! - IMPORTANT)
        for pattern, fee_name in self.fee_patterns_regex:
            if re.search(pattern, query_lower):
                if fee_name not in entities["Fee"]:
                    entities["Fee"].append(fee_name)

        # Check limit regex patterns (NEW!)
        for pattern, limit_name in self.limit_patterns_regex:
            if re.search(pattern, query_lower):
                if limit_name not in entities["Limit"]:
                    entities["Limit"].append(limit_name)

        # Check requirement regex patterns (NEW! - PRIORITY 1)
        for pattern, requirement_name in self.requirement_patterns_regex:
            if re.search(pattern, query_lower):
                if requirement_name not in entities["Requirement"]:
                    entities["Requirement"].append(requirement_name)

        # Check feature regex patterns (NEW! - PRIORITY 1)
        for pattern, feature_name in self.feature_patterns_regex:
            if re.search(pattern, query_lower):
                if feature_name not in entities["Feature"]:
                    entities["Feature"].append(feature_name)

        # Check UI element regex patterns (NEW! - PRIORITY 1 - CRITICAL!)
        for pattern, ui_name in self.ui_element_patterns_regex:
            if re.search(pattern, query_lower):
                if ui_name not in entities["UIElement"]:
                    entities["UIElement"].append(ui_name)

        # Check timeframe regex patterns (NEW! - PRIORITY 2)
        for pattern, timeframe_name in self.timeframe_patterns_regex:
            if re.search(pattern, query_lower):
                if timeframe_name not in entities["TimeFrame"]:
                    entities["TimeFrame"].append(timeframe_name)

        # Check document regex patterns (NEW! - PRIORITY 2)
        for pattern, document_name in self.document_patterns_regex:
            if re.search(pattern, query_lower):
                if document_name not in entities["Document"]:
                    entities["Document"].append(document_name)

        # Check account type regex patterns (NEW! - PRIORITY 2)
        for pattern, account_type_name in self.account_type_patterns_regex:
            if re.search(pattern, query_lower):
                if account_type_name not in entities["AccountType"]:
                    entities["AccountType"].append(account_type_name)

        # Check contact channel regex patterns (NEW! - PRIORITY 3)
        for pattern, channel_name in self.contact_channel_patterns_regex:
            if re.search(pattern, query_lower):
                if channel_name not in entities["ContactChannel"]:
                    entities["ContactChannel"].append(channel_name)

        # Check service regex patterns (IMPROVED!)
        for pattern, service_name in self.service_patterns_regex:
            if re.search(pattern, query_lower):
                if service_name not in entities["Service"]:
                    entities["Service"].append(service_name)

        # Check bank regex patterns (IMPROVED!)
        for pattern, bank_name in self.bank_patterns_regex:
            if re.search(pattern, query_lower):
                if bank_name not in entities["Bank"]:
                    entities["Bank"].append(bank_name)

        return entities

    def _merge_entities(
        self,
        entities1: Dict[str, List[str]],
        entities2: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Merge two entity dicts"""
        merged = entities1.copy()

        for entity_type, values in entities2.items():
            if entity_type not in merged:
                merged[entity_type] = []

            for value in values:
                if value not in merged[entity_type]:
                    merged[entity_type].append(value)

        return merged

    def _apply_contextual_rules(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Apply contextual rules to improve extraction"""
        query_lower = query.lower()

        for (keyword1, keyword2), (entity_type, entity_value) in self.contextual_rules.items():
            if keyword1 in query_lower and keyword2 in query_lower:
                if entity_type not in entities:
                    entities[entity_type] = []
                if entity_value not in entities[entity_type]:
                    entities[entity_type].append(entity_value)

        return entities

    def _validate_entities(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Validate and auto-correct entities"""
        query_lower = query.lower()

        # Rule: Nếu có "mở khóa" → xóa "Khóa tài khoản" (vì "mở khóa" ưu tiên hơn "khóa")
        if "mở khóa" in query_lower and "Mở khóa tài khoản" in entities.get("Topic", []):
            if "Khóa tài khoản" in entities.get("Topic", []):
                entities["Topic"].remove("Khóa tài khoản")

        # Rule: Nếu có "khóa" nhưng KHÔNG có "mở" → có thể là "khóa tài khoản"
        # (logic này đã được xử lý bởi pattern matching)

        # Rule: Nếu query có "chuyển tiền" mà không có Topic, thêm vào
        if "chuyển tiền" in query_lower or "chuyển khoản" in query_lower:
            if "Chuyển tiền" not in entities.get("Topic", []):
                if "Topic" not in entities:
                    entities["Topic"] = []
                entities["Topic"].append("Chuyển tiền")

        # Rule: Nếu query có "nạp tiền" mà không có Topic, thêm vào
        # CRITICAL FIX: Only add generic "Nạp tiền" if no specific "nạp tiền" topic exists
        if "nạp tiền" in query_lower or "nạp" in query_lower:
            existing_topics = entities.get("Topic", [])
            # Check if any existing topic already contains "nạp tiền" (more specific)
            has_specific_nap_tien = any("nạp tiền" in t.lower() or "nạp" in t.lower()
                                       for t in existing_topics if t != "Nạp tiền")

            # Debug log
            if has_specific_nap_tien:
                logger.debug(f"   Skipping generic 'Nạp tiền' - found specific topic: {existing_topics}")

            if not has_specific_nap_tien and "Nạp tiền" not in existing_topics:
                if "Topic" not in entities:
                    entities["Topic"] = []
                entities["Topic"].append("Nạp tiền")

        # Rule: Nếu query có "sinh trắc học" hoặc "ekyc" mà không có Topic, thêm vào
        if ("sinh trắc" in query_lower or "ekyc" in query_lower) and "Sinh trắc học" not in entities.get("Topic", []):
            if "Topic" not in entities:
                entities["Topic"] = []
            entities["Topic"].append("Sinh trắc học")

        # Rule: Nếu query có "đổi mật khẩu" / "thay đổi mật khẩu" mà không có Topic, thêm vào
        if ("đổi mật khẩu" in query_lower or "thay đổi mật khẩu" in query_lower or "đặt lại mật khẩu" in query_lower) and "Đổi mật khẩu" not in entities.get("Topic", []):
            if "Topic" not in entities:
                entities["Topic"] = []
            entities["Topic"].append("Đổi mật khẩu")

        # Rule: Nếu có error về "chưa nhận được" + có "chuyển tiền"
        # → Đảm bảo có Topic "Chuyển tiền"
        if entities.get("Error"):
            for error in entities["Error"]:
                if "chưa nhận" in error.lower() and "chuyển" in query_lower:
                    if "Topic" not in entities:
                        entities["Topic"] = []
                    if "Chuyển tiền" not in entities["Topic"]:
                        entities["Topic"].append("Chuyển tiền")
                # Rule: Nếu có error về sinh trắc → Đảm bảo có Topic "Sinh trắc học"
                if ("sinh trắc" in error.lower() or "ekyc" in error.lower() or "ngày sinh" in error.lower() or "định danh" in error.lower()):
                    if "Topic" not in entities:
                        entities["Topic"] = []
                    if "Sinh trắc học" not in entities["Topic"]:
                        entities["Topic"].append("Sinh trắc học")

        return entities

    def _calculate_confidence(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> float:
        """
        Calculate confidence score (0.0 - 1.0)

        Scoring:
        - Error found: +0.4
        - Topic found: +0.3
        - Service found: +0.2
        - Multiple entities: +0.1
        """
        confidence = 0.0

        # Error entities are most important for troubleshooting
        if entities.get("Error"):
            confidence += 0.4

        # Topic helps narrow down
        if entities.get("Topic"):
            confidence += 0.3

        # Service provides context
        if entities.get("Service"):
            confidence += 0.2

        # Multiple entities = higher confidence
        total_entities = sum(len(v) for v in entities.values() if isinstance(v, list))
        if total_entities >= 3:
            confidence += 0.1

        return min(confidence, 1.0)  # Cap at 1.0

    def _should_use_llm_fallback(
        self,
        query: str,
        entities: Dict[str, List[str]],
        confidence: float
    ) -> Tuple[bool, str]:
        """
        Determine if LLM fallback is needed

        Returns:
            (should_use_llm: bool, reason: str)
        """
        import config

        query_lower = query.lower()

        # Trigger 1: Low confidence
        if confidence < config.LLM_FALLBACK_THRESHOLD:
            return True, f"low_confidence ({confidence:.2%} < {config.LLM_FALLBACK_THRESHOLD:.2%})"

        # Trigger 2: Question keywords but no relevant answer entities
        if config.LLM_FALLBACK_FOR_QUESTIONS:
            if self._is_question_query(query) and not self._has_answer_entities(entities):
                return True, "question_without_answer_entities"

        # Trigger 3: Ambiguous queries
        if config.LLM_FALLBACK_FOR_AMBIGUOUS:
            if self._is_ambiguous(query, entities):
                return True, "ambiguous_query"

        # Trigger 4: Critical entities missing
        if self._missing_critical_entities(query, entities):
            return True, "missing_critical_entities"

        return False, "pattern_sufficient"

    def _is_question_query(self, query: str) -> bool:
        """Check if query is asking a question"""
        question_keywords = [
            "như thế nào", "làm sao", "thế nào",
            "bao nhiêu", "là gì", "tại sao", "khi nào",
            "ở đâu", "ai", "có", "phải", "được"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in question_keywords)

    def _has_answer_entities(self, entities: Dict) -> bool:
        """Check if we extracted answer-relevant entities"""
        # Has action, fee, limit, or error entities
        answer_entity_types = ["Action", "Fee", "Limit", "Error", "Status"]
        return any(entities.get(entity_type) for entity_type in answer_entity_types)

    def _is_ambiguous(self, query: str, entities: Dict) -> bool:
        """Check if query/entities are ambiguous"""
        query_lower = query.lower()

        # "hủy" without specific action
        if "hủy" in query_lower and not entities.get("Action"):
            return True

        # Generic pronouns without context
        generic_words = ["này", "đó", "kia", "ấy"]
        if any(w in query_lower for w in generic_words):
            if len(entities.get("Action", [])) == 0 and len(entities.get("Topic", [])) == 0:
                return True

        return False

    def _missing_critical_entities(self, query: str, entities: Dict) -> bool:
        """Check if critical entities are missing"""
        query_lower = query.lower()

        # Query mentions fee but Fee not extracted
        fee_keywords = ["phí", "bao nhiêu", "tốn", "chi phí", "mất tiền"]
        if any(kw in query_lower for kw in fee_keywords):
            if not entities.get("Fee"):
                return True

        # Query mentions limit but Limit not extracted
        limit_keywords = ["hạn mức", "tối đa", "giới hạn", "tối thiểu"]
        if any(kw in query_lower for kw in limit_keywords):
            if not entities.get("Limit"):
                return True

        # Query mentions action verbs but Action not extracted
        action_keywords = ["làm", "thực hiện", "tiến hành", "xử lý"]
        if any(kw in query_lower for kw in action_keywords):
            if not entities.get("Action"):
                return True

        return False

    def _extract_with_llm(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities using LLM (same prompt as document extraction)

        Returns:
            Dictionary of entities
        """
        try:
            from llm_entity_extractor import LLMEntityExtractor

            # Initialize LLM extractor (reuse existing instance if possible)
            if not hasattr(self, '_llm_extractor'):
                self._llm_extractor = LLMEntityExtractor()

            # Extract using same method as document extraction
            result = self._llm_extractor.extract_entities_and_relationships(
                question=query,
                answer="",  # Empty for query extraction
                section=""  # Empty for query
            )

            # Return only entities (ignore relationships for query extraction)
            return result.get("entities", {})

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}

    def _merge_llm_results(
        self,
        pattern_entities: Dict[str, List[str]],
        llm_entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Merge pattern and LLM results (LLM takes priority)

        Strategy:
        - Keep all LLM entities (they are more accurate)
        - Add pattern entities that LLM didn't find
        - Remove duplicates
        """
        merged = {}

        # Get all entity types from both
        all_types = set(pattern_entities.keys()) | set(llm_entities.keys())

        for entity_type in all_types:
            # Skip special flags
            if entity_type == "out_of_scope":
                merged[entity_type] = pattern_entities.get(entity_type, False)
                continue

            # Start with LLM entities (higher priority)
            llm_vals = llm_entities.get(entity_type, [])
            pattern_vals = pattern_entities.get(entity_type, [])

            # Combine and deduplicate (case-insensitive)
            combined = list(llm_vals)  # Start with LLM

            for pv in pattern_vals:
                # Add pattern value if not already in LLM results
                # CRITICAL FIX: Also skip if pattern value is a substring of any LLM value
                # (e.g., don't add "Nạp tiền" if LLM found "Hủy dịch vụ nạp tiền tự động")
                is_duplicate = any(pv.lower() == lv.lower() for lv in llm_vals)
                is_substring = any(pv.lower() in lv.lower() for lv in llm_vals if len(pv) < len(lv))

                if not is_duplicate and not is_substring:
                    combined.append(pv)

            merged[entity_type] = combined

        return merged

    def _merge_llm_priority(
        self,
        llm_entities: Dict[str, List[str]],
        regex_entities: Dict[str, List[str]],
        llm_weight: float = 0.8
    ) -> Dict[str, List[str]]:
        """
        Merge LLM and Regex results with LLM priority (for LLM-First strategy)

        Strategy (80% LLM, 20% Regex):
        - Take all LLM entities (PRIMARY source)
        - Add regex entities only if:
          1. LLM didn't extract that entity type
          2. Regex entity is factual (Bank, Document, Error, Status)
          3. Regex entity provides additional specific detail
        """
        merged = {}

        # Get all entity types
        all_types = set(llm_entities.keys()) | set(regex_entities.keys())

        for entity_type in all_types:
            llm_vals = llm_entities.get(entity_type, [])
            regex_vals = regex_entities.get(entity_type, [])

            # Priority 1: Start with all LLM values (always include)
            merged[entity_type] = llm_vals.copy()

            # Priority 2: Add regex values selectively
            # High-value factual entity types - trust regex
            if entity_type in ['Bank', 'Document', 'Error', 'Status', 'Fee', 'Limit']:
                for rv in regex_vals:
                    if rv not in merged[entity_type]:
                        merged[entity_type].append(rv)

            # If LLM missed entirely, use regex
            elif not llm_vals and regex_vals:
                merged[entity_type].extend(regex_vals)

            # If regex provides more specific detail, add it
            elif regex_vals:
                for rv in regex_vals:
                    # Check if regex value is more specific than LLM value
                    is_more_specific = any(
                        len(rv) > len(lv) and lv.lower() in rv.lower()
                        for lv in llm_vals
                    )
                    # Or if it's completely different valuable info
                    is_different = not any(
                        rv.lower() in lv.lower() or lv.lower() in rv.lower()
                        for lv in llm_vals
                    )

                    if (is_more_specific or is_different) and rv not in merged[entity_type]:
                        merged[entity_type].append(rv)

        return merged

    def _validate_with_regex(
        self,
        query: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Validate LLM-extracted entities using regex patterns

        Strategy:
        - Remove LLM entities that don't appear in query text (hallucinations)
        - Validate factual entities (Bank, Document) against known patterns
        - Keep semantic entities (Topic, Action) as-is (LLM can infer these)
        """
        validated = {}

        query_lower = query.lower()

        for entity_type, values in entities.items():
            validated[entity_type] = []

            for value in values:
                # Skip validation for semantic entity types (LLM can infer)
                if entity_type in ['Topic', 'Action', 'Requirement', 'Service']:
                    # For these, LLM inference is acceptable
                    # But still check if it's too far from query
                    value_words = set(value.lower().split())
                    query_words = set(query_lower.split())
                    overlap = len(value_words & query_words)

                    # Accept if at least 30% overlap or very short (1-2 words)
                    if overlap > 0 or len(value_words) <= 2:
                        validated[entity_type].append(value)
                    else:
                        logger.warning(f"   ⚠️ Filtered LLM entity (no overlap): {entity_type}={value}")

                # Strict validation for factual entities
                elif entity_type in ['Bank', 'Document', 'Error']:
                    # Must appear in query text
                    if value.lower() in query_lower:
                        validated[entity_type].append(value)
                    else:
                        logger.warning(f"   ⚠️ Filtered LLM entity (not in query): {entity_type}={value}")

                # Moderate validation for others
                else:
                    # Check if at least one word appears
                    value_words = value.lower().split()
                    if any(word in query_lower for word in value_words):
                        validated[entity_type].append(value)
                    else:
                        logger.warning(f"   ⚠️ Filtered LLM entity (no words match): {entity_type}={value}")

        return validated


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    extractor = EnhancedEntityExtractor()

    test_queries = [
        "Tôi thực hiện giao dịch chuyển tiền đến ngân hàng nhưng tài khoản thụ hưởng chưa nhận được thì phải làm thế nào?",
        "Chuyển tiền rồi mà tiền chưa về",
        "Giao dịch nạp tiền thất bại",
        "Làm sao để chuyển tiền đến Vietinbank?",
        "Không nhận được OTP khi chuyển tiền",
        "Tài khoản không hợp lệ",
    ]

    print("=" * 80)
    print("ENHANCED ENTITY EXTRACTOR TEST")
    print("=" * 80)

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")

        # Extract with confidence
        entities, confidence = extractor.extract_with_confidence(query)

        print(f"\n📊 Confidence: {confidence:.2%}")

        print("\n📌 Extracted Entities:")
        for entity_type, values in entities.items():
            if values and entity_type != 'out_of_scope':
                print(f"  {entity_type}: {values}")

        # Interpretation
        print(f"\n💡 Interpretation:")
        if confidence >= 0.7:
            print("  ✅ HIGH confidence - Extraction is reliable")
        elif confidence >= 0.4:
            print("  🟡 MEDIUM confidence - May need fallback")
        else:
            print("  ⚠️  LOW confidence - Consider using LLM fallback")

        if entities.get("Error"):
            print("  🔧 Detected as TROUBLESHOOTING query")
        elif entities.get("Topic") and not entities.get("Error"):
            print("  📖 Detected as HOW-TO or INFO query")
