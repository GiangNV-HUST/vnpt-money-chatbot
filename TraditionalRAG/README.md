# Traditional RAG Chatbot

## Giới Thiệu

Traditional RAG chatbot sử dụng **vector similarity search** đơn giản để tìm câu trả lời từ FAQ database.

### So Sánh với GraphRAG

| Feature | Traditional RAG | GraphRAG |
|---------|----------------|----------|
| **Database** | In-memory/FAISS | Neo4j Graph |
| **Search** | Vector similarity | Graph + Semantic + Keyword |
| **Context** | ❌ Không | ✅ Có |
| **Case handling** | ❌ Không | ✅ Có |
| **Complexity** | Đơn giản | Phức tạp |
| **Accuracy** | Trung bình | Cao |

## Cài Đặt

### 1. Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configuration

File `.env`:

```env
OPENAI_API_KEY=your_api_key_here
```

## Chạy Chatbot

### Flask Web App

```bash
python app.py
```

Mở browser: http://localhost:5000

### Python API

```python
from rag_chatbot import RAGChatbot

# Initialize
bot = RAGChatbot()

# Load FAQs
bot.load_faqs("../data/paraphrase_documents.json")

# Chat
response = bot.chat("Làm thế nào để nạp tiền?")
print(response)
```

## Cách Hoạt Động

### 1. Load FAQs

```python
# Load from JSON
bot.load_faqs("data/faqs.json")

# Embeddings được tạo và lưu trong FAISS index
```

### 2. Search

```python
# User query
query = "Nạp tiền từ ngân hàng"

# Encode query
query_embedding = bot.encode(query)

# Search top-k similar FAQs
results = bot.search(query_embedding, k=3)

# Return most similar FAQ answer
return results[0]['answer']
```

### 3. Hybrid Search (Optional)

File `hybrid_search.py` kết hợp:
- BM25 (keyword matching)
- Semantic similarity (vector search)

```python
from hybrid_search import HybridSearch

searcher = HybridSearch()
results = searcher.search(query, k=5)
```

## Files

- `rag_chatbot.py` - Main RAG implementation
- `hybrid_search.py` - Hybrid search (BM25 + semantic)
- `faq_loader.py` - Load và process FAQ data
- `app.py` - Flask web interface

## Ưu Điểm

✅ **Đơn giản**: Dễ implement và maintain

✅ **Nhanh**: Vector search rất nhanh

✅ **Không cần DB**: Chạy in-memory hoặc FAISS

## Nhược Điểm

❌ **Không hiểu context**: Mỗi query độc lập

❌ **Không tách Case**: Trả về toàn bộ FAQ answer

❌ **Limited reasoning**: Chỉ dựa vào similarity

## Khi Nào Dùng

- **Prototype nhanh**: Cần test nhanh với FAQ dataset
- **Simple use case**: Chỉ cần Q&A đơn giản
- **Limited resources**: Không muốn setup Neo4j

## Migration lên GraphRAG

Nếu muốn upgrade sang GraphRAG:

```bash
cd ../GraphRAG

# Setup Neo4j (xem HOW_TO_RUN.md)
python neo4j_graph_builder_llm.py

# Run GraphRAG chatbot
python main.py
```

GraphRAG cung cấp:
- Context-aware conversations
- Case-based responses
- Graph traversal
- Better accuracy
