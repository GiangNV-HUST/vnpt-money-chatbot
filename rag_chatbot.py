"""
RAG Chatbot System tối ưu cho Excel FAQ
"""

import os
import logging
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
from dotenv import load_dotenv
from faq_loader import load_all_faq_files, load_faq_json
from hybrid_search import HybridRetrieverWrapper, HybridRetriever

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


class RAGChatbotSystem:
    def __init__(
        self,
        data_dir="data",
        persist_dir="faiss_index",
        company_name="VNPT-Media",
        use_hybrid_search=True,
        hybrid_alpha=0.5,
    ):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.company_name = company_name
        self.use_hybrid_search = use_hybrid_search
        self.hybrid_alpha = hybrid_alpha

        logger.info(f"Khởi tạo RAG Chatbot: {os.path.abspath(data_dir)}")

        # 1. Load Embedding Model (Fine-tuned Vietnamese-SBERT)
        try:
            # Ưu tiên sử dụng model đã finetune
            local_model_path = os.path.join(os.getcwd(), "models", "vnpt-sbert-mnrl")

            if os.path.exists(local_model_path):
                logger.info(f"Tải finetuned Vietnamese SBERT từ local: {local_model_path}")
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name=local_model_path,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                logger.info(f"Đã tải thành công finetune model từ local")
            else:
                logger.warning("⚠️ Không tìm thấy fine-tuned model, sử dụng base model...")
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="Keepitreal/vietnamese-sbert",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
            logger.info("✅ Đã tải embedding model")

        except Exception as e:
            raise Exception(f"Không thể tải embedding model: {str(e)}")

        # 2. Khởi tạo Google Gemini LLM
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("Thiết lập GOOGLE_API_KEY trong .env")

        try:
            logger.info("Khởi tạo Google Gemini 2.5 Flash...")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                temperature=0.1,
                google_api_key=google_api_key,
                max_output_tokens=2048,
                top_p=0.8,
                top_k=20,
            )
            logger.info("✅ Đã khởi tạo Gemini")
        except Exception as e:
            raise Exception(f"Lỗi khởi tạo Gemini: {str(e)}")

        # 3. Memory
        self.memory = InMemoryChatMessageHistory()

        # 4. Đảm bảo thư mục data tồn tài
        self._ensure_data_directory()

        # 5. Load hoặc tạo FAISS index
        if os.path.exists(f"{persist_dir}/index.faiss") and os.path.exists(
            f"{persist_dir}/index.pkl"
        ):
            logger.info(f"Tải FAISS index từ {persist_dir}")
            try:
                self.vectordb = FAISS.load_local(
                    persist_dir,
                    self.embedding_model,
                    allow_dangerous_deserialization=True,
                )
                logger.info("✅ Đã tải FAISS index")
            except Exception as e:
                logger.error(f"Lỗi tải FAISS: {e}")
                self._setup_system()

        else:
            logger.info("Tạo vector database mới...")
            self._setup_system()

        # 6. Setup chain
        self._setup_chain()

    def _ensure_data_directory(self):
        """Đảm bảo thư mục data tồn tại"""
        data_path = Path(self.data_dir)
        data_path.mkdir(exist_ok=True)

    def _setup_system(self):
        """Load documents và tạo FAISS index"""
        # Ưu tiên load từ file JSON paraphrase_documents.json
        json_file = os.path.join(self.data_dir, "paraphrase_documents.json")

        if os.path.exists(json_file):
            logger.info(f"📄 Tìm thấy file JSON: {json_file}")
            documents = load_faq_json(json_file)
        else:
            logger.info(f"⚠️ Không tìm thấy file JSON, load từ Excel...")
            # Fallback: Load tất cả Excel FAQ từ data/
            documents = load_all_faq_files(self.data_dir)

        # Xử lý trường hợp documents là None hoặc rỗng
        if documents is None or not documents:
            logger.warning("Không có documents, tạo document mẫu")
            documents = [
                Document(page_content="Tài liệu mẫu.", metadata={"source": "sample"})
            ]

        # Tạo FAISS vector database
        try:
            logger.info(f"Embedding {len(documents)} documents...")
            self.vectordb = FAISS.from_documents(documents, self.embedding_model)

            os.makedirs(self.persist_dir, exist_ok=True)
            self.vectordb.save_local(self.persist_dir)
            logger.info("✅ Đã tạo và lưu FAISS index")

            # Khởi tạo hybrid search nếu được bật
            if self.use_hybrid_search:
                logger.info("Khởi tạo Hybrid Retriever...")
                self.hybrid_retriever = HybridRetriever(
                    vectorstore=self.vectordb,
                    documents=documents,
                    alpha=self.hybrid_alpha,
                    k=3,
                )
            else:
                self.hybrid_retriever = None

        except Exception as e:
            logger.error(f"Lỗi tạo FAISS index: {e}")
            raise

    def _setup_chain(self):
        """Setup ConversationRetrievalChain"""
        # Sử dụng hybrid search hoặc FAISS retrieval
        if (
            self.use_hybrid_search
            and hasattr(self, "hybrid_retriever")
            and self.hybrid_retriever
        ):
            logger.info("Sử dụng hybrid retriever cho chain")
            retriever = HybridRetrieverWrapper(self.hybrid_retriever)
        else:
            logger.info("Sử dụng FAISS MMR Retriever cho chain")
            retriever = self.vectordb.as_retriever(
                search_type="mmr", search_kwargs={"k": 3, "fetch_k": 6}
            )

        company_context = f"về {self.company_name}" if self.company_name else ""

        # Prompt template với strict anti-hallucination rules
        template = f"""Bạn là trợ lý ảo thông minh của VNPT Money, giúp trả lời các câu hỏi về ứng dụng VNPT Money, ví điện tử, và các dịch vụ tài chính liên quan.

NGUYÊN TẮC QUAN TRỌNG - PHẢI TUÂN THỦ NGHIÊM NGẶT

1. **XỬ LÝ CÂU GIAO TIẾP CƠ BẢN** (KHÔNG cần context):
   - Chào hỏi: "Xin chào", "Hi", "Hello", "Chào bạn"
     → Trả lời: "Xin chào! Tôi là trợ lý ảo của VNPT Money. Tôi có thể giúp gì cho bạn hôm nay?"

   - Cảm ơn: "Cảm ơn", "Thanks", "Cảm ơn bạn"
     → Trả lời: "Rất vui được giúp đỡ bạn! Nếu còn thắc mắc gì về VNPT Money, đừng ngần ngại hỏi tôi nhé."

   - Tạm biệt: "Tạm biệt", "Bye", "Goodbye"
     → Trả lời: "Tạm biệt! Chúc bạn có trải nghiệm tốt với VNPT Money. Hẹn gặp lại!"

   - Hỏi khỏe: "Bạn khỏe không?", "How are you?"
     → Trả lời: "Tôi khỏe, cảm ơn bạn! Tôi luôn sẵn sàng hỗ trợ bạn về VNPT Money. Bạn cần tôi giúp gì?"

2. CHỈ trả lời câu hỏi liên quan đến VNPT Money, VNPT Pay, ví điện tử, dịch vụ thanh toán, nạp/rút/chuyển tiền, liên kết ngân hàng

3. Nếu câu hỏi KHÔNG liên quan đến VNPT Money hoặc dịch vụ tài chính:
   - Nếu hỏi mua HÀNG HÓA VẬT LÝ (máy bay, xe, nhà, điện thoại...) → Trả lời:
     "Xin lỗi, hiện tại VNPT Money chưa hỗ trợ mua mặt hàng này. Bạn còn câu hỏi nào mà VNPT Money có thể giúp không?"

   - Nếu hỏi về thời tiết, nấu ăn, lịch sử, toán học,... → Trả lời:
     "Xin lỗi, tôi là trợ lý chuyên về VNPT Money nên chỉ có thể tư vấn các vấn đề liên quan đến ứng dụng và dịch vụ ví điện tử thôi ạ. Bạn có câu hỏi nào về VNPT Money mà tôi có thể giúp không?"

4. ⭐ CỰC KỲ QUAN TRỌNG - CHỈ TRẢ LỜI DỰA VÀO CONTEXT (ngoại trừ câu giao tiếp cơ bản):
    Nếu Context KHÔNG chứa đủ thông tin để trả lời câu hỏi, trả lời tự nhiên và KHÔNG được sử dụng các cụm từ máy móc như "trong dữ liệu của mình", "theo dữ liệu":
    "Xin lỗi, tôi chưa có thông tin về vấn đề này. Để được hỗ trợ chính xác nhất, bạn vui lòng liên hệ hotline 1900 8198 hoặc email support@vnptmoney.vn nhé!"

5. **TUYỆT ĐỐI KHÔNG ĐƯỢC**:
    - Tự suy đoán hoặc thêm thông tin KHÔNG có trong context
    - Bịa đặt hoặc tưởng tượng thông tin
    - Sử dụng kiến thức chung của bạn để trả lời về VNPT Money
    - Đưa ra câu trả lời mơ hồ khi không chắc chắn

6. **CHỈ ĐƯỢC**:
    - Trả lời các câu giao tiếp cơ bản (chào, cảm ơn, tạm biệt) KHÔNG cần context
    - Trích dẫn CHÍNH XÁC thông tin từ Context cho câu hỏi chuyên môn
    - Paraphrase (diễn giải lại) thông tin trong Context
    - Kết hợp nhiều phần tử từ Context để trả lời
    - Từ chối lịch sự khi Context không có thông tin

7. Trả lời ngắn gọn, chính xác, lịch sự và chuyên nghiệp. Giọng điệu thân thiện như đang tư vấn trực tiếp cho khách hàng

Context từ cơ sở dữ liệu: {{context}}
Lịch sử hội thoại: {{chat_history}}
Câu hỏi của khách hàng: {{question}}

Hướng dẫn trả lời:
0. **KIỂM TRA Ý ĐỊNH CỦA CÂU HỎI TRƯỚC - CỰC KỲ QUAN TRỌNG:**

   ⚠️ QUY TẮC: Phân biệt giữa câu hỏi về DỊCH VỤ của VNPT Money vs câu hỏi mua BÁN hàng hóa vật lý

   ✅ CÓ LIÊN QUAN - Các dịch vụ VNPT Money hỗ trợ:
   - "mua vé máy bay", "đặt vé máy bay", "thanh toán vé máy bay" (dịch vụ đặt vé ✅)
   - "nạp tiền", "chuyển tiền", "rút tiền", "liên kết ngân hàng"
   - "thanh toán hóa đơn", "mua thẻ cào", "nạp điện thoại"
   - Các dịch vụ thanh toán/tài chính khác

   ❌ KHÔNG LIÊN QUAN - Mua bán hàng hóa VẬT LÝ (không phải dịch vụ):
   - "mua máy bay" (mua chiếc máy bay - hàng hóa vật lý ❌)
   - "mua xe máy", "mua ô tô", "mua nhà", "mua điện thoại"
   - "giá vàng", "thời tiết", "nấu ăn"

   **QUAN TRỌNG - Phân biệt ngữ nghĩa:**

   Câu hỏi: "mua vé máy bay"
   → ✅ CÓ liên quan (mua VÉ = dịch vụ thanh toán, VNPT Money hỗ trợ)
   → Kiểm tra Context và trả lời

   Câu hỏi: "mua máy bay"
   → ❌ KHÔNG liên quan (mua CHIẾC MÁY BAY = hàng hóa vật lý)
   → Trả lời: "Xin lỗi, hiện tại VNPT Money chưa hỗ trợ mua mặt hàng này. Bạn còn câu hỏi nào mà VNPT Money có thể giúp không?"

   Câu hỏi: "tôi muốn mua máy bay"
   → ❌ KHÔNG liên quan (mua hàng hóa vật lý)
   → Trả lời: "Xin lỗi, hiện tại VNPT Money chưa hỗ trợ mua mặt hàng này. Bạn còn câu hỏi nào mà VNPT Money có thể giúp không?"

   Câu hỏi: "đặt vé máy bay như thế nào"
   → ✅ CÓ liên quan (đặt vé = dịch vụ)
   → Kiểm tra Context và trả lời

   Câu hỏi: "mua xe máy"
   → ❌ KHÔNG liên quan (mua hàng hóa vật lý)
   → Trả lời: "Xin lỗi, hiện tại VNPT Money chưa hỗ trợ mua mặt hàng này. Bạn còn câu hỏi nào mà VNPT Money có thể giúp không?"

   **NGUYÊN TẮC:**
   - "mua VÉ/THẺ" = dịch vụ → Trả lời ✅
   - "mua HÀNG HÓA VẬT LÝ" (máy bay, xe, nhà...) = không phải dịch vụ → Từ chối ❌
   - Nếu không chắc → Kiểm tra Context, nếu Context có thông tin phù hợp → Trả lời

1. **Kiểm tra xem có phải câu giao tiếp cơ bản không** (chào, cảm ơn, tạm biệt, hỏi khỏe)
   - Nếu có -> Trả lời thân thiện theo hướng dẫn ở trên, KHÔNG cần dùng Context

2. **Nếu là câu hỏi chuyên môn về VNPT Money:**
   - Đọc kỹ Context
   - Nếu Context CÓ thông tin -> Trả lời dựa vào HOÀN TOÀN Context
   - Nếu Context KHÔNG có thông tin -> Trả lời: "Xin lỗi, tôi chưa có thông tin về vấn đề này. Để được hỗ trợ chính xác nhất, bạn vui lòng liên hệ hotline 1900 8198 hoặc email support@vnptmoney.vn nhé!"

3. **Nếu câu hỏi KHÔNG liên quan VNPT Money:**
   - Nếu hỏi mua HÀNG HÓA VẬT LÝ (máy bay, xe, nhà...) → Trả lời: "Xin lỗi, hiện tại VNPT Money chưa hỗ trợ mua mặt hàng này. Bạn còn câu hỏi nào mà VNPT Money có thể giúp không?"
   - Nếu hỏi về thời tiết, nấu ăn, v.v. → Trả lời: "Xin lỗi, tôi là trợ lý chuyên về VNPT Money nên chỉ có thể tư vấn các vấn đề liên quan đến ứng dụng và dịch vụ ví điện tử thôi ạ. Bạn có câu hỏi nào về VNPT Money mà tôi có thể giúp không?"

**QUAN TRỌNG - Format câu trả lời:**
Nếu Context có cấu trúc nhiều bước/ cách thức (ví dụ: "Bước 1", "Bước 2", hoặc nhiều cách làm):
- Format rõ ràng với **tiêu đề in đậm** cho từng cách/phương pháp
- Chia thành bullet points (-) cho từng bước
- Xuống dòng giữa các cách để dễ đọc
- Ví dụ:
    **Cách 1: Nạp tiền từ ngân hàng liên kết**
    - Bước 1: Mở app, chọn "Nạp tiền"
    - Bước 2: Chọn ngân hàng
    
    **Cách 2: Chuyển khoản ngân hàng**
    - Bước 1: ...
Nếu Context là đoạn văn liên tục (không có bước):
- Giữ nguyên nội dung, paraphrase tự nhiên
- Có thể chia thành nhiều đoạn ngắn (2-3 câu/đoạn) để dễ đọc
- Sự dụng **in đậm** cho những thông tin quan trọng (số tiền, thời gian, tên ngân hàng...)

**HIỂN THỊ NGUỒN:**
- Sau khi trả lời xong, LUÔN thêm 1 dòng cuối cùng hiện thị nguồn thông tin
- Format: "\n\n📌 *Nguồn: [Tên sheet]*"
- Nếu không tìm thấy thông tin sheet_name trong metadata có thể bỏ qua dòng này

Trả lời:
"""

        QA_PROMPT = PromptTemplate(
            input_variables=["context", "chat_history", "question"], template=template
        )

        # Tạo chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            return_source_documents=True,
        )

        # Wrap với memory
        self.chain = RunnableWithMessageHistory(
            chain,
            lambda: self.memory,
            input_messages_key="question",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def _check_relevance(self, query: str, threshold: float = 0.3):
        """
        Kiểm tra độ liên quan của câu hỏi với dữ liệu
        Returns: (is_relevant, similarity_score)
        """
        try:
            docs_and_scores = self.vectordb.similarity_search_with_score(query, k=5)

            if not docs_and_scores:
                return False, 0.0

            best_distance = docs_and_scores[0][1]

            # Chuyển distance -> similarity (0-1)
            similarity = 1 / (1 + best_distance * 0.5)

            # Log chi tiết để debug
            logger.info(f"📊 Query: '{query[:50]}...'")
            logger.info(f"   Best similarity: {similarity:.4f} (threshold: {threshold})")
            logger.info(f"   Best distance: {best_distance:.4f}")
            logger.info(f"   Top doc: {docs_and_scores[0][0].page_content[:80]}...")

            return similarity > threshold, similarity

        except Exception as e:
            logger.error(f"Lỗi check relevance: {e}")
            return True, 1.0

    def _is_generic_no_info_response(self, answer: str) -> bool:
        """Kiểm tra xem câu trả lời có phải không biết không"""
        no_info_phrases = [
            "Không tìm thấy thông tin",
            "Không có thông tin",
            "tôi không biết",
            "vui lòng liên hệ",
        ]
        return any(phrase in answer.lower() for phrase in no_info_phrases)

    def _is_greeting(self, query: str) -> tuple:
        """
        Kiểm tra xem câu hỏi có phải là câu giao tiếp cơ bản không
        Returns: (is_greeting, greeting_type)
        """
        query_lower = query.lower().strip()

        # Loại trừ các từ khóa nghiệp vụ chứa "chào" hoặc các từ tương tự
        business_keywords = [
            "giao dịch", "chuyển khoản", "thanh toán", "nạp tiền", "rút tiền",
            "liên kết", "ngân hàng", "tài khoản", "ví", "app", "ứng dụng"
        ]

        # Nếu câu hỏi chứa từ khóa nghiệp vụ → không phải greeting
        if any(keyword in query_lower for keyword in business_keywords):
            return False, None

        # Chào hỏi - chỉ match khi câu ngắn (< 15 từ)
        words = query_lower.split()
        if len(words) <= 15:
            # Các pattern chào hỏi cụ thể
            exact_greetings = [
                "xin chào", "chào bạn", "chào bn", "hi", "hello", "hey",
                "chào bot", "chào chatbot", "chào trợ lý", "xin chao"
            ]
            if any(g in query_lower for g in exact_greetings):
                return True, "greeting"

            # Chỉ "chào" khi đứng đầu câu hoặc là từ duy nhất
            if query_lower.startswith("chào") and len(words) <= 3:
                return True, "greeting"

        # Cảm ơn - chỉ khi câu ngắn
        if len(words) <= 10:
            thanks_patterns = ["cảm ơn", "thanks", "thank you", "cám ơn", "thank"]
            if any(t in query_lower for t in thanks_patterns):
                return True, "thanks"

        # Tạm biệt - chỉ khi câu ngắn
        if len(words) <= 10:
            goodbyes = ["tạm biệt", "bye", "goodbye", "chào tạm biệt", "bye bye", "bái bai"]
            if any(g in query_lower for g in goodbyes):
                return True, "goodbye"

        # Hỏi khỏe - pattern cụ thể
        health_checks = ["khỏe không", "how are you", "bạn thế nào", "bạn ra sao", "có khỏe"]
        if any(h in query_lower for h in health_checks):
            return True, "health_check"

        return False, None

    def _get_greeting_response(self, greeting_type: str) -> str:
        """Trả về câu trả lời cho các câu giao tiếp cơ bản"""
        responses = {
            "greeting": "Xin chào! Tôi là trợ lý ảo của VNPT Money. Tôi có thể giúp gì cho bạn hôm nay?",
            "thanks": "Rất vui được giúp đỡ bạn! Nếu còn thắc mắc gì về VNPT Money, đừng ngần ngại hỏi tôi nhé.",
            "goodbye": "Tạm biệt! Chúc bạn có trải nghiệm tốt với VNPT Money. Hẹn gặp lại!",
            "health_check": "Tôi khỏe, cảm ơn bạn! Tôi luôn sẵn sàng hỗ trợ bạn về VNPT Money. Bạn cần tôi giúp gì?"
        }
        return responses.get(greeting_type, "")

    def chat(self, query: str):
        """
        Main chat function

        Args:
            query: Câu hỏi của user

        Returns:
            dict với keys: answer, sources, confidence, relevance_score
        """
        # Ngưỡng độ liên quan cố định - chỉ admin có thể thay đổi trong code
        RELEVANCE_THRESHOLD = 0.25  # 0.25 = balanced, 0.2 = loose, 0.3 = strict

        try:
            # 0. Kiểm tra câu giao tiếp cơ bản TRƯỚC
            is_greeting, greeting_type = self._is_greeting(query)
            if is_greeting:
                logger.info(f"Phát hiện câu giao tiếp: {greeting_type}")
                return {
                    "answer": self._get_greeting_response(greeting_type),
                    "sources": [],
                    "confidence": "high",
                    "relevance_score": 1.0,
                }

            # 1. Kiểm tra mức độ liên quan
            is_relevant, score = self._check_relevance(query, RELEVANCE_THRESHOLD)

            if not is_relevant:
                logger.info(f"Câu hỏi không liên quan (score: {score:.4f})")
                return {
                    "answer": "Xin lỗi, tôi là trợ lý chuyên về VNPT Money nên chỉ có thể tư vấn các vấn đề liên quan đến ứng dụng và dịch vụ ví điện tử thôi ạ. Bạn có câu hỏi nào về VNPT Money mà tôi có thể giúp không?",
                    "sources": [],
                    "relevance_score": score,
                    "confidence": "low",
                }

            # 2. Invoke chain
            result = self.chain.invoke(
                {"question": query}, config={"configurable": {"session_id": "default"}}
            )

            answer = result["answer"]
            source_docs = result["source_documents"]

            # 3. Extract sources
            if not source_docs:
                return {
                    "answer": "Xin lỗi, hiện tại tôi chưa có thông tin về vấn đề này. Để được hỗ trợ chính xác nhất, bạn vui lòng liên hệ hotline 1900 8198 hoặc email support@vnptmoney.vn nhé!",
                    "sources": [],
                    "relevance_score": score,
                    "confidence": "low",
                }

            sources = []
            for doc in source_docs:
                sheet_name = doc.metadata.get("sheet_name", "")
                source_name = doc.metadata.get("source", "Unknown")
                if sheet_name:
                    sources.append(f"{source_name} - {sheet_name}")
                else:
                    sources.append(source_name)

            # 4. Đánh giá confidence
            confidence = "high"
            if self._is_generic_no_info_response(answer):
                confidence = "low"
            elif score < 0.7:
                confidence = "medium"

            logger.info(f"Confidence: {confidence}, Sources: {len(sources)}")

            return {
                "answer": answer,
                "sources": list(dict.fromkeys(sources)),
                "confidence": confidence,
                "relevance_score": score,
            }

        except Exception as e:
            logger.error(f"Lỗi chat: {e}")
            return {"answer": f"Lỗi: {str(e)}", "sources": [], "confidence": "error"}

    def clear_memory(self):
        """Xóa lịch sử chat"""
        self.memory.clear()
        logger.info("Đã xóa lịch sử")

    def reload_data(self):
        """Reload dữ liệu từ data/"""
        logger.info("Reload dữ liệu...")
        self._setup_system()
        self._setup_chain()
        logger.info("✅ Đã reload")
