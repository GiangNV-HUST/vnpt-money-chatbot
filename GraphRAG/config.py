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
LLM_PROVIDER = "openai"
# Supported models: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
LLM_MODEL = "gpt-4o-mini"  # Recommended: gpt-4o-mini (fast, cheap, good quality)
LLM_TEMPERATURE = 0.1  # Low temperature for consistent extraction
LLM_MAX_TOKENS = 4096  # Increased to allow for longer, detailed responses

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
HYBRID_WEIGHT_ENTITY_GRAPH = 0.7  # Entity-based graph search (70% - increased to prioritize exact entity matches)
HYBRID_WEIGHT_SEMANTIC = 0.3      # Semantic similarity search (30% - reduced to minimize contamination from previous queries)
HYBRID_WEIGHT_KEYWORD = 0.0       # Keyword search (disabled in hybrid mode)

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

# Response Generation
RESPONSE_LANGUAGE = "vi"  # Vietnamese
INCLUDE_SOURCES = True  # Include source references in response
MAX_RESPONSE_LENGTH = 500  # Maximum characters in response

# Conversation Memory Configuration (LangChain)
ENABLE_LANGCHAIN_MEMORY = True  # Use LangChain ConversationSummaryBufferMemory
MEMORY_TYPE = "summary_buffer"  # Options: "buffer", "summary", "summary_buffer"
MEMORY_MAX_TOKEN_LIMIT = 2000  # Max tokens to keep in buffer before summarizing
MEMORY_RETURN_MESSAGES = True  # Return as message objects instead of string
MEMORY_AI_PREFIX = "VNPT Assistant"  # AI message prefix
MEMORY_HUMAN_PREFIX = "Khách hàng"  # Human message prefix

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
