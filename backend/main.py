from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.core.embeddings import get_embedding_model
from backend.core.retriever import _load_permanent_index
from backend.db.session import init_db
from backend.utils.logger import get_logger

from backend.api.policy_routes import router as policy_router
from backend.api.chat_routes import router as chat_router
from backend.api.feedback_routes import router as feedback_router
from backend.api.pdf_chat_routes import router as pdf_chat_router
from backend.api.export_routes import router as export_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts, before any request is accepted.
    Warms up the embedding model + FAISS index (avoids cold-start
    delay on the first user question) and ensures database tables
    exist before any route tries to use them.
    """
    logger.info("Starting up — warming up embedding model and FAISS index...")
    get_embedding_model()
    _load_permanent_index()
    logger.info("Warm-up complete.")

    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")

    logger.info("Server ready to accept requests.")

    yield

    logger.info("Shutting down.")


app = FastAPI(
    title="Policy Intelligence Assistant",
    description="RAG-based policy assistant for AstraNova Technologies Pvt. Ltd.",
    version="2.0.0",
    lifespan=lifespan
)

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policy_router, prefix="/policy", tags=["Policy Assistant"])
app.include_router(chat_router, prefix="/chat", tags=["Chat History"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(pdf_chat_router, prefix="/pdf_chat", tags=["PDF Chat"])
app.include_router(export_router, prefix="/export", tags=["Export"])


# @app.get("/")
# def health_check():
#     """Simple endpoint to confirm the server is alive."""
#     return {"status": "ok", "message": "Policy Intelligence Assistant API is running."}

from fastapi.responses import FileResponse

@app.get("/")
def dashboard():
    return FileResponse("frontend/dashboard.html")

@app.get("/policy")
def policy_workspace():
    return FileResponse("frontend/policy_assistant_workspace.html")

@app.get("/pdf")
def pdf_workspace():
    return FileResponse("frontend/pdf_chat_workspace.html")