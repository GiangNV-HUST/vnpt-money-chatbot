# VNPT Money GraphRAG Chatbot

Chatbot hỗ trợ khách hàng VNPT Money sử dụng **GraphRAG** (Graph-based Retrieval Augmented Generation) kết hợp với **LLM** (Large Language Model).

## Tính năng chính

- **GraphRAG**: Sử dụng Neo4j Knowledge Graph để lưu trữ và truy vấn FAQ
- **Multi-LLM Support**: Hỗ trợ OpenAI API và vLLM (self-hosted Qwen2.5-DPO)
- **Intent Classification**: Phân loại ý định người dùng (FEE, LIMIT, TIME, HOW_TO, TROUBLESHOOT, ...)
- **Entity Extraction**: Trích xuất entities từ câu hỏi (ngân hàng, dịch vụ, lỗi, ...)
- **Focused Answer Extraction**: Trả lời đúng trọng tâm thay vì trả về toàn bộ FAQ
- **Conversation Memory**: Theo dõi ngữ cảnh hội thoại với Mem0
- **Follow-up Detection**: Phát hiện câu hỏi tiếp nối để duy trì context
- **Vietnamese Support**: Hỗ trợ đầy đủ tiếng Việt

## Kiến trúc hệ thống

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│    Chatbot      │────▶│   Neo4j Graph   │
│  (app_streamlit)│     │   (chatbot.py)  │     │   (Knowledge)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  Intent   │ │  Entity   │ │  Focused  │
            │Classifier │ │ Extractor │ │ Extractor │
            └───────────┘ └───────────┘ └───────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   LLM (vLLM / OpenAI)   │
                    │   Qwen2.5-DPO Finetune  │
                    └─────────────────────────┘
```

## Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/GiangNV-HUST/vnpt-money-chatbot.git
cd vnpt-money-chatbot/Chatbot/GraphRAG
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Tạo file `.env`:

```env
# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=vnptmoney

# LLM Provider: "vllm" hoặc "openai"
LLM_PROVIDER=vllm

# vLLM Configuration (nếu dùng vLLM)
VLLM_API_BASE=http://10.144.47.51:8020/v1
VLLM_MODEL=vnpt-money-dpo

# OpenAI Configuration (nếu dùng OpenAI)
OPENAI_API_KEY=sk-xxx
```

### 4. Khởi động Neo4j

```bash
# Sử dụng Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

### 5. Khởi động vLLM Server (nếu dùng self-hosted model)

```bash
python -m vllm.entrypoints.openai.api_server \
    --model ./training/outputs/final-dpo-qwen25 \
    --served-model-name vnpt-money-dpo \
    --port 8020 \
    --host 0.0.0.0 \
    --gpu-memory-utilization 0.25 \
    --max-model-len 2048
```

## Chạy ứng dụng

### Streamlit UI (Recommended)

```bash
streamlit run app_streamlit.py --server.port 8501
```

Truy cập: http://localhost:8501

### Command Line

```bash
python chatbot.py
```

## Cấu trúc thư mục

```
GraphRAG/
├── config.py                    # Cấu hình hệ thống
├── chatbot.py                   # Chatbot chính
├── app_streamlit.py             # Giao diện Streamlit
│
├── neo4j_connector.py           # Kết nối Neo4j
├── neo4j_rag_engine.py          # RAG engine với Neo4j
│
├── intent_classifier.py         # Phân loại intent
├── enhanced_entity_extractor.py # Trích xuất entities (hybrid)
├── llm_entity_extractor.py      # Trích xuất entities (LLM)
│
├── focused_answer_extractor.py  # Trả lời đúng trọng tâm
├── intent_answer_extractor.py   # Trích xuất theo intent
│
├── conversation_context_manager.py  # Quản lý context hội thoại
├── follow_up_detector.py        # Phát hiện câu hỏi follow-up
├── memory_manager.py            # Mem0 memory manager
├── step_tracker.py              # Theo dõi các bước hướng dẫn
│
└── data/
    ├── chroma_db/               # Vector store (ChromaDB)
    └── mem0_chroma/             # Mem0 memory storage
```

## Cấu hình LLM

### Sử dụng vLLM (Self-hosted) - Recommended

```python
# config.py hoặc .env
LLM_PROVIDER = "vllm"
VLLM_API_BASE = "http://your-server:8020/v1"
VLLM_MODEL = "vnpt-money-dpo"
```

**Ưu điểm:**
- Không tốn phí API
- Dữ liệu không ra ngoài (on-premise)
- Model đã finetune cho domain VNPT Money

### Sử dụng OpenAI

```python
# config.py hoặc .env
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "sk-xxx"
```

### Chuyển đổi nhanh qua Environment Variable

