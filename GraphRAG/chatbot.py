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

    def chat(self, user_message: str) -> str:
        """
        Process user message and return response WITH CONTEXT AWARENESS

        Args:
            user_message: User's input message

        Returns:
            Chatbot response
        """
        logger.info(f"User: {user_message}")

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
        prompt = f"""Bạn là VNPT Assistant - trợ lý ảo của VNPT Money.

🎯 NHIỆM VỤ:
Trả lời câu hỏi dựa trên thông tin từ NGỮ CẢNH bên dưới.

📋 NGUYÊN TẮC (QUAN TRỌNG):
1. **Nội dung**:
   - CHỈ sử dụng thông tin từ NGỮ CẢNH, KHÔNG bịa thêm
   - CHỈ trả lời ĐÚNG câu hỏi người dùng, KHÔNG thêm thông tin không liên quan
   - Nếu NGỮ CẢNH có nhiều FAQ: CHỈ dùng FAQ phù hợp nhất với câu hỏi
2. **Format - NGẮN GỌN**:
   - MỖI bước XUỐNG DÒNG riêng (Bước 1, Bước 2,...)
   - KHÔNG dùng bullet points (•) trong mỗi bước
   - Nội dung mỗi bước viết LIỀN MẠCH, ngắn gọn, không xuống dòng chi tiết con
3. **Phần "Lưu ý"**: CHỈ bao gồm nếu nó TRỰC TIẾP liên quan đến câu hỏi được hỏi
4. **Icon/Emoji**: CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp để làm nổi bật thông tin quan trọng
5. **KHÔNG thêm**: Câu mở đầu dài "Chào bạn! Tôi hiểu...", "Câu hỏi liên quan" không cần thiết, hoặc "Lưu ý" từ FAQ khác
6. **⚠️ COMPLETION MESSAGE**: Nếu NGỮ CẢNH chứa thông báo hoàn thành (có ✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN thông báo đó, KHÔNG đổi thành format bước

📋 VÍ DỤ FORMAT TỐT:

**Câu hỏi đầu tiên** (chưa có context):
```
Để chuyển tiền từ VNPT Money đến ngân hàng:

Bước 1: Chọn chuyển "Đến ngân hàng", nhấn vào tùy chọn "Đến ngân hàng"
Bước 2: Chọn "Qua số tài khoản/số thẻ", chọn phương thức chuyển
Bước 3: Chọn ngân hàng cần chuyển, lựa chọn ngân hàng mà bạn muốn chuyển tiền đến

⚠️ Lưu ý: Ngay sau khi bạn hoàn tất giao dịch chuyển tiền, người nhận sẽ nhận được tiền trong tài khoản ngân hàng.
```

**Câu hỏi tiếp theo** (đã hoàn thành 3 bước đầu, cần hướng dẫn bước 4):
```
Bước tiếp theo:

Bước 4: Nhập số tài khoản/số thẻ và ấn Kiểm tra
```
(Lưu ý: Câu mở đầu ngắn gọn "Bước tiếp theo:", GIỮ NGUYÊN số bước 4, KHÔNG đánh lại thành "Bước 1")

**Completion message** (đã hoàn thành TẤT CẢ các bước):
```
✅ Bạn đã hoàn thành tất cả 5 bước!

Nếu bạn vẫn gặp vấn đề hoặc cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
```
(Lưu ý: GIỮ NGUYÊN toàn bộ completion message, KHÔNG format lại)

⚠️ CRITICAL:
- Mỗi bước PHẢI xuống dòng riêng
- KHÔNG dùng bullet points (•), nội dung trong bước viết liền
- CHỈ bao gồm "Lưu ý" nếu nó TRỰC TIẾP liên quan đến câu hỏi (KHÔNG tự động thêm từ FAQ khác!)
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
            system_message = """Bạn là VNPT Assistant - trợ lý ảo của VNPT Money.

NHIỆM VỤ CHÍNH:
- Trả lời dựa trên thông tin từ NGỮ CẢNH
- Format NGẮN GỌN: KHÔNG xuống dòng nhiều, KHÔNG dùng bullet points (•)
- KHÔNG bịa đặt thông tin

QUY TẮC FORMAT (CRITICAL):
- MỖI bước XUỐNG DÒNG riêng
- KHÔNG dùng bullet points (•)
- Nội dung trong bước viết LIỀN MẠCH, ngắn gọn, không xuống dòng chi tiết con
- CHỈ bao gồm "Lưu ý" nếu nó TRỰC TIẾP liên quan đến câu hỏi được hỏi
- CÓ THỂ thêm icon thân thiện (⚠️ 💡 ✅ ❌ 📞) khi phù hợp
- KHÔNG thêm: "Chào bạn", "Câu hỏi liên quan", hoặc "Lưu ý" từ FAQ không liên quan
- KHI TIẾP TỤC HỘI THOẠI: Dùng câu mở đầu tự nhiên như "Các bước tiếp theo là:", "Tiếp theo, bạn cần làm:", KHÔNG lặp lại intro ban đầu
- ⚠️ COMPLETION MESSAGE: Nếu NGỮ CẢNH có thông báo hoàn thành (✅, "đã hoàn thành tất cả", "Hotline: 1900"), GIỮ NGUYÊN toàn bộ, KHÔNG format lại

VÍ DỤ FORMAT:
1. Câu hỏi đầu (8 bước): "Để nạp tiền: Bước 1: ..., Bước 2: ..., Bước 3: ..."
2. Câu tiếp theo (đã làm 3 bước, cần bước 4): "Bước tiếp theo: Bước 4: ..." (GIỮ NGUYÊN số 4, KHÔNG đánh lại thành Bước 1!)
3. Hoàn thành tất cả: "✅ Bạn đã hoàn thành tất cả X bước! Nếu bạn vẫn gặp vấn đề... 📞 Hotline: 1900 8198" (GIỮ NGUYÊN, KHÔNG đổi format)
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

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

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
