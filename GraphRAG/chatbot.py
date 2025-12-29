"""
GraphRAG Chatbot for VNPT Money
Combines GraphRAG retrieval with LLM generation
NOW WITH CONVERSATION CONTEXT SUPPORT!
"""

import logging
from typing import Dict, List, Optional

from neo4j_rag_engine import Neo4jGraphRAGEngine
from conversation_context_manager import ConversationContextManager
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphRAGChatbot:
    """Chatbot that uses GraphRAG + LLM for answering questions with conversation context tracking"""

    def __init__(self):
        """Initialize chatbot with GraphRAG engine and LLM"""
        # Initialize GraphRAG engine
        self.rag_engine = Neo4jGraphRAGEngine()

        # Initialize Conversation Context Manager (NEW)
        self.context_manager = ConversationContextManager(max_history=5)
        logger.info("Conversation context manager initialized")

        # Initialize LLM
        self.llm = None
        self._initialize_llm()

        # Conversation history (legacy, now using context_manager)
        self.conversation_history = []

    def _initialize_llm(self):
        """Initialize LLM based on configuration"""
        try:
            if config.LLM_PROVIDER == "openai":
                self._initialize_openai()
            else:
                logger.warning("No LLM configured, using template responses")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            logger.warning("Falling back to template responses")

    def _initialize_openai(self):
        """Initialize OpenAI LLM"""
        try:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.llm = "openai"
            logger.info(f"OpenAI LLM initialized: {config.LLM_MODEL}")
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
            raise

    def _is_chitchat(self, message: str) -> bool:
        """Check if message is chitchat/greeting (not FAQ-related)"""
        import re

        message_lower = message.lower().strip()

        # CRITICAL FIX: Use word boundaries to prevent false positives
        # Example: "tên bạn là gì?" should match, but "Họ tên bạn không trùng" should NOT

        # Greeting patterns (use word boundaries)
        greeting_patterns = [
            r'\bxin chào\b', r'\bchào bạn\b', r'\bhello\b', r'\bhi\b',
            r'^chào\b', r'\bchào$'  # "chào" at start or end only
        ]

        # Identity question patterns (more specific)
        identity_patterns = [
            r'\bbạn là ai\b', r'\bbạn là gì\b',
            r'\btên bạn là\b', r'\btên bạn\?',  # "tên bạn là gì?" or "tên bạn?"
            r'^tên bạn\b', # Only at start of message
            r'\bai đây\b'
        ]

        # Thanks patterns
        thanks_patterns = [
            r'\bcảm ơn\b', r'\bcám ơn\b', r'\bthank\b', r'\bthanks\b'
        ]

        # Goodbye patterns
        goodbye_patterns = [
            r'\btạm biệt\b', r'\bbye\b', r'\bgoodbye\b'
        ]

        # Capability question patterns
        capability_patterns = [
            r'\bbạn làm được gì\b', r'\bbạn có thể làm gì\b', r'\bgiúp gì được\b'
        ]

        # Combine all patterns
        all_patterns = (greeting_patterns + identity_patterns + thanks_patterns +
                       goodbye_patterns + capability_patterns)

        # Check if any pattern matches
        for pattern in all_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def _handle_chitchat(self, message: str) -> str:
        """Handle chitchat/greeting messages"""
        message_lower = message.lower().strip()

        # Greetings
        if any(x in message_lower for x in ["xin chào", "chào bạn", "hello", "hi ", "chào"]):
            return "Xin chào! Tôi là VNPT Assistant, trợ lý ảo của VNPT Money. Tôi có thể giúp bạn giải đáp các thắc mắc về dịch vụ VNPT Money. Bạn cần hỗ trợ gì?"

        # Identity
        if any(x in message_lower for x in ["bạn là ai", "bạn là gì", "tên bạn", "ai đây"]):
            return "Tôi là VNPT Assistant - trợ lý ảo thông minh của VNPT Money. Tôi được thiết kế để giúp bạn giải đáp các câu hỏi về dịch vụ ví điện tử VNPT Money, bao gồm: nạp tiền, rút tiền, chuyển tiền, liên kết ngân hàng và các tính năng khác. Bạn có câu hỏi gì về VNPT Money không?"

        # Thanks
        if any(x in message_lower for x in ["cảm ơn", "cám ơn", "thank"]):
            return "Rất vui được hỗ trợ bạn! Nếu có thêm câu hỏi, đừng ngại hỏi tôi nhé!"

        # Goodbyes
        if any(x in message_lower for x in ["tạm biệt", "bye", "goodbye"]):
            return "Tạm biệt! Chúc bạn một ngày tốt lành. Hẹn gặp lại!"

        # Capability
        if any(x in message_lower for x in ["bạn làm được gì", "bạn có thể làm gì", "giúp gì được"]):
            return "Tôi có thể giúp bạn:\n- Hướng dẫn sử dụng các tính năng VNPT Money (nạp tiền, rút tiền, chuyển tiền, thanh toán hóa đơn...)\n- Giải quyết các vấn đề kỹ thuật (lỗi giao dịch, liên kết ngân hàng, định danh...)\n- Tư vấn về phí, hạn mức, điều kiện sử dụng\n- Và nhiều thông tin khác về VNPT Money!\n\nBạn cần hỗ trợ gì?"

        # Default chitchat
        return "Tôi là VNPT Assistant. Bạn có câu hỏi gì về dịch vụ VNPT Money không?"

    def chat(self, user_message: str) -> str:
        """
        Process user message and return response WITH CONTEXT AWARENESS

        Args:
            user_message: User's input message

        Returns:
            Chatbot response
        """
        logger.info(f"User: {user_message}")

        # Step 0: Handle chitchat/greetings first (NEW)
        if self._is_chitchat(user_message):
            response = self._handle_chitchat(user_message)
            logger.info(f"Assistant (chitchat): {response}")
            return response

        # Step 1: Check for contextual references and enhance query
        enhanced_query, continuation_context = self.context_manager.enhance_query_with_context(user_message)

        # Step 2: Retrieve relevant context from GraphRAG
        rag_result = self.rag_engine.query(
            enhanced_query,
            continuation_context=continuation_context
        )

        # Step 3: Generate response
        # CRITICAL FIX: For procedural FAQs with steps, use original answer directly
        # to preserve all steps without LLM summarization
        steps = rag_result.get("steps", [])
        has_steps = steps and len(steps) > 0

        if has_steps and rag_result.get("status") == "success":
            # Procedural FAQ - use original answer to preserve all steps
            logger.info(f"Procedural FAQ detected ({len(steps)} steps), using original answer")
            response = rag_result.get("answer", "")
            # Apply formatting post-processor to improve readability
            response = self._format_answer_for_readability(response)
        elif self.llm:
            # Non-procedural or no steps - use LLM for better formatting
            response = self._generate_llm_response(user_message, rag_result, continuation_context)
        else:
            response = self._generate_template_response(rag_result)

        # Step 4: Add to conversation context
        self.context_manager.add_turn(user_message, rag_result)

        # Step 5: Add to legacy conversation history
        self.conversation_history.append({
            "user": user_message,
            "assistant": response,
            "rag_context": rag_result
        })

        logger.info(f"Assistant: {response}")

        return response

    def _generate_llm_response(self, user_message: str, rag_result: Dict, continuation_context: Optional[Dict] = None) -> str:
        """Generate response using LLM with RAG context"""

        # Build prompt with context
        prompt = self._build_prompt(user_message, rag_result, continuation_context)

        try:
            if self.llm == "openai":
                return self._call_openai(prompt)
            else:
                return self._generate_template_response(rag_result)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._generate_template_response(rag_result)

    def _build_prompt(self, user_message: str, rag_result: Dict, continuation_context: Optional[Dict] = None) -> str:
        """Build prompt for LLM with RAG context"""

        if rag_result["status"] != "success":
            return f"""Bạn là trợ lý ảo thông minh của VNPT Money, tên là "VNPT Assistant".

CÂU HỎI: {user_message}

YÊU CẦU:
Rất tiếc, tôi không tìm thấy thông tin chính xác trong cơ sở dữ liệu về câu hỏi này.

Hãy trả lời một cách thân thiện và lịch sự:
1. Xin lỗi khách hàng vì chưa có thông tin
2. Đề xuất họ liên hệ Hotline: 1900 8198 hoặc email: hotro@vnptmoney.vn
3. Giọng điệu chuyên nghiệp, thấu hiểu
4. Ngắn gọn, không dài dòng"""

        # Extract context
        answer = rag_result.get("answer", "")
        related_entities = rag_result.get("related_entities", {})
        alternative_actions = rag_result.get("alternative_actions", [])
        related_questions = rag_result.get("related_questions", [])
        steps = rag_result.get("steps", [])
        confidence = rag_result.get("confidence", 0)

        # Build context string with better structure
        context_parts = []

        # Main answer
        context_parts.append(f"📌 THÔNG TIN CHÍNH:\n{answer}")

        # Steps if available
        if steps and len(steps) > 0:
            steps_text = "\n".join([f"   Bước {i+1}: {step}" for i, step in enumerate(steps)])
            context_parts.append(f"\n📝 CÁC BƯỚC THỰC HIỆN:\n{steps_text}")

        # Related entities
        if related_entities:
            entities_info = []
            if related_entities.get("services"):
                entities_info.append(f"   • Dịch vụ: {', '.join(related_entities['services'])}")
            if related_entities.get("banks"):
                entities_info.append(f"   • Ngân hàng: {', '.join(related_entities['banks'])}")
            if related_entities.get("errors"):
                entities_info.append(f"   • Lỗi liên quan: {', '.join(related_entities['errors'])}")
            if related_entities.get("features"):
                entities_info.append(f"   • Tính năng: {', '.join(related_entities['features'])}")

            if entities_info:
                context_parts.append(f"\n🔗 THÔNG TIN LIÊN QUAN:\n" + "\n".join(entities_info))

        # Alternative actions
        if alternative_actions:
            alt_text = "\n".join([f"   • {alt['action']}: {alt['reason']}" for alt in alternative_actions])
            context_parts.append(f"\n💡 PHƯƠNG ÁN THAY THẾ:\n{alt_text}")

        # Related questions
        if related_questions:
            rq_text = "\n".join([f"   • {rq['question']}" for rq in related_questions[:3]])
            context_parts.append(f"\n❓ CÂU HỎI LIÊN QUAN:\n{rq_text}")

        context = "\n".join(context_parts)

        # Add continuation context instructions if present
        # CRITICAL: Skip if answer is a completion message
        continuation_instruction = ""
        is_completion_answer = ("✅" in answer and ("hoàn thành tất cả" in answer or "Hotline: 1900" in answer))

        if continuation_context and not is_completion_answer:
            # Case 1: Status-based continuation
            if continuation_context.get("status_result"):
                status = continuation_context["status_result"]
                next_step = continuation_context.get("next_step", 2)
                continuation_instruction = f"""
🔄 CONTINUATION CONTEXT (QUAN TRỌNG):
- Người dùng đã hoàn thành bước 1 (kiểm tra trạng thái)
- Trạng thái giao dịch: **{status}**
- BẮT BUỘC: Chỉ trả lời về bước {next_step} (trường hợp trạng thái "{status}")
- KHÔNG lặp lại bước 1 hoặc toàn bộ các bước
- Trả lời ngắn gọn, tập trung vào hành động cần làm tiếp theo

"""
            # Case 2: Step-based continuation (e.g., "đã hoàn thành N bước đầu")
            else:
                completed_step = continuation_context.get("completed_step", 1)
                next_step = continuation_context.get("next_step", 2)
                continuation_instruction = f"""
🔄 CONTINUATION CONTEXT (QUAN TRỌNG):
- Người dùng đã hoàn thành bước 1 đến bước {completed_step}
- Đang cần hướng dẫn tiếp BỘC TIẾP THEO (bước {next_step})
- BẮT BUỘC: Viết câu mở đầu TỰ NHIÊN như đang tiếp tục hội thoại
- VÍ DỤ MỞ ĐẦU TỐT:
  * "Bước tiếp theo:"
  * "Tiếp theo, bạn cần:"
  * "Sau khi hoàn thành {completed_step} bước đầu, bạn tiếp tục:"
- KHÔNG viết: "Để chuyển tiền từ VNPT Money đến ngân hàng:" (quá cứng nhắc!)
- NGỮ CẢNH chỉ chứa bước {next_step} (KHÔNG phải tất cả các bước còn lại)
- GIỮ NGUYÊN số thứ tự bước trong NGỮ CẢNH, KHÔNG đánh số lại
- Chỉ cần viết câu mở đầu tự nhiên rồi sao chép bước từ NGỮ CẢNH

"""

        # Build final prompt with improved instructions
        prompt = f"""Bạn là VNPT Assistant - trợ lý ảo của VNPT Money, nói chuyện TỰ NHIÊN như một người tư vấn viên thân thiện, KHÔNG phải là bot.

🎯 NHIỆM VỤ:
Trả lời câu hỏi dựa trên thông tin từ NGỮ CẢNH, nhưng phải VIẾT LẠI theo phong cách TỰ NHIÊN, THÂN THIỆN, DỄ HIỂU như đang tư vấn 1-1 cho khách hàng.

📋 NGUYÊN TẮC (QUAN TRỌNG):
1. **Nội dung**:
   - CHỈ sử dụng thông tin từ NGỮ CẢNH, KHÔNG bịa thêm
   - CHỈ trả lời ĐÚNG câu hỏi người dùng, KHÔNG thêm thông tin không liên quan
   - Nếu NGỮ CẢNH có nhiều FAQ: CHỈ dùng FAQ phù hợp nhất với câu hỏi
   - ⚠️ **QUAN TRỌNG - LỌC PHƯƠNG THỨC CỤ THỂ**:
     * Nếu câu hỏi đề cập đến PHƯƠNG THỨC/TÍNH NĂNG CỤ THỂ (ví dụ: "ngân hàng liên kết", "QR code", "chuyển khoản", "ví điện tử")
     * VÀ FAQ chứa NHIỀU phương thức/hình thức khác nhau
     * Thì CHỈ trích xuất và trả lời về phương thức được hỏi, BỎ QUA các phương thức khác
     * VÍ DỤ: Nếu hỏi "nạp tiền từ ngân hàng liên kết" → CHỈ trả lời về phương thức liên kết, KHÔNG kể "nạp bằng QR" hoặc phương thức khác

2. **Giọng điệu - TỰ NHIÊN NHƯ NGƯỜI THẬT (⚠️ QUAN TRỌNG NHẤT)**:
   - **TRÁNH ngôn ngữ cứng nhắc kiểu bot**: KHÔNG dùng "Bước 1, Bước 2, Bước 3" TRỪ KHI ngữ cảnh GỐC có sẵn
   - **SỬ DỤNG chuyển tiếp tự nhiên**: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
   - **THÊM động viên và cảm xúc**: "đừng lo nhé", "rất đơn giản", "dễ dàng thôi", "chỉ cần..."
   - **DÙNG ngôn ngữ thân mật**: "bạn", "mình", "nhé", "nha"
   - **NÓI như đang tư vấn trực tiếp**: Mượt mà, thấu hiểu, không cứng nhắc

   - **NẾU NGỮ CẢNH có "Bước 1, 2, 3"** → VIẾT LẠI tự nhiên hơn:
     * THAY VÌ: "Bước 1: Chọn..., Bước 2: Nhập..., Bước 3: Xác nhận..."
     * VIẾT THÀNH: "Đầu tiên, bạn cần chọn... Tiếp theo, bạn nhập... Sau đó xác nhận... Cuối cùng..."

   - **NẾU NGỮ CẢNH KHÔNG có "Bước"** → Trả lời thông thường, tự nhiên
     * Giải thích ngắn gọn, thân thiện
     * KHÔNG tự ý thêm "Bước 1, 2, 3"

3. **Phần "Lưu ý"**: CHỈ bao gồm nếu nó TRỰC TIẾP liên quan đến câu hỏi được hỏi
4. **Icon/Emoji**: CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp để làm nổi bật thông tin quan trọng
5. **KHÔNG thêm**: Câu mở đầu dài "Chào bạn! Tôi hiểu...", "Câu hỏi liên quan" không cần thiết, hoặc "Lưu ý" từ FAQ khác
6. **⚠️ COMPLETION MESSAGE**: Nếu NGỮ CẢNH chứa thông báo hoàn thành (có ✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN thông báo đó, KHÔNG đổi thành format bước

📋 VÍ DỤ TRẢ LỜI TỰ NHIÊN (CONVERSATIONAL):

**Ví dụ 1: Hủy ví VNPT Money** (NGỮ CẢNH có "Bước 1, 2, 3" → VIẾT LẠI tự nhiên):
```
Để hủy ví VNPT Money, bạn cần làm một vài việc nhé:

Đầu tiên, hãy đảm bảo bạn đã ngắt kết nối với tất cả tài khoản ngân hàng trên ví VNPT Money.

Tiếp theo, nếu ví của bạn còn số dư, bạn nên sử dụng hết hoặc chuyển ra ngân hàng trước nhé. Ngoài ra, nếu có khoản nợ nào, bạn cũng cần thanh toán hết luôn.

Sau khi hoàn tất những bước trên, bạn liên hệ với bộ phận hỗ trợ và cung cấp các thông tin cần thiết để họ xử lý việc hủy ví cho bạn.

⚠️ Lưu ý: Khi ví đã được hủy, bạn sẽ không thể khôi phục lại được nhé.
```

**Ví dụ 2: Rút tiền bị mất phí** (NGỮ CẢNH KHÔNG có "Bước" → Trả lời tự nhiên):
```
Khi bạn rút tiền từ ví VNPT Pay, bạn sẽ bị tính khoản phí theo chính sách của VNPT Pay. Đây là phí dịch vụ chuẩn, không phải lỗi nhé.

Nếu bạn muốn biết rõ hơn về mức phí, bạn có thể kiểm tra trong phần "Biểu phí" trên ứng dụng hoặc liên hệ Hotline 1900 8198 để được tư vấn chi tiết hơn.
```

**Ví dụ 3: Nạp tiền từ ngân hàng liên kết** (NGỮ CẢNH có "Bước" → VIẾT LẠI tự nhiên):
```
Nạp tiền từ ngân hàng liên kết rất đơn giản thôi bạn:

Đầu tiên, bạn chọn "Nạp tiền" trên màn hình chính.

Tiếp theo, nhập số tiền bạn muốn nạp vào, rồi ấn "Xác nhận".

Sau đó, hệ thống sẽ gửi mã OTP đến số điện thoại của bạn. Bạn chỉ cần nhập mã OTP này để hoàn tất nạp tiền là xong!

💡 Tiền sẽ được chuyển vào ví của bạn ngay lập tức sau khi xác nhận thành công.
```

**Completion message** (đã hoàn thành TẤT CẢ các bước - GIỮ NGUYÊN):
```
✅ Bạn đã hoàn thành tất cả 5 bước!

Nếu bạn vẫn gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
```
(Lưu ý: GIỮ NGUYÊN toàn bộ completion message, KHÔNG format lại)

⚠️ CRITICAL - QUY TẮC VIẾT:
- DÙNG chuyển tiếp tự nhiên: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
- TRÁNH "Bước 1, Bước 2, Bước 3" trừ khi NGỮ CẢNH gốc BẮT BUỘC phải có
- THÊM động viên: "rất đơn giản thôi", "đừng lo nhé", "dễ dàng", "chỉ cần..."
- DÙNG ngôn ngữ thân mật: "bạn", "nhé", "nha", "của bạn"
- MỖI đoạn XUỐNG DÒNG để dễ đọc (mỗi dòng tối đa 80-100 ký tự)
- GIỮ khoảng trắng giữa các phần để thoáng
- CHỈ bao gồm "Lưu ý" nếu TRỰC TIẾP liên quan đến câu hỏi
- Nếu là COMPLETION MESSAGE: GIỮ NGUYÊN, không format lại

{continuation_instruction}📚 NGỮ CẢNH (Độ tin cậy: {confidence:.0%}):
{context}

❓ CÂU HỎI:
"{user_message}"

💬 TRẢ LỜI (format dễ đọc như ví dụ - mỗi bước/bullet xuống dòng):
"""

        return prompt

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            # System message with formatting instructions
            system_message = """Bạn là VNPT Assistant - trợ lý ảo của VNPT Money, nói chuyện TỰ NHIÊN như một người tư vấn viên thân thiện.

NHIỆM VỤ CHÍNH:
- Trả lời dựa trên thông tin từ NGỮ CẢNH
- Viết theo phong cách TỰ NHIÊN, THÂN THIỆN như đang tư vấn 1-1 cho khách hàng
- Format DỄ ĐỌC: Mỗi dòng tối đa 80-100 ký tự
- KHÔNG bịa đặt thông tin

QUY TẮC VIẾT TỰ NHIÊN (⚠️ QUAN TRỌNG NHẤT):
- TRÁNH ngôn ngữ cứng nhắc kiểu bot: KHÔNG dùng "Bước 1, Bước 2, Bước 3" TRỪ KHI ngữ cảnh GỐC có sẵn
- SỬ DỤNG chuyển tiếp tự nhiên: "Đầu tiên...", "Tiếp theo...", "Sau đó...", "Cuối cùng..."
- THÊM động viên và cảm xúc: "đừng lo nhé", "rất đơn giản thôi", "dễ dàng", "chỉ cần..."
- DÙNG ngôn ngữ thân mật: "bạn", "mình", "nhé", "nha", "của bạn"
- NÓI như đang tư vấn trực tiếp: Mượt mà, thấu hiểu, không cứng nhắc

VÍ DỤ TỐT (TỰ NHIÊN):
❌ TRÁNH: "Bước 1: Đảm bảo không còn liên kết. Bước 2: Sử dụng hết số dư. Bước 3: Thanh toán dư nợ."
✅ VIẾT: "Đầu tiên, hãy đảm bảo bạn đã ngắt kết nối với tất cả tài khoản ngân hàng. Tiếp theo, nếu ví còn số dư, bạn nên sử dụng hết hoặc chuyển ra ngân hàng trước nhé."

FORMAT:
- MỖI đoạn XUỐNG DÒNG để dễ đọc (mỗi dòng tối đa 80-100 ký tự)
- KHÔNG dùng bullet points (•)
- GIỮ khoảng trắng giữa các đoạn để thoáng
- CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp
- CHỈ bao gồm "Lưu ý" nếu TRỰC TIẾP liên quan đến câu hỏi
- KHÔNG thêm: "Chào bạn", "Câu hỏi liên quan", hoặc "Lưu ý" từ FAQ không liên quan
- ⚠️ COMPLETION MESSAGE: Nếu NGỮ CẢNH có thông báo hoàn thành (✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN toàn bộ, KHÔNG format lại
"""

            # Call OpenAI API
            response = self.llm_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )

            answer = response.choices[0].message.content.strip()

            # Post-process to improve formatting
            answer = self._format_answer_for_readability(answer)

            return answer

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _format_answer_for_readability(self, answer: str) -> str:
        """
        Post-process answer to enforce better formatting:
        - Break long lines with comma-separated actions
        - Add spacing between steps
        """
        import re

        lines = answer.split('\n')
        formatted_lines = []

        for line in lines:
            # Check if this is a step line (Bước X: ...)
            step_match = re.match(r'(Bước\s+\d+:\s*)(.+)', line)

            if step_match:
                step_label = step_match.group(1)  # "Bước 1: "
                step_content = step_match.group(2)  # The actual content

                # If content has multiple comma-separated clauses and is long (>80 chars)
                # OR has 3+ commas (lots of actions)
                comma_count = step_content.count(',')

                if comma_count >= 2 or (comma_count >= 1 and len(step_content) > 80):
                    # Split by comma
                    parts = [p.strip() for p in step_content.split(',')]

                    # First part goes on same line as "Bước X:"
                    formatted_lines.append(f"{step_label}{parts[0]}")

                    # Rest go on separate lines
                    for part in parts[1:]:
                        if part:  # Skip empty parts
                            # Capitalize if starts with lowercase
                            formatted_part = part[0].upper() + part[1:] if part and part[0].islower() else part
                            formatted_lines.append(formatted_part)

                    # Add blank line after step for spacing
                    formatted_lines.append('')
                else:
                    # Step is short enough, keep as is
                    formatted_lines.append(line)
                    # Add blank line after step for spacing
                    if len(step_content) > 0:
                        formatted_lines.append('')
            else:
                # Not a step line, keep as is
                formatted_lines.append(line)

        # Remove trailing blank lines
        while formatted_lines and not formatted_lines[-1].strip():
            formatted_lines.pop()

        return '\n'.join(formatted_lines)

    def _generate_template_response(self, rag_result: Dict) -> str:
        """Generate template response without LLM"""

        if rag_result["status"] != "success":
            return """Xin lỗi, tôi chưa tìm thấy thông tin phù hợp với câu hỏi của bạn trong cơ sở dữ liệu.

Để được hỗ trợ tốt hơn, bạn có thể:
📞 Gọi Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
🌐 Truy cập: https://vnptpay.vn

Chúng tôi luôn sẵn sàng hỗ trợ bạn!"""

        # Extract information
        answer = rag_result.get("answer", "")
        alternative_actions = rag_result.get("alternative_actions", [])
        related_questions = rag_result.get("related_questions", [])
        related_entities = rag_result.get("related_entities", {})
        confidence = rag_result.get("confidence", 0)

        # Build response
        response_parts = []

        # Main answer with confidence indicator
        if confidence >= 0.8:
            response_parts.append(f"{answer}")
        else:
            response_parts.append(f"Dựa trên thông tin tôi tìm được:\n\n{answer}")

        # Alternative actions
        if alternative_actions:
            response_parts.append("\n💡 **Phương án thay thế:**")
            for i, alt in enumerate(alternative_actions, 1):
                response_parts.append(f"{i}. {alt['action']}: {alt['reason']}")

        # Additional info from entities
        if related_entities:
            notes = []
            if related_entities.get("errors"):
                notes.append(f"⚠️ Lỗi liên quan: {', '.join(related_entities['errors'])}")
            if related_entities.get("features"):
                notes.append(f"✨ Tính năng: {', '.join(related_entities['features'])}")

            if notes:
                response_parts.append("\n" + "\n".join(notes))

        # Related questions
        if related_questions:
            response_parts.append("\n❓ **Bạn có thể quan tâm:**")
            for i, rq in enumerate(related_questions[:3], 1):
                response_parts.append(f"{i}. {rq['question']}")

        # Footer
        response_parts.append("\n---")
        response_parts.append("Nếu cần hỗ trợ thêm, vui lòng liên hệ Hotline: 1900 8198")

        return "\n".join(response_parts)

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history

    def clear_history(self):
        """Clear conversation history and context"""
        self.conversation_history = []
        self.context_manager.clear_context()
        logger.info("Conversation history and context cleared")

    def get_chat_statistics(self) -> Dict:
        """Get chatbot statistics with context info"""
        context_summary = self.context_manager.get_summary()
        return {
            "total_conversations": len(self.conversation_history),
            "llm_enabled": self.llm is not None,
            "llm_provider": config.LLM_PROVIDER,
            "cache_size": len(self.rag_engine.cache),
            "context_turns": context_summary.get("num_turns", 0),
            "current_topic": context_summary.get("current_topic"),
            "has_active_context": context_summary.get("has_active_context", False)
        }