```bash
# Dùng vLLM
export LLM_PROVIDER=vllm

# Dùng OpenAI
export LLM_PROVIDER=openai
```

## Knowledge Graph Schema

### Node Types

| Node | Mô tả | Ví dụ |
|------|-------|-------|
| `FAQ` | Câu hỏi + Trả lời | "Làm sao để nạp tiền?" |
| `Topic` | Chủ đề | Nạp tiền, Rút tiền, Chuyển tiền |
| `Service` | Dịch vụ | VNPT Money, VNPT Pay |
| `Bank` | Ngân hàng | Vietcombank, BIDV, Techcombank |
| `Error` | Lỗi/vấn đề | "Thông tin không hợp lệ" |
| `Feature` | Tính năng | QR code, OTP, Sinh trắc học |
| `Action` | Hành động UI | "Chọn Nạp tiền", "Nhập OTP" |
| `Requirement` | Điều kiện | "Có tài khoản ngân hàng" |
| `TimeFrame` | Thời gian | "2-3 ngày làm việc" |
| `Case` | Trường hợp xử lý | "Nếu trạng thái Thành công" |

### Relationship Types

```
(FAQ)-[:ABOUT]->(Topic)
(FAQ)-[:MENTIONS_SERVICE]->(Service)
(FAQ)-[:MENTIONS_BANK]->(Bank)
(FAQ)-[:DESCRIBES_ERROR]->(Error)
(FAQ)-[:SUGGESTS_ACTION]->(Action)
(FAQ)-[:HAS_CASE]->(Case)
(FAQ)-[:SIMILAR_TO {score}]->(FAQ)
```

## Intent Types

| Intent | Mô tả | Ví dụ |
|--------|-------|-------|
| `FEE` | Hỏi về phí | "Phí chuyển tiền là bao nhiêu?" |
| `LIMIT` | Hỏi về hạn mức | "Hạn mức chuyển tiền tối đa?" |
| `TIME` | Hỏi về thời gian | "Bao lâu tiền về tài khoản?" |
| `HOW_TO` | Hướng dẫn thực hiện | "Làm sao để nạp tiền?" |
| `TROUBLESHOOT` | Xử lý lỗi/sự cố | "Chuyển tiền thất bại phải làm sao?" |
| `REQUIREMENT` | Điều kiện/yêu cầu | "Cần gì để liên kết ngân hàng?" |
| `COMPARISON` | So sánh | "Khác nhau giữa nạp tiền và chuyển khoản?" |
| `GENERAL` | Câu hỏi chung | "VNPT Money là gì?" |

## API Endpoints (vLLM)

vLLM server expose OpenAI-compatible API:

```bash
# List models
curl http://localhost:8020/v1/models

# Chat completion
curl http://localhost:8020/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vnpt-money-dpo",
    "messages": [{"role": "user", "content": "Xin chào"}]
  }'
```

## Neo4j Query Examples

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

## Troubleshooting

### Neo4j connection failed

```bash
# Kiểm tra Neo4j đang chạy
curl http://localhost:7474

# Kiểm tra Docker container
docker ps | grep neo4j
```

### vLLM connection failed

```bash
# Kiểm tra vLLM server
curl http://your-server:8020/v1/models

# Nếu có corporate proxy, code đã set trust_env=False
```

### OpenAI quota exceeded (429)

```bash
# Chuyển sang vLLM
export LLM_PROVIDER=vllm

# Hoặc nạp thêm credit OpenAI
```

### Encoding errors (Windows)

```python
# Thêm vào đầu script
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

## Performance

| Metric | vLLM (Qwen2.5-DPO) | OpenAI (gpt-4o-mini) |
|--------|-------------------|---------------------|
| Response Time | ~2-5s | ~1-3s |
| Cost | Free (self-hosted) | ~$0.15/1M tokens |
| Privacy | On-premise | Cloud |
| Quality | Domain-optimized | General |

## Files đã update cho vLLM

| File | Thay đổi |
|------|----------|
| `config.py` | Thêm VLLM_* configs |
| `chatbot.py` | `_initialize_vllm()`, `_call_vllm()` |
| `llm_entity_extractor.py` | vLLM support |
| `focused_answer_extractor.py` | vLLM support |
| `follow_up_detector.py` | vLLM support |
| `intent_answer_extractor.py` | vLLM support |

## License

MIT License

## Author

- **GiangNV** - VNPT Media
- AI Assistant: Claude (Anthropic)

## Support

Nếu gặp vấn đề:
1. Kiểm tra logs trong terminal
2. Verify Neo4j connection: http://localhost:7474
3. Verify vLLM server: `curl http://server:8020/v1/models`
4. Tạo issue trên GitHub
