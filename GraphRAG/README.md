# VNPT Money GraphRAG Chatbot (LLM-based)

Hệ thống chatbot FAQ cho VNPT Money sử dụng **Knowledge Graph** và **LLM** để trả lời câu hỏi.

## 🎯 Tính năng

- ✅ **LLM-based Entity Extraction**: Sử dụng OpenAI ChatGPT (hoặc Google Gemini) để trích xuất entities và relationships
- ✅ **Knowledge Graph**: Neo4j graph database để lưu trữ tri thức có cấu trúc
- ✅ **Semantic Search**: Tìm kiếm ngữ nghĩa với embeddings
- ✅ **GraphRAG**: Kết hợp graph traversal và semantic retrieval
- ✅ **Vietnamese Support**: Hỗ trợ đầy đủ tiếng Việt
- ✅ **Flexible LLM Provider**: Hỗ trợ cả OpenAI và Gemini

## 📦 Cấu trúc Project

```
graphRAGChatBot/
├── config.py                        # Cấu hình
├── llm_entity_extractor.py         # LLM entity extractor
├── neo4j_connector.py              # Neo4j connector
├── neo4j_graph_builder_llm.py      # Graph builder (LLM-based)
├── neo4j_rag_engine.py             # RAG engine
├── chatbot.py                      # Chatbot interface
├── main.py                         # Main entry point
├── test_llm_extraction.py          # Test LLM extraction
├── visualize_graph_schema.py       # Visualize graph
├── requirements.txt                # Dependencies
├── README_LLM_EXTRACTION.md        # Chi tiết về LLM extraction
└── data/                           # Data directory
```

## 🚀 Quick Start

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình

Tạo file `.env` trong thư mục `graphRAGChatBot/`:

```env
# OpenAI API (Recommended)
OPENAI_API_KEY=sk-proj-your_openai_api_key_here

# Google Gemini API (Alternative)
GOOGLE_API_KEY=your_google_api_key_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=vnptmoney
```

**Lấy OpenAI API Key**: https://platform.openai.com/api-keys (Khuyến nghị)
**Lấy Google API Key**: https://makersuite.google.com/app/apikey (Alternative)

### 3. Khởi động Neo4j

**Sử dụng Docker:**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

**Hoặc cài đặt trực tiếp:**
Download từ: https://neo4j.com/download/

### 4. Test LLM Extraction

```bash
python test_openai_extraction.py
```

### 5. Build Knowledge Graph

**Test với 10 documents:**
```bash
python neo4j_graph_builder_llm.py --limit 10
```

**Build toàn bộ (803 documents):**
```bash
python neo4j_graph_builder_llm.py
```

### 6. Visualize Graph

```bash
python visualize_graph_schema.py
```

### 7. Chạy Chatbot

```bash
python main.py
```

## 📊 Knowledge Graph Schema

### Node Types

- **FAQ**: Câu hỏi + Trả lời
- **Topic**: Chủ đề (Nạp tiền, Rút tiền, Liên kết ngân hàng)
- **Section**: Phân loại chủ đề
- **Service**: Dịch vụ (VNPT Money, VNPT Pay)
- **Bank**: Ngân hàng (Vietinbank, Vietcombank, BIDV)
- **Error**: Thông báo lỗi
- **Action**: Hành động cần thực hiện
- **Requirement**: Điều kiện yêu cầu
- **Feature**: Tính năng ứng dụng
- **TimeFrame**: Khung thời gian

### Relationship Types

- **ABOUT**: (FAQ) → (Topic)
- **BELONGS_TO**: (FAQ) → (Section)
- **MENTIONS_SERVICE**: (FAQ) → (Service)
- **MENTIONS_BANK**: (FAQ) → (Bank)
- **DESCRIBES_ERROR**: (FAQ) → (Error)
- **SUGGESTS_ACTION**: (FAQ) → (Action)
- **SOLVES**: (FAQ) → (Error)
- **REQUIRES**: (Action) → (Requirement)
- **USES_FEATURE**: (Action) → (Feature)
- **HAS_TIMEFRAME**: (Action) → (TimeFrame)
- **SIMILAR_TO**: (FAQ) ↔ (FAQ) [với similarity score]

## 🔍 Query Examples (Neo4j Browser)

### Tìm FAQs về một topic