# ============================================
# INTERACTIVE CHAT
# ============================================

def interactive_chat():
    """Run interactive chatbot session"""
    print("=" * 60)
    print("VNPT Money GraphRAG Chatbot")
    print("=" * 60)
    print("Gõ 'exit' hoặc 'quit' để thoát")
    print("Gõ 'clear' để xóa lịch sử hội thoại")
    print("Gõ 'stats' để xem thống kê")
    print("=" * 60)

    chatbot = GraphRAGChatbot()

    while True:
        try:
            user_input = input("\n\nBạn: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'thoát']:
                print("\nCảm ơn bạn đã sử dụng VNPT Money Chatbot. Hẹn gặp lại!")
                break

            if user_input.lower() == 'clear':
                chatbot.clear_history()
                print("\nĐã xóa lịch sử hội thoại.")
                continue

            if user_input.lower() == 'stats':
                stats = chatbot.get_chat_statistics()
                print(f"\nThống kê:")
                print(f"  - Số lượt hội thoại: {stats['total_conversations']}")
                print(f"  - LLM: {stats['llm_provider']} ({'Enabled' if stats['llm_enabled'] else 'Disabled'})")
                print(f"  - Cache size: {stats['cache_size']}")
                continue

            # Get response
            response = chatbot.chat(user_input)

            print(f"\nVNPT Money Bot: {response}")

        except KeyboardInterrupt:
            print("\n\nCảm ơn bạn đã sử dụng VNPT Money Chatbot. Hẹn gặp lại!")
            break
        except Exception as e:
            logger.error(f"Error in chat loop: {e}")
            print(f"\nXin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.")


if __name__ == "__main__":
    interactive_chat()
