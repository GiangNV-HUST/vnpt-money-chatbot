"""
Streamlit UI cho Excel FAQ Chatbot
"""

import streamlit as st
import logging
from rag_chatbot import RAGChatbotSystem

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    st.set_page_config(page_title="VNPT Bot", page_icon="🤖", layout="wide")

    st.title("🤖 VNPT Bot")
    # st.markdown("*Powered by Vietnamese-SBERT + Google Gemini 2.0 Flash*")

    # Khởi tạo chatbot
    with st.spinner("Đang khởi tạo chatbot..."):
        if "chatbot" not in st.session_state:
            try:
                st.session_state.chatbot = RAGChatbotSystem()
                st.success("✅ Chatbot sẵn sàng!")
            except Exception as e:
                st.error(f"❌ Lỗi khởi tạo: {str(e)}")
                return

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Quản lý")

        # Quản lý

        if st.button("🔄️ Reload dữ liệu"):
            with st.spinner("Đang reload..."):
                st.session_state.chatbot.reload_data()
                st.success("✅ Đã reload dữ liệu")

        if st.button("🗑️ Xóa lịch sử chat"):
            st.session_state.chatbot.clear_memory()
            st.session_state.messages = [
                {"role": "assistant", "content": "Xin chào! Hỏi tôi bất cứ điều gì."},
            ]
            st.success("✅ Đã xóa lịch sử")

        # Thông tin
        st.subheader("ℹ️ Thông tin")
        st.info(
            """
                **Model**
                - Embedding: Vietnamese-SBERT
                - LLM: Google Gemini 2.5 Flash
                - Vector DB: FAISS
                
                **Hướng dẫn**
                1. Đặt file Excel FAQ vào thư mục data/
                2. Click "Reload dữ liệu"
                3. Bắt đầu chat!
                

            """
        )

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Xin chào! Hỏi tôi bất cứ điều gì."}
        ]

    # Hiển thị lịch sử
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])



            # # Hiện thị sources
            # if message.get("sources"):
            #     st.markdown("**📌 Nguồn:**")
            #     for source in message["sources"]:
            #         st.markdown(f"- {source}")
    # Chạy input
    if prompt := st.chat_input("Nhập câu hỏi của bạn.."):
        # Thêm user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Xử lý và hiện thị response
        with st.chat_message("assistant"):
            with st.spinner("Đang suy nghĩ..."):
                response = st.session_state.chatbot.chat(prompt)

                # Hiển thi answer
                st.markdown(response["answer"])

                # # Hiện thị sources
                # if response.get("sources"):
                #     st.markdown("**📌 Nguồn:**")
                #     for source in response["sources"]:
                #         st.markdown(f"- {source}")

                # Lưu vào history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response.get("sources", []),
                        "confidence": response.get("confidence"),
                    }
                )


if __name__ == "__main__":
    main()
