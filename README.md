# VNPT Money Chatbot

Hệ thống chatbot hỗ trợ khách hàng VNPT Money với **hai kiến trúc RAG** (Retrieval Augmented Generation):

- **GraphRAG**: Sử dụng Neo4j Knowledge Graph + vLLM (Qwen2.5-DPO finetuned)
- **TraditionalRAG**: Sử dụng FAISS + Hybrid Search (BM25 + Dense) + Google Gemini

## Tính năng chính

| Tính năng | GraphRAG | TraditionalRAG |
|-----------|----------|----------------|
| **Vector Store** | Neo4j Knowledge Graph | FAISS |
| **LLM** | vLLM (Qwen2.5-DPO) | Google Gemini 2.5 Flash |
| **Search** | Graph traversal | Hybrid (Dense + BM25) |
| **Intent Classification** | Yes | No |
| **Entity Extraction** | Yes (LLM-based) | No |
| **Conversation Memory** | Mem0 | In-memory |
| **Follow-up Detection** | Yes | No |
| **Embedding** | ChromaDB | Vietnamese-SBERT |

## Kiến trúc

```
                            ┌─────────────────────────────────────────────────────┐
                            │                    VNPT Money Chatbot               │
                            └────────────────────────┬────────────────────────────┘
                                                     │
                    ┌────────────────────────────────┼────────────────────────────────┐
                    │                                │                                │
                    ▼                                ▼                                ▼
        ┌───────────────────┐            ┌───────────────────┐            ┌───────────────────┐
        │    GraphRAG       │            │   TraditionalRAG  │            │   Shared Data     │
        │  (Neo4j + vLLM)   │            │  (FAISS + Gemini) │            │                   │
        └─────────┬─────────┘            └─────────┬─────────┘            └─────────┬─────────┘
                  │                                │                                │
    ┌─────────────┼─────────────┐     ┌────────────┼────────────┐                   │
    ▼             ▼             ▼     ▼            ▼            ▼                   ▼
┌───────┐   ┌─────────┐   ┌─────────┐ ┌──────┐ ┌───────┐ ┌─────────┐      ┌─────────────────┐
│Intent │   │ Entity  │   │ Focused │ │FAISS │ │Hybrid │ │ Gemini  │      │ Vietnamese-SBERT│
│Classif│   │Extractor│   │ Answer  │ │Index │ │Search │ │   LLM   │      │   (finetuned)   │
└───────┘   └─────────┘   └─────────┘ └──────┘ └───────┘ └─────────┘      └─────────────────┘
                  │                                │                                │
                  ▼                                ▼                                ▼
        ┌───────────────────┐            ┌───────────────────┐            ┌───────────────────┐
        │   Neo4j Graph     │            │  BM25 + Dense     │            │   FAQ Data        │
        │  Knowledge Base   │            │  Vector Search    │            │  (Excel + JSON)   │
        └───────────────────┘            └───────────────────┘            └───────────────────┘
```

## Cấu trúc thư mục

```
Chatbot/
├── GraphRAG/                    # GraphRAG system
│   ├── app_streamlit.py         # Streamlit UI
│   ├── chatbot.py               # Main chatbot class
│   ├── config.py                # Configuration (vLLM, Neo4j, OpenAI)
│   ├── neo4j_connector.py       # Neo4j connection
│   ├── neo4j_rag_engine.py      # RAG engine với Neo4j
│   ├── intent_classifier.py     # Intent classification
│   ├── enhanced_entity_extractor.py  # Hybrid entity extraction
│   ├── llm_entity_extractor.py  # LLM-based entity extraction
│   ├── focused_answer_extractor.py   # Extract focused answers
│   ├── intent_answer_extractor.py    # Intent-based extraction
│   ├── conversation_context_manager.py  # Context management
│   ├── follow_up_detector.py    # Follow-up question detection
│   ├── memory_manager.py        # Mem0 memory
│   ├── step_tracker.py          # Step tracking
│   └── requirements.txt
│
├── TraditionalRAG/              # Traditional RAG (backup)
│   ├── app.py
│   ├── rag_chatbot.py
│   ├── hybrid_search.py
│   ├── faq_loader.py
│   └── requirements.txt
│
├── app.py                       # TraditionalRAG entry point
├── rag_chatbot.py               # RAG chatbot class
├── hybrid_search.py             # Hybrid search (BM25 + Dense)
├── faq_loader.py                # FAQ data loader
├── requirements.txt
│
├── models/
│   └── vnpt-sbert-mnrl/         # Finetuned Vietnamese-SBERT
│
├── faiss_index/                 # FAISS vector index
│   ├── index.faiss
│   └── index.pkl
│
├── data/
│   ├── CHATBOT - Kịch bản trả lời.xlsx  # FAQ source
│   └── paraphrase_documents.json         # Paraphrased FAQs
│
└── .env                         # Environment variables
```

## Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/GiangNV-HUST/vnpt-money-chatbot.git
cd vnpt-money-chatbot/Chatbot
```

### 2. Cài đặt dependencies

```bash
# Cho GraphRAG
pip install -r GraphRAG/requirements.txt

# Cho TraditionalRAG
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Tạo file `.env`:

```env
# === GRAPHRAG CONFIGURATION ===

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=vnptmoney

# LLM Provider: "vllm" hoặc "openai"
LLM_PROVIDER=vllm

# vLLM Configuration (self-hosted Qwen2.5-DPO)
VLLM_API_BASE=http://10.144.47.51:8020/v1
VLLM_MODEL=vnpt-money-dpo
VLLM_API_KEY=EMPTY
VLLM_TIMEOUT=120

# OpenAI Configuration (backup)
OPENAI_API_KEY=sk-xxx

# === TRADITIONALRAG CONFIGURATION ===

# Google Gemini API
GOOGLE_API_KEY=your_google_api_key
```

## Chạy ứng dụng

### GraphRAG (Recommended cho production)

```bash
# 1. Khởi động Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# 2. Khởi động vLLM server (trên GPU server)
python -m vllm.entrypoints.openai.api_server \
    --model ./training/outputs/final-dpo-qwen25 \
    --served-model-name vnpt-money-dpo \
    --port 8020 \
    --host 0.0.0.0 \
    --gpu-memory-utilization 0.25

# 3. Chạy Streamlit UI
cd GraphRAG
streamlit run app_streamlit.py --server.port 8501
```

Truy cập: http://localhost:8501

### TraditionalRAG (Lightweight, không cần GPU)

```bash
streamlit run app.py --server.port 8502
```

Truy cập: http://localhost:8502

## LLM Configuration

### vLLM (Self-hosted) - Recommended

```python
# GraphRAG/config.py
LLM_PROVIDER = "vllm"
VLLM_API_BASE = "http://10.144.47.51:8020/v1"
VLLM_MODEL = "vnpt-money-dpo"
```

**Ưu điểm:**
- Không tốn phí API
- Dữ liệu on-premise (bảo mật)
- Model đã finetuned cho domain VNPT Money

### OpenAI (Backup)

```python
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "sk-xxx"
```

### Google Gemini (TraditionalRAG)

```python
GOOGLE_API_KEY = "your_key"
# Model: gemini-2.5-flash-lite
```

## Hybrid Search (TraditionalRAG)

Hệ thống kết hợp hai phương pháp tìm kiếm:

| Method | Ưu điểm | Nhược điểm |
|--------|---------|------------|
| **Dense (FAISS)** | Semantic understanding, xử lý synonyms | Cần embedding model tốt |
| **Sparse (BM25)** | Exact keyword matching, nhanh | Không hiểu ngữ nghĩa |

**Reciprocal Rank Fusion (RRF):**
```
score = α × dense_score + (1-α) × sparse_score
```
- `α = 0.5`: Cân bằng
- `α > 0.5`: Ưu tiên semantic
- `α < 0.5`: Ưu tiên keyword

## GraphRAG Features

### Intent Classification

