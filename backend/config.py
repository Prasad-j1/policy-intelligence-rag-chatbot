import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env into the environment
load_dotenv()

# ----------------------------------------------------------------
# BASE PATHS
# ----------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # project root

KNOWLEDGE_BASE_PATH = str(BASE_DIR / "data" / "knowledge_base")
UPLOADS_PATH = str(BASE_DIR / "data" / "uploads")
VECTOR_STORE_PATH = str(BASE_DIR / "vector_store")          # contains permanent/ and temp/
PROMPTS_PATH = str(BASE_DIR / "prompts")
LOGS_PATH = str(BASE_DIR / "logs")

# ----------------------------------------------------------------
# LLM CONFIGURATION
# ----------------------------------------------------------------
# Which LLM each workspace uses. Configurable, never hardcoded in business logic.
# POLICY_ASSISTANT_LLM = os.getenv("POLICY_ASSISTANT_LLM", "gemini")   # "gemini" or "ollama"
# PDF_CHAT_LLM = os.getenv("PDF_CHAT_LLM", "ollama")                   # "gemini" or "ollama"
# NVIDIA_LLM = os.getenv("NVIDIA_LLM", "nvidia")                       # "nvidia"

POLICY_ASSISTANT_LLM = os.getenv("POLICY_ASSISTANT_LLM", "nvidia")
PDF_CHAT_LLM = os.getenv("PDF_CHAT_LLM", "nvidia")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "phi")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ----------------------------------------------------------------
# EMBEDDING MODEL
# ----------------------------------------------------------------
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")

# ----------------------------------------------------------------
# RETRIEVAL / FAISS
# ----------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "4"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.70"))

# ----------------------------------------------------------------
# CHUNKING
# ----------------------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "75"))

# ----------------------------------------------------------------
# PDF UPLOAD (Chat with PDF workspace)
# ----------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))

# ----------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")

# ----------------------------------------------------------------
# DEVELOPER MODE
# ----------------------------------------------------------------
DEVELOPER_MODE_DEFAULT = os.getenv("DEVELOPER_MODE_DEFAULT", "false").lower() == "true"

# ----------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")



# ----------------------------------------------------------------
# OPTIONAL FEATURE TOGGLES
# ----------------------------------------------------------------
ENABLE_FOLLOWUP_QUESTIONS = os.getenv("ENABLE_FOLLOWUP_QUESTIONS", "false").lower() == "true"

# ----------------------------------------------------------------
# Suggested questions path (used by backend/suggested_questions.py)
# ----------------------------------------------------------------

SUGGESTED_QUESTIONS_PATH = str(BASE_DIR / "backend" / "data" / "suggested_questions.json")

# ----------------------------------------------------------------
# EVALUATION TARGETS (used by evaluation/run_eval.py, not enforced at runtime)
# ----------------------------------------------------------------
EVAL_RETRIEVAL_ACCURACY_TARGET = 0.90
EVAL_GROUNDED_ANSWER_RATE_TARGET = 0.95
EVAL_HALLUCINATION_RATE_MAX = 0.05
EVAL_RESPONSE_TIME_MAX_SECONDS = 3.0
EVAL_RETRIEVER_TIME_MAX_MS = 500


CROSS_ENCODER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# PDF_CHUNK_SIZE = int(os.getenv("PDF_CHUNK_SIZE", "180"))
# PDF_CHUNK_OVERLAP = int(os.getenv("PDF_CHUNK_OVERLAP", "30"))


# nvidia llm

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL_NAME = os.getenv(
    "NVIDIA_MODEL_NAME",
    "nvidia/nemotron-3.5-lightning-30b-a3b"
)