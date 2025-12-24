# GraphRAG Chatbot - Hướng Dẫn Chạy

## Giới Thiệu

GraphRAG Chatbot sử dụng **Neo4j Knowledge Graph** để tổ chức và truy vấn thông tin FAQ một cách thông minh.

### Ưu Điểm

✅ **Hiểu ngữ cảnh**: Theo dõi conversation history và previous steps

✅ **Tách Case nodes**: Trả về đúng phương thức/điều kiện được hỏi

✅ **Graph traversal**: Tìm kiếm thông tin liên quan qua relationships

✅ **Hybrid search**: Kết hợp graph + semantic + keyword search

## Yêu Cầu Hệ Thống

### 1. Neo4j Database

**Cài đặt Neo4j Desktop**:
- Download: https://neo4j.com/download/
- Tạo database mới với password trong file `.env`

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Embedding Model

Model SBERT đã được train: `models/vnpt-sbert-mnrl/`

## Cấu Hình

### File `.env`

```env
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Model Paths
EMBEDDING_MODEL_PATH=../models/vnpt-sbert-mnrl
```

## Setup Database

### Bước 1: Tạo Knowledge Graph

```bash
# Build graph from paraphrase_documents.json
python neo4j_graph_builder_llm.py
```

### Bước 2: Migrate Step Nodes

```bash
# Add Step nodes cho các process
python migrate_steps_to_neo4j.py
```

### Bước 3: Tạo Case Nodes

```bash
# Tự động tạo Case nodes cho FAQs có nhiều methods/conditions
python auto_create_case_nodes.py --execute
```

### Bước 4: Verify

```bash
# Kiểm tra tất cả Case nodes
python verify_all_cases.py
```

## Chạy Chatbot

### 1. CLI Interface

```bash
python main.py
```

Tương tác qua command line:
```
> Tôi có thể nạp tiền từ ngân hàng vào Mobile Money như thế nào?
> Bước tiếp theo là gì?
> exit
```

### 2. Web UI (Streamlit)

```bash
streamlit run app_streamlit.py
```

Mở browser tại: http://localhost:8501

### 3. Python API

```python
from chatbot import GraphRAGChatbot

# Initialize
bot = GraphRAGChatbot()

# Chat
response = bot.chat("Tôi muốn nạp tiền từ ngân hàng liên kết")
print(response)

# Follow-up với context
response = bot.chat("Bước tiếp theo là gì?")
print(response)

# Clear history
bot.clear_history()
```

## Các Tính Năng Chính

### 1. Case-Based Response

Bot tự động chọn đúng Case dựa vào keywords:

```python
# Query: "nạp tiền từ liên kết"
# → Returns: Case "Nạp tiền từ ngân hàng liên kết trực tiếp" (5 steps)

# Query: "nạp tiền bằng chuyển khoản"
# → Returns: Case "Nạp bằng Chuyển khoản ngân hàng" (QR method)
```

### 2. Context-Aware

```python
# First message
bot.chat("Tôi muốn nạp tiền Mobile Money")

# Follow-up (bot nhớ context)
bot.chat("Bước tiếp theo là gì?")  # Trả về bước 2, 3...
```

### 3. Multi-Modal Search

- **Graph traversal**: Tìm qua relationships (HAS_STEP, MENTIONS_SERVICE, etc.)
- **Semantic search**: Vector similarity với SBERT embeddings
- **Keyword boost**: Boost exact keyword matches

## Testing

### Test Case Nodes

```bash
# Test các Case nodes đã tạo
python test_case_nodes.py
```

### Test Specific Query

```bash
# Test query cụ thể
python test_new_cases.py
```

## Maintenance

### Update Embeddings

Khi có FAQ mới:

```bash
python update_embeddings.py
```

### Visualize Graph

```bash
python visualize_graph_schema.py
```

### Export Database

```bash
python export_neo4j_database.py
```

## Troubleshooting

### Lỗi kết nối Neo4j

```
Neo.ClientError.Security.Unauthorized
```

**Fix**: Kiểm tra password trong `.env`

### Lỗi Case nodes không được chọn đúng

**Debug**:
```bash
python check_faq_answer.py
```

**Fix**: Cập nhật keywords trong `neo4j_rag_engine.py:671-719`

### Lỗi encoding trên Windows

**Fix**: Thêm vào đầu file:
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

## Files Quan Trọng

| File | Mô tả |
|------|-------|
| `chatbot.py` | Main chatbot class |
| `neo4j_rag_engine.py` | RAG engine với graph traversal |
| `neo4j_connector.py` | Neo4j database connector |
| `conversation_context_manager.py` | Context tracking |
| `auto_create_case_nodes.py` | Tự động tạo Case nodes |
| `verify_all_cases.py` | Verify Case nodes |

## Tài Liệu

- [CASE_NODES_SUMMARY.md](CASE_NODES_SUMMARY.md) - Chi tiết Case nodes implementation
- [CASE_NODES_UPDATE_REPORT.md](CASE_NODES_UPDATE_REPORT.md) - Báo cáo update Case nodes
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Tổng quan project

## Support

Nếu gặp vấn đề, check:
1. Neo4j database đang chạy
2. `.env` file có đúng credentials
3. `paraphrase_documents.json` tồn tại trong `../data/`
4. Embedding model tồn tại tại path trong `.env`