| Intent | Mô tả | Ví dụ |
|--------|-------|-------|
| `FEE` | Hỏi về phí | "Phí chuyển tiền bao nhiêu?" |
| `LIMIT` | Hỏi về hạn mức | "Hạn mức chuyển tiền tối đa?" |
| `TIME` | Hỏi về thời gian | "Bao lâu tiền về tài khoản?" |
| `HOW_TO` | Hướng dẫn | "Làm sao để nạp tiền?" |
| `TROUBLESHOOT` | Xử lý lỗi | "Chuyển tiền thất bại phải làm sao?" |
| `REQUIREMENT` | Điều kiện | "Cần gì để liên kết ngân hàng?" |

### Knowledge Graph Schema

**Nodes:**
- `FAQ`: Câu hỏi + Câu trả lời
- `Topic`: Chủ đề (Nạp tiền, Rút tiền, ...)
- `Service`: Dịch vụ (VNPT Money, VNPT Pay)
- `Bank`: Ngân hàng
- `Error`: Lỗi/vấn đề
- `Action`: Hành động UI

**Relationships:**
```cypher
(FAQ)-[:ABOUT]->(Topic)
(FAQ)-[:MENTIONS_SERVICE]->(Service)
(FAQ)-[:MENTIONS_BANK]->(Bank)
(FAQ)-[:DESCRIBES_ERROR]->(Error)
(FAQ)-[:SIMILAR_TO {score}]->(FAQ)
```

## Performance

| Metric | GraphRAG (vLLM) | TraditionalRAG (Gemini) |
|--------|-----------------|-------------------------|
| Response Time | 2-5s | 1-3s |
| Cost | Free (self-hosted) | ~$0.0001/query |
| Privacy | On-premise | Cloud |
| Quality | Domain-optimized | General |
| Complexity | High | Low |

## Troubleshooting

### Neo4j connection failed

```bash
# Kiểm tra Neo4j
curl http://localhost:7474
docker ps | grep neo4j
```

### vLLM connection failed

```bash
# Kiểm tra vLLM server
curl http://10.144.47.51:8020/v1/models

# Corporate proxy fix (đã implement trong code)
# trust_env=False trong httpx client
```

### FAISS index error

```bash
# Xóa và rebuild index
rm -rf faiss_index/
python -c "from rag_chatbot import RAGChatbotSystem; RAGChatbotSystem()"
```

### Encoding errors (Windows)

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

## API Reference

### GraphRAG Chatbot

```python
from GraphRAG.chatbot import GraphRAGChatbot

chatbot = GraphRAGChatbot()
response = chatbot.chat("Làm sao để nạp tiền?")
# Returns: {"answer": "...", "intent": "HOW_TO", "entities": [...], "confidence": 0.95}
```

### TraditionalRAG Chatbot

```python
from rag_chatbot import RAGChatbotSystem

chatbot = RAGChatbotSystem(use_hybrid_search=True, hybrid_alpha=0.5)
response = chatbot.chat("Phí chuyển tiền bao nhiêu?")
# Returns: {"answer": "...", "sources": [...], "confidence": "high"}
```

### vLLM API (OpenAI-compatible)

```bash
curl http://10.144.47.51:8020/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vnpt-money-dpo",
    "messages": [{"role": "user", "content": "Xin chào"}]
  }'
```

## Development

### Thêm FAQ mới

1. Cập nhật file `data/CHATBOT - Kịch bản trả lời.xlsx`
2. Chạy reload:
   - GraphRAG: Reload qua Streamlit UI
   - TraditionalRAG: Click "Reload dữ liệu" hoặc xóa `faiss_index/`

### Finetune embedding model

```python
# Xem models/finetune_mnrl_kaggle.py
# Model output: models/vnpt-sbert-mnrl/
```

### Chuyển đổi LLM provider

```bash
# Sử dụng vLLM
export LLM_PROVIDER=vllm

# Sử dụng OpenAI
export LLM_PROVIDER=openai
```

## License

MIT License

## Author

- **GiangNV** - VNPT Media
- AI Assistant: Claude (Anthropic)

## Support

1. Kiểm tra logs trong terminal
2. Verify Neo4j: http://localhost:7474
3. Verify vLLM: `curl http://server:8020/v1/models`
4. Tạo issue trên GitHub