```cypher
MATCH (f:FAQ)-[:ABOUT]->(t:Topic {name: 'Nạp tiền'})
RETURN f.question, f.answer
LIMIT 10
```

### Tìm lỗi và giải pháp

```cypher
MATCH (f:FAQ)-[:DESCRIBES_ERROR]->(e:Error)
MATCH (f)-[:SUGGESTS_ACTION]->(a:Action)
WHERE e.name CONTAINS 'không hợp lệ'
RETURN e.name, f.question, collect(a.name) as solutions
```

### Tìm FAQs tương tự

```cypher
MATCH (f1:FAQ)-[r:SIMILAR_TO]->(f2:FAQ)
WHERE r.similarity_score > 0.8
RETURN f1.question, f2.question, r.similarity_score
ORDER BY r.similarity_score DESC
LIMIT 10
```

### Visualize toàn bộ graph của một FAQ

```cypher
MATCH (f:FAQ {id: 'FAQ_0'})
MATCH (f)-[r]->(e)
RETURN f, r, e
```

## 📖 Chi tiết

**Quick Start với OpenAI**: [QUICKSTART_OPENAI.md](QUICKSTART_OPENAI.md)

**Hướng dẫn chi tiết**: [OPENAI_SETUP.md](OPENAI_SETUP.md) để biết:
- Setup OpenAI API
- So sánh OpenAI vs Gemini
- Chi phí và models
- Troubleshooting
- Performance optimization

## 🛠️ Development

### Project Structure

```
Core Components:
├── config.py                 # Configuration settings
├── neo4j_connector.py        # Neo4j database interface
├── llm_entity_extractor.py   # LLM-based extraction
├── neo4j_graph_builder_llm.py # Graph construction
└── neo4j_rag_engine.py       # RAG query engine

Application:
├── chatbot.py                # Chatbot logic
└── main.py                   # CLI interface

Testing & Utilities:
├── test_openai_extraction.py # Test OpenAI extraction
└── visualize_graph_schema.py # Graph visualization
```

### Extending the System

**Thêm entity type mới:**

1. Cập nhật prompt trong `llm_entity_extractor.py`
2. Thêm logic xử lý trong `neo4j_graph_builder_llm.py`
3. Test với `test_openai_extraction.py`

**Thêm relationship type mới:**

1. Cập nhật ĐỊNH NGHĨA CÁC LOẠI MỐI QUAN HỆ trong prompt
2. Thêm logic tạo relationship trong `_create_relationship_from_extraction`

## 📊 Performance

| Metric | OpenAI (gpt-4o-mini) | Gemini (flash) |
|--------|---------------------|----------------|
| Documents | 803 FAQs | 803 FAQs |
| Build Time | ~30-40 minutes | ~45-60 minutes |
| LLM API Calls | ~803 requests | ~803 requests |
| Cost | ~$0.80 | Free (có quota) |
| Graph Nodes | ~2000-3000 nodes | ~1500-2500 nodes |
| Relationships | ~5000-7000 edges | ~4000-6000 edges |
| Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Rate Limiting:**
- OpenAI Paid Tier: 3,500 requests/minute
- Google Gemini Free Tier: 60 requests/minute
- Script tự động thêm delay để tránh rate limiting

## 🐛 Troubleshooting

### "OpenAI API Key not found"
- Kiểm tra file `.env` có `OPENAI_API_KEY`
- Verify API key valid tại https://platform.openai.com/api-keys

### "Unable to connect to Neo4j"
- Kiểm tra Neo4j đang chạy: http://localhost:7474
- Verify credentials trong `.env`
- Check firewall settings

### "Insufficient quota" (OpenAI)
- Thêm payment method tại https://platform.openai.com/account/billing
- Nạp tối thiểu $5

### Rate Limiting
- Sử dụng `--limit` để test với ít documents
- Script tự động sleep 1s mỗi 10 requests
- OpenAI paid tier có rate limit cao hơn

## 📝 License

MIT License

## 📧 Support

Nếu gặp vấn đề:
1. Xem [QUICKSTART_OPENAI.md](QUICKSTART_OPENAI.md) cho hướng dẫn nhanh
2. Xem [OPENAI_SETUP.md](OPENAI_SETUP.md) cho troubleshooting chi tiết
3. Kiểm tra logs trong `logs/`
4. Tạo issue trên GitHub
