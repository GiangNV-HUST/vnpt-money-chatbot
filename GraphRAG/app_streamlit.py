# -*- coding: utf-8 -*-
"""
Streamlit Chat Interface for VNPT Money GraphRAG Chatbot
"""

import streamlit as st
import logging
from datetime import datetime
from chatbot import GraphRAGChatbot  # Use the main chatbot class
import config

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="VNPT Money Chatbot",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #1E88E5;
    }
    .bot-message {
        background-color: #F5F5F5;
        border-left: 4px solid #4CAF50;
    }
    .message-header {
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    .user-header {
        color: #1E88E5;
    }
    .bot-header {
        color: #4CAF50;
    }
    .confidence-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .high-confidence {
        background-color: #4CAF50;
        color: white;
    }
    .medium-confidence {
        background-color: #FFC107;
        color: black;
    }
    .low-confidence {
        background-color: #FF5722;
        color: white;
    }
    .entity-tag {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        margin: 0.2rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        background-color: #E1F5FE;
        color: #01579B;
    }
    .footer {
        text-align: center;
        color: #666;
        padding: 1rem;
        margin-top: 2rem;
        border-top: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_chatbot():
    """Load chatbot instance (cached)"""
    return GraphRAGChatbot()


def format_confidence(confidence):
    """Format confidence badge"""
    if confidence >= 0.7:
        badge_class = "high-confidence"
        label = "Cao"
    elif confidence >= 0.4:
        badge_class = "medium-confidence"
        label = "Trung bình"
    else:
        badge_class = "low-confidence"
        label = "Thấp"

    return f'<span class="confidence-badge {badge_class}">{label} ({confidence:.0%})</span>'


def display_message(role, content, metadata=None):
    """Display a chat message"""

    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-header user-header">👤 Bạn</div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        confidence_badge = ""
        entities_html = ""
        related_html = ""

        if metadata:
            confidence = metadata.get("confidence", 0)
            confidence_badge = format_confidence(confidence)

            # Entities
            entities = metadata.get("related_entities", {})
            entity_tags = []

            if entities.get("services"):
                for s in entities["services"][:3]:
                    entity_tags.append(f'<span class="entity-tag">🔹 {s}</span>')
            if entities.get("topics"):
                for t in entities["topics"][:3]:
                    entity_tags.append(f'<span class="entity-tag">📌 {t}</span>')
            if entities.get("banks"):
                for b in entities["banks"][:2]:
                    entity_tags.append(f'<span class="entity-tag">🏦 {b}</span>')

            if entity_tags:
                entities_html = "<br><br>" + "".join(entity_tags)

            # Related questions
            related_q = metadata.get("related_questions", [])
            if related_q:
                related_html = "<br><br><b>📚 Câu hỏi liên quan:</b><br>"
                for i, rq in enumerate(related_q[:2], 1):
                    related_html += f"<small>{i}. {rq['question']}</small><br>"

        st.markdown(f"""
        <div class="chat-message bot-message">
            <div class="message-header bot-header">
                🤖 VNPT Assistant {confidence_badge}
            </div>
            <div>{content}{entities_html}{related_html}</div>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main Streamlit app"""

    # Header
    st.markdown('<h1 class="main-header">💬 VNPT Money Chatbot</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài đặt")

        # Stats
        st.subheader("📊 Thống kê")
        if "message_count" in st.session_state:
            st.metric("Số câu hỏi", st.session_state.message_count)

        if "avg_confidence" in st.session_state and st.session_state.avg_confidence > 0:
            st.metric("Độ tin cậy TB", f"{st.session_state.avg_confidence:.0%}")

        st.markdown("---")

        # Clear chat
        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            # Clear Streamlit session state
            st.session_state.messages = []
            st.session_state.message_count = 0
            st.session_state.avg_confidence = 0

            # Clear chatbot history
            chatbot = load_chatbot()
            chatbot.clear_history()

            st.rerun()

        st.markdown("---")

        # Info
        st.markdown("""
        ### 📖 Hướng dẫn
        - Nhập câu hỏi về VNPT Money
        - Bot sẽ tìm kiếm trong 803 FAQs
        - Câu trả lời dựa trên Neo4j Graph

        ### 💡 Ví dụ câu hỏi
        - Làm sao nạp tiền vào ví?
        - Liên kết ngân hàng như thế nào?
        - Kiểm tra lịch sử giao dịch ở đâu?
        """)

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    if "avg_confidence" not in st.session_state:
        st.session_state.avg_confidence = 0

    # Load chatbot
    with st.spinner("🔄 Đang khởi tạo hệ thống..."):
        chatbot = load_chatbot()

    # Display chat history
    for message in st.session_state.messages:
        display_message(
            message["role"],
            message["content"],
            message.get("metadata")
        )

    # Chat input
    if prompt := st.chat_input("Nhập câu hỏi của bạn..."):

        # Display user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        display_message("user", prompt)

        # Get response using chatbot
        with st.spinner("🤔 Đang suy nghĩ..."):
            try:
                # Call chatbot.chat() - it handles everything internally
                response = chatbot.chat(prompt)

                # Get the last RAG result for metadata
                if chatbot.conversation_history:
                    last_turn = chatbot.conversation_history[-1]
                    rag_context = last_turn.get("rag_context", {})

                    # Update stats
                    st.session_state.message_count += 1
                    if rag_context.get("confidence"):
                        # Running average
                        old_avg = st.session_state.avg_confidence
                        count = st.session_state.message_count
                        st.session_state.avg_confidence = (old_avg * (count - 1) + rag_context["confidence"]) / count

                    # Display bot message with metadata
                    metadata = {
                        "confidence": rag_context.get("confidence", 0),
                        "related_entities": rag_context.get("related_entities", {}),
                        "related_questions": rag_context.get("related_questions", []),
                        "is_continuation": rag_context.get("is_continuation", False),
                        "completed_step": rag_context.get("completed_step")
                    }

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "metadata": metadata,
                        "timestamp": datetime.now()
                    })

                    display_message("assistant", response, metadata)
                else:
                    # Fallback if no context available
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "metadata": {},
                        "timestamp": datetime.now()
                    })
                    display_message("assistant", response, {})

            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
                logger.error(f"Chat error: {e}", exc_info=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <p>🚀 Powered by Neo4j GraphRAG + LLM | 📊 Database: 803 FAQs | 💡 Neo4j + Sentence Transformers</p>
        <p><small>Hotline: 1900 8198 | Email: hotro@vnptmoney.vn</small></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
