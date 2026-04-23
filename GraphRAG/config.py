"""
Configuration file for GraphRAG Chatbot
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Data paths
RAW_DATA_PATH = PROJECT_ROOT.parent / "data" / "paraphrase_documents.json"
GRAPH_DB_PATH = DATA_DIR / "knowledge_graph.db"

# API Keys (set in .env file)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LLM Configuration
# Provider: "openai" | "vllm"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "vllm")

# OpenAI Configuration (when LLM_PROVIDER = "openai")
# Supported models: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
LLM_MODEL = "gpt-4o-mini"  # Recommended: gpt-4o-mini (fast, cheap, good quality)
LLM_TEMPERATURE = 0.1  # Low temperature for consistent extraction
LLM_MAX_TOKENS = 4096  # Increased to allow for longer, detailed responses

# vLLM Configuration (when LLM_PROVIDER = "vllm")
# For self-hosted Qwen2.5-DPO finetune model on A100
VLLM_API_BASE = os.getenv("VLLM_API_BASE", "http://10.144.47.51:8020/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "vnpt-money-dpo")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")  # vLLM doesn't require real API key
VLLM_TIMEOUT = int(os.getenv("VLLM_TIMEOUT", "120"))  # Higher timeout for large models

# Embedding Configuration
# Using custom finetuned model for VNPT Money domain
EMBEDDING_MODEL = str(PROJECT_ROOT.parent / "models" / "vnpt-sbert-mnrl")
EMBEDDING_DIMENSION = 384

# Graph Database Configuration
GRAPH_DB_TYPE = "neo4j"  # Options: "networkx", "neo4j"

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "vnptmoney")  # Database name
USE_NEO4J = True  # Set to True to use Neo4j (now default)

# Graph Configuration
MAX_GRAPH_DEPTH = 3  # Maximum depth for graph traversal
MIN_SIMILARITY_SCORE = 0.7  # Minimum similarity for RELATED_TO edges
MAX_RELATED_QUESTIONS = 5  # Maximum related questions per node

# RAG Configuration
TOP_K_RETRIEVAL = 5  # Number of relevant nodes to retrieve (default for UI)
CONTEXT_WINDOW = 3  # Number of hops in graph traversal
ENABLE_RERANKING = True  # Enable result reranking

# Query Classification
SIMPLE_QUERY_THRESHOLD = 0.8  # Confidence threshold for simple queries
ENABLE_HYBRID_MODE = True  # Enable Vector + Graph hybrid

# Hybrid Search Weights (must sum to 1.0)
# UPDATED: Prioritize entity-based graph matching to reduce semantic search contamination
HYBRID_WEIGHT_ENTITY_GRAPH = 0.8  # Entity-based graph search (80% - increased to prioritize exact entity matches)
HYBRID_WEIGHT_SEMANTIC = 0.2      # Semantic similarity search (20% - reduced to minimize contamination from previous queries)
HYBRID_WEIGHT_KEYWORD = 0.0       # Keyword search (disabled in hybrid mode)

# Hybrid Entity Matching (NEW!)
USE_HYBRID_ENTITY_MATCHING = False  # Use hybrid (rule-based + semantic) for entity matching in graph scoring (DISABLED - requires PyTorch)
HYBRID_ENTITY_USE_SEMANTIC = False  # Enable semantic matching in hybrid entity matcher (requires embedding model) (DISABLED - requires PyTorch)

# Vector Store Configuration (for hybrid mode)
VECTOR_STORE_TYPE = "chromadb"  # Options: "chromadb", "faiss"
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = LOGS_DIR / "chatbot.log"

# Performance
CACHE_ENABLED = True
CACHE_SIZE = 100  # Number of queries to cache

# Entity Extraction
ENTITY_EXTRACTION_METHOD = "hybrid"  # Options: "pattern", "llm", "hybrid"
MIN_ENTITY_CONFIDENCE = 0.6
USE_LLM_EXTRACTION = True  # Use LLM for entity and relationship extraction

# Hybrid Entity Extraction (Pattern + LLM Fallback)
ENABLE_LLM_FALLBACK = True  # Enable LLM fallback when pattern-based confidence is low
LLM_FALLBACK_THRESHOLD = 0.45  # Use LLM if pattern confidence < 45% (lowered from 0.5 to catch more edge cases)
LLM_FALLBACK_FOR_QUESTIONS = True  # Always use LLM for question-type queries with low entity coverage
LLM_FALLBACK_FOR_AMBIGUOUS = True  # Use LLM for ambiguous queries

# LLM-First Strategy (NEW! - For maximum accuracy)
USE_LLM_FIRST_STRATEGY = True  # Always use LLM first, regex for augmentation (80% LLM, 20% Regex)
LLM_FIRST_REGEX_WEIGHT = 0.2  # How much weight to give regex results (0.2 = 20%)
LLM_FIRST_VALIDATION = True  # Use regex to validate LLM results

# Regex Fallback Strategy (NEWEST! - Regex supplements when Neo4j query fails)
USE_REGEX_FALLBACK_ON_EMPTY_RESULTS = True  # If Neo4j returns no results with LLM entities, add regex entities and retry
REGEX_FALLBACK_MAX_RETRIES = 2  # Maximum number of retries with regex augmentation

# ============================================
# FOCUSED ANSWER EXTRACTION (LLM-FIRST STRATEGY)
# ============================================
# Giải quyết vấn đề: User hỏi 1 ý nhưng bot trả lời hết cả FAQ
#
# Chiến lược LLM-First (chi phí không phải vấn đề, ưu tiên chất lượng):
# 1. LLM EXTRACTION (Primary): Luôn dùng LLM trước - hiểu ngữ cảnh tốt nhất
# 2. REGEX FALLBACK: Chỉ khi LLM fail - cho FEE/LIMIT/TIME patterns
# 3. CASE-BASED: Cho HOW_TO/TROUBLESHOOT - extract section liên quan

USE_FOCUSED_EXTRACTION = True       # Enable 3-layer focused extraction
USE_LLM_ANSWER_EXTRACTION = True    # Enable LLM as fallback layer
LLM_EXTRACTION_MIN_ANSWER_LENGTH = 300  # Only extract if FAQ answer > 300 chars (likely multi-case)
LLM_EXTRACTION_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to use extracted answer
FOCUSED_EXTRACTION_MIN_REDUCTION = 0.2  # Minimum 20% reduction to use extracted answer

# Intents that trigger extraction (specific intents get focused answers)
EXTRACTION_ENABLED_INTENTS = [
    "FEE",        # Extract only fee information
    "LIMIT",      # Extract only limit/quota information
    "TIME",       # Extract only time/duration information
    "HOW_TO",     # Extract steps for specific method
    "TROUBLESHOOT",  # Extract solution for specific problem
    "COMPARISON"  # Extract comparison data
]

# Response Generation
RESPONSE_LANGUAGE = "vi"  # Vietnamese
INCLUDE_SOURCES = True  # Include source references in response
MAX_RESPONSE_LENGTH = 500  # Maximum characters in response

# Conversation Memory Configuration (LangChain) - LEGACY
ENABLE_LANGCHAIN_MEMORY = False  # Disabled - now using Mem0
MEMORY_TYPE = "summary_buffer"  # Options: "buffer", "summary", "summary_buffer"
MEMORY_MAX_TOKEN_LIMIT = 2000  # Max tokens to keep in buffer before summarizing
MEMORY_RETURN_MESSAGES = True  # Return as message objects instead of string
MEMORY_AI_PREFIX = "VNPT Assistant"  # AI message prefix
MEMORY_HUMAN_PREFIX = "Khách hàng"  # Human message prefix

# ============================================
# MEM0 CONFIGURATION (NEW - Intelligent Memory Layer)
# ============================================
# Mem0 provides semantic memory search, automatic fact extraction,
# and intelligent conversation context management

ENABLE_MEM0 = True  # Enable Mem0 for conversation memory
MEM0_USE_CLOUD = False  # Use local mode (set True for Mem0 Cloud)
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")  # API key for Mem0 Cloud

# Mem0 Search Configuration
MEM0_SEARCH_LIMIT = 5  # Max memories to retrieve per search
MEM0_MIN_RELEVANCE_SCORE = 0.5  # Minimum score to consider memory relevant
MEM0_FOLLOW_UP_THRESHOLD = 0.7  # Score threshold for follow-up detection

# Follow-up Detection Configuration
ENABLE_FOLLOW_UP_DETECTION = True  # Enable intelligent follow-up detection
FOLLOW_UP_USE_LLM = True  # Use LLM for uncertain cases (more accurate)
FOLLOW_UP_LLM_MODEL = "gpt-4o-mini"  # Model for follow-up detection

# Memory Storage (for local Mem0)
MEM0_VECTOR_STORE = "chroma"  # Options: "chroma", "qdrant"
MEM0_PERSIST_DIR = DATA_DIR / "mem0_chroma"  # Directory for Mem0 data

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
