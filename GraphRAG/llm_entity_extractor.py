"""
LLM-based Entity and Relationship Extractor for VNPT Money Chatbot
Uses LLM (OpenAI ChatGPT or Google Gemini) to extract entities and relationships from FAQ documents
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMEntityExtractor:
    """Extract entities and relationships using LLM (OpenAI ChatGPT or Google Gemini)"""

    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize LLM Entity Extractor

        Args:
            provider: LLM provider ("openai" or "gemini", defaults to config.LLM_PROVIDER)
            api_key: API key for the LLM provider (defaults to config)
        """
        self.provider = provider or config.LLM_PROVIDER

        if self.provider == "openai":
            self._init_openai(api_key)
        elif self.provider == "gemini":
            self._init_gemini(api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use 'openai' or 'gemini'")

        logger.info(f"Initialized LLM Entity Extractor with {self.provider} ({config.LLM_MODEL})")

    def _init_openai(self, api_key: Optional[str] = None):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

        self.api_key = api_key or config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = config.LLM_MODEL

    def _init_gemini(self, api_key: Optional[str] = None):
        """Initialize Google Gemini client"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Google Generative AI package not installed. Run: pip install google-generativeai")

        self.api_key = api_key or config.GOOGLE_API_KEY
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY in .env file")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=config.LLM_MODEL,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        self.model_name = config.LLM_MODEL

    def extract_entities_and_relationships(
        self,
        question: str,
        answer: str,
        section: str = ""
    ) -> Dict:
        """
        Extract entities and relationships from question and answer using LLM

        Args:
            question: FAQ question text
            answer: FAQ answer text
            section: Section/category of the FAQ

        Returns:
            Dictionary containing:
            - entities: Dict of entity types and their instances
            - relationships: List of relationships between entities
        """
        prompt = self._build_extraction_prompt(question, answer, section)

        try:
            if self.provider == "openai":
                response_text = self._call_openai(prompt)
            else:  # gemini
                response_text = self._call_gemini(prompt)

            result = self._parse_llm_response(response_text)
            return result
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
            return self._get_empty_result()

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert in analyzing Vietnamese text and extracting structured information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2048
        )
        return response.choices[0].message.content

    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API"""
        response = self.model.generate_content(prompt)
        return response.text

    def _build_extraction_prompt(self, question: str, answer: str, section: str = "") -> str:
        """
        Build prompt for LLM to extract entities and relationships

        Args:
            question: FAQ question
            answer: FAQ answer
            section: Section name

        Returns:
            Formatted prompt string
        """
        prompt = f"""Bạn là một chuyên gia phân tích văn bản tiếng Việt. Nhiệm vụ của bạn là trích xuất các thực thể (entities) và mối quan hệ (relationships) từ cặp câu hỏi-trả lời về dịch vụ VNPT Money.

**ĐỊNH NGHĨA CÁC LOẠI THỰC THỂ:**

1. **Topic**: Chủ đề chính của câu hỏi
   - Ví dụ: "Nạp tiền", "Rút tiền", "Liên kết ngân hàng", "Chuyển tiền", "OTP", "Sinh trắc học", "Định danh"

2. **Service**: Dịch vụ được đề cập
   - Ví dụ: "VNPT Money", "VNPT Pay", "Mobile Banking", "Internet Banking"

3. **Bank**: Tên ngân hàng cụ thể
   - Ví dụ: "Vietinbank", "Vietcombank", "BIDV", "Techcombank", "ACB", "VPBank"

4. **Error**: Thông báo lỗi hoặc vấn đề
   - Ví dụ: "thông tin thẻ/tài khoản không hợp lệ", "Không nhận được OTP", "Quá hạn mức"
   - **LƯU Ý**: Ưu tiên lấy text trong dấu ngoặc kép "", nếu không có thì lấy toàn bộ mô tả lỗi

5. **Action**: Hành động mà người dùng cần thực hiện (các bước cụ thể trong UI)
   - Ví dụ: "Chọn Cá nhân", "Nhập số tiền", "Nhấn Xác nhận", "Chọn ngân hàng", "Nhập OTP"
   - **LƯU Ý**: Với hướng dẫn từng bước, tách mỗi bước thành một Action riêng
   - **PHÂN BIỆT với Feature**: Action là thao tác UI cụ thể, Feature là phương thức/tính năng của hệ thống

6. **Requirement**: Điều kiện cần thiết để thực hiện hành động
   - Ví dụ: "Đăng ký dịch vụ thanh toán trực tuyến", "Có số dư tối thiểu", "Thông tin trùng khớp"

7. **Feature**: Tính năng/công cụ/phương thức của ứng dụng (KHÔNG phải hành động người dùng)
   - Ví dụ công cụ/tính năng: "QR đa năng", "OTP", "Tra soát giao dịch", "Lịch sử giao dịch", "NFC", "Sinh trắc học"
   - **QUAN TRỌNG**: Bao gồm cả **phương thức thanh toán/giao dịch cụ thể**:
     * "ngân hàng liên kết", "liên kết ngân hàng", "tài khoản liên kết" (phương thức nạp/rút từ tài khoản bank đã liên kết)
     * "QR code", "mã QR", "QR đa năng" (phương thức thanh toán bằng quét mã)
     * "Chuyển khoản ngân hàng" (phương thức chuyển tiền qua bank - KHÔNG PHẢI qua liên kết)
     * "ví điện tử", "tài khoản ví" (phương thức thanh toán qua ví)
   - **NHẬN DIỆN Feature trong câu** (QUAN TRỌNG - ƯU TIÊN):
     * **LUÔN LUÔN** extract Feature nếu có từ "bằng", "qua", "thông qua", "bằng cách", "sử dụng" + phương thức
     * Ví dụ: "nạp tiền **bằng chuyển khoản ngân hàng**" → Feature: "Chuyển khoản ngân hàng" (KHÔNG phải Action!)
     * Ví dụ: "thực hiện **bằng tài khoản liên kết**" → Feature: "liên kết ngân hàng"
     * Ví dụ: "thanh toán **qua** QR" → Feature: "QR code"
     * **LƯU Ý**: Khi có "bằng/qua/thông qua", text sau nó là Feature, KHÔNG phải Action
   - **PHÂN BIỆT**:
     * Feature = Phương thức/tính năng (vd: "ngân hàng liên kết", "QR code", "Chuyển khoản ngân hàng")
     * Action = Thao tác UI (vd: "Chọn ngân hàng", "Nhập số tiền", "Nhấn Xác nhận")
   - **Mục đích**: Giúp phân biệt các phương thức khác nhau trong cùng 1 dịch vụ
     * "nạp tiền **bằng liên kết** ngân hàng" → Feature: "liên kết ngân hàng"
     * "nạp tiền **bằng chuyển khoản** ngân hàng" → Feature: "Chuyển khoản ngân hàng"

8. **TimeFrame**: Khung thời gian liên quan
   - Ví dụ: "2 ngày làm việc", "3 ngày làm việc", "45-60 ngày làm việc", "Ngay lập tức"
   - **LƯU Ý**: Chuẩn hóa bằng cách loại bỏ ghi chú trong ngoặc như "(không tính thứ 7, CN và Lễ)"

9. **Status**: Trạng thái của giao dịch hoặc tài khoản
   - Ví dụ: "Thành công", "Đang xử lý", "Thất bại", "Chưa kích hoạt", "Đã kích hoạt"

10. **Document**: Loại giấy tờ định danh
    - Ví dụ: "CCCD", "CMND", "Hộ chiếu", "CCCD gắn chíp", "Giấy tờ"

11. **AccountType**: Loại tài khoản
    - Ví dụ: "Tài khoản ví", "Tài khoản ngân hàng", "Thẻ nội địa", "Số tài khoản", "Số thẻ"

12. **UIElement**: Phần tử giao diện người dùng (menu, button, screen)
    - Ví dụ: "Cá nhân", "Ngân hàng liên kết", "Chuyển tiền", "Trợ giúp", "Qua số tài khoản/số thẻ"

13. **ContactChannel**: Kênh liên hệ hỗ trợ
    - Ví dụ: "Trợ giúp", "Hotline", "Bộ phận hỗ trợ ngân hàng", "Bộ phận chăm sóc khách hàng"
    - **Bao gồm cả số điện thoại cụ thể của nhà mạng/ngân hàng**:
      * "Vinaphone: 18001091", "Mobifone: 18001090", "Viettel: 18008098"
      * Format: "<Tên nhà mạng/ngân hàng>: <Số điện thoại>"
    - **Khi câu hỏi hỏi về số điện thoại/hotline của một nhà mạng cụ thể**, extract tên nhà mạng đó với số điện thoại

14. **Fee**: Phí, chi phí, biểu phí, chính sách phí liên quan đến giao dịch/dịch vụ
    - Ví dụ: "phí rút tiền", "phí chuyển tiền", "phí dịch vụ", "biểu phí VNPT Money"

15. **Limit**: Hạn mức, giới hạn số tiền/số lần giao dịch
    - Ví dụ: "số tiền tối đa trong ngày", "hạn mức thanh toán theo ngày", "số lần rút tiền miễn phí trong tháng"

**ĐỊNH NGHĨA CÁC LOẠI MỐI QUAN HỆ:**

1. **ABOUT**: Câu hỏi về chủ đề gì
   - Format: (Question) -[ABOUT]-> (Topic)

2. **MENTIONS_SERVICE**: Đề cập đến dịch vụ
   - Format: (Question/Answer) -[MENTIONS_SERVICE]-> (Service)

3. **MENTIONS_BANK**: Đề cập đến ngân hàng
   - Format: (Question/Answer) -[MENTIONS_BANK]-> (Bank)

4. **DESCRIBES_ERROR**: Câu hỏi mô tả lỗi
   - Format: (Question) -[DESCRIBES_ERROR]-> (Error)

5. **SUGGESTS_ACTION**: Câu trả lời gợi ý hành động
   - Format: (Answer) -[SUGGESTS_ACTION]-> (Action)

6. **REQUIRES**: Hành động yêu cầu điều kiện
   - Format: (Action) -[REQUIRES]-> (Requirement)

7. **USES_FEATURE**: Hành động sử dụng tính năng
   - Format: (Action) -[USES_FEATURE]-> (Feature)

8. **SOLVES**: Câu trả lời giải quyết lỗi
   - Format: (Answer) -[SOLVES]-> (Error)

9. **HAS_TIMEFRAME**: Hành động có khung thời gian
   - Format: (Action) -[HAS_TIMEFRAME]-> (TimeFrame)

10. **RELATED_TO_TOPIC**: Chủ đề liên quan đến chủ đề khác
    - Format: (Topic) -[RELATED_TO_TOPIC]-> (Topic)

11. **HAS_STATUS**: Giao dịch hoặc tài khoản có trạng thái
    - Format: (Action/AccountType) -[HAS_STATUS]-> (Status)

12. **REQUIRES_DOCUMENT**: Hành động yêu cầu giấy tờ
    - Format: (Action) -[REQUIRES_DOCUMENT]-> (Document)

13. **NEXT_STEP**: Bước tiếp theo trong quy trình
    - Format: (Action) -[NEXT_STEP]-> (Action)

14. **NAVIGATES_TO**: Điều hướng đến phần tử UI
    - Format: (Action) -[NAVIGATES_TO]-> (UIElement)

15. **CONTACTS**: Liên hệ qua kênh
    - Format: (Action) -[CONTACTS]-> (ContactChannel)

16. **AFFECTS_ACCOUNT**: Hành động ảnh hưởng đến loại tài khoản
    - Format: (Action) -[AFFECTS_ACCOUNT]-> (AccountType)

**DỮ LIỆU ĐẦU VÀO:**

Section: {section if section else "Không xác định"}

Câu hỏi: {question}

Câu trả lời: {answer}

**YÊU CẦU CHI TIẾT:**

1. **Trích xuất Entities:**
   - Trích xuất TẤT CẢ các thực thể thuộc các loại trên từ câu hỏi và câu trả lời
   - Chuẩn hóa tên thực thể (viết hoa đúng, loại bỏ khoảng trắng thừa)
   - Với Error, ưu tiên lấy text trong dấu ngoặc kép ""
   - Với TimeFrame, loại bỏ ghi chú trong ngoặc đơn ()
   - Với Action trong hướng dẫn từng bước (Bước 1, Bước 2...), tách mỗi bước thành Action riêng

2. **Xử lý Hướng dẫn Từng Bước:**
   - Khi câu trả lời có "Bước 1:", "Bước 2:", etc.
   - Trích xuất mỗi bước thành một Action riêng
   - Tạo relationship NEXT_STEP giữa các bước liên tiếp
   - Nếu bước đề cập UI element (menu/button), tạo UIElement và relationship NAVIGATES_TO

   Ví dụ:
   Input: "Bước 1: Chọn 'Cá nhân'. Bước 2: Chọn 'Ngân hàng liên kết'"
   Output:
   - Action: ["Chọn Cá nhân", "Chọn Ngân hàng liên kết"]
   - UIElement: ["Cá nhân", "Ngân hàng liên kết"]
   - Relationships:
     * (Answer) -[SUGGESTS_ACTION]-> (Chọn Cá nhân)
     * (Chọn Cá nhân) -[NEXT_STEP]-> (Chọn Ngân hàng liên kết)
     * (Chọn Cá nhân) -[NAVIGATES_TO]-> (Cá nhân)
     * (Chọn Ngân hàng liên kết) -[NAVIGATES_TO]-> (Ngân hàng liên kết)

3. **Xử lý Trạng thái:**
   - Khi câu trả lời đề cập "Trạng thái", "trạng thái", status
   - Trích xuất Status entity
   - Tạo relationship HAS_STATUS

   Ví dụ:
   Input: "Giao dịch có trạng thái 'Đang xử lý'"
   Output:
   - Action: ["Giao dịch"]
   - Status: ["Đang xử lý"]
   - Relationship: (Giao dịch) -[HAS_STATUS]-> (Đang xử lý)

4. **Xử lý Giấy tờ:**
   - Khi câu trả lời yêu cầu CCCD, CMND, Hộ chiếu, etc.
   - Trích xuất Document entity
   - Tạo relationship REQUIRES_DOCUMENT

   Ví dụ:
   Input: "Bạn cần cung cấp CCCD gắn chíp để định danh"
   Output:
   - Action: ["Định danh"]
   - Document: ["CCCD gắn chíp"]
   - Relationship: (Định danh) -[REQUIRES_DOCUMENT]-> (CCCD gắn chíp)

5. **Xác định Relationships:**
   - Tạo relationships giữa các entities đã trích xuất
   - Đảm bảo relationships chính xác và có ý nghĩa
   - Với hướng dẫn từng bước, nhớ tạo NEXT_STEP giữa các Action

**FORMAT ĐẦU RA (JSON):**

Trả về ĐÚNG format JSON sau (không thêm markdown, chỉ JSON thuần túy):

{{
  "entities": {{
    "Topic": ["tên topic 1", "tên topic 2"],
    "Service": ["tên service 1"],
    "Bank": ["tên bank 1"],
    "Error": ["thông báo lỗi đầy đủ"],
    "Action": ["hành động 1", "hành động 2"],
    "Requirement": ["điều kiện 1"],
    "Feature": ["tính năng 1"],
    "TimeFrame": ["khung thời gian"],
    "Status": ["trạng thái 1"],
    "Document": ["loại giấy tờ"],
    "AccountType": ["loại tài khoản"],
    "UIElement": ["phần tử UI"],
    "ContactChannel": ["kênh liên hệ"],
    "Fee": ["thông tin phí hoặc tên loại phí"],
    "Limit": ["mô tả hạn mức hoặc giới hạn"]
  }},
  "relationships": [
    {{"from": "Question", "relation": "ABOUT", "to": "tên topic", "to_type": "Topic"}},
    {{"from": "Question", "relation": "MENTIONS_SERVICE", "to": "tên service", "to_type": "Service"}},
    {{"from": "Question", "relation": "DESCRIBES_ERROR", "to": "thông báo lỗi", "to_type": "Error"}},
    {{"from": "Answer", "relation": "SUGGESTS_ACTION", "to": "hành động", "to_type": "Action"}},
    {{"from": "Answer", "relation": "SOLVES", "to": "thông báo lỗi", "to_type": "Error"}},
    {{"from": "hành động", "relation": "REQUIRES", "to": "điều kiện", "to_type": "Requirement"}},
    {{"from": "hành động", "relation": "USES_FEATURE", "to": "tính năng", "to_type": "Feature"}},
    {{"from": "hành động", "relation": "HAS_TIMEFRAME", "to": "khung thời gian", "to_type": "TimeFrame"}},
    {{"from": "hành động 1", "relation": "NEXT_STEP", "to": "hành động 2", "to_type": "Action"}},
    {{"from": "hành động", "relation": "NAVIGATES_TO", "to": "phần tử UI", "to_type": "UIElement"}},
    {{"from": "giao dịch", "relation": "HAS_STATUS", "to": "trạng thái", "to_type": "Status"}},
    {{"from": "hành động", "relation": "REQUIRES_DOCUMENT", "to": "giấy tờ", "to_type": "Document"}},
    {{"from": "hành động", "relation": "CONTACTS", "to": "kênh liên hệ", "to_type": "ContactChannel"}},
    {{"from": "hành động", "relation": "AFFECTS_ACCOUNT", "to": "loại tài khoản", "to_type": "AccountType"}},
    {{"from": "hành động hoặc dịch vụ", "relation": "HAS_FEE", "to": "thông tin phí", "to_type": "Fee"}},
    {{"from": "hành động hoặc dịch vụ", "relation": "HAS_LIMIT", "to": "hạn mức", "to_type": "Limit"}}
  ]
}}

**LƯU Ý QUAN TRỌNG:**
- Chỉ trả về JSON, KHÔNG thêm bất kỳ text nào khác
- Nếu không tìm thấy thực thể nào của một loại, trả về danh sách rỗng []
- Tên thực thể phải chính xác và đầy đủ
- Relationships phải liên kết đúng với entities đã trích xuất
- Với hướng dẫn từng bước, nhớ tạo NEXT_STEP relationships
- TimeFrame phải được chuẩn hóa (loại bỏ ghi chú trong ngoặc)
- Error ưu tiên lấy text trong dấu ngoặc kép
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict:
        """
        Parse LLM response to extract entities and relationships

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed entities and relationships
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            result = json.loads(response_text)

            # Validate structure
            if "entities" not in result or "relationships" not in result:
                logger.warning("Invalid LLM response structure")
                return self._get_empty_result()

            # Clean and validate entities
            entities = result.get("entities", {})
            for entity_type in entities:
                if not isinstance(entities[entity_type], list):
                    entities[entity_type] = []
                # Remove empty strings and duplicates
                entities[entity_type] = list(set([
                    e.strip() for e in entities[entity_type]
                    if e and isinstance(e, str) and e.strip()
                ]))

            # Clean and validate relationships
            relationships = result.get("relationships", [])
            validated_relationships = []
            for rel in relationships:
                if all(k in rel for k in ["from", "relation", "to", "to_type"]):
                    validated_relationships.append({
                        "from": str(rel["from"]).strip(),
                        "relation": str(rel["relation"]).strip(),
                        "to": str(rel["to"]).strip(),
                        "to_type": str(rel["to_type"]).strip()
                    })

            return {
                "entities": entities,
                "relationships": validated_relationships
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._get_empty_result()

    def _get_empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "entities": {
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
                "Limit": []
            },
            "relationships": []
        }

    def extract_from_document(self, document: Dict) -> Dict:
        """
        Extract entities and relationships from a complete FAQ document

        Args:
            document: Document with 'metadata' field containing question and answer

        Returns:
            Extracted entities and relationships
        """
        metadata = document.get("metadata", {})
        question = metadata.get("question", "")
        answer = metadata.get("answer", "")
        section = metadata.get("section", "")

        if not question or not answer:
            logger.warning("Document missing question or answer")
            return self._get_empty_result()

        result = self.extract_entities_and_relationships(question, answer, section)

        # Add metadata to result
        result["metadata"] = metadata

        return result


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test LLM entity extraction
    extractor = LLMEntityExtractor()

    test_question = "Tôi nạp tiền từ ngân hàng Vietinbank báo \"thông tin thẻ/tài khoản không hợp lệ\""
    test_answer = "Bạn vui lòng thực hiện hủy liên kết hiện tại và liên kết ngân hàng lại, sau đó thực hiện nạp tiền"
    test_section = "I. Nạp tiền"

    print("Testing LLM Entity Extraction...")
    print(f"Question: {test_question}")
    print(f"Answer: {test_answer}")
    print(f"Section: {test_section}")
    print("\n" + "="*60 + "\n")

    result = extractor.extract_entities_and_relationships(
        test_question,
        test_answer,
        test_section
    )

    print("Extracted Entities:")
    for entity_type, entities in result["entities"].items():
        if entities:
            print(f"\n{entity_type}:")
            for entity in entities:
                print(f"  - {entity}")

    print("\n" + "="*60 + "\n")
    print("Extracted Relationships:")
    for rel in result["relationships"]:
        print(f"  ({rel['from']}) -[{rel['relation']}]-> ({rel['to']} : {rel['to_type']})")
