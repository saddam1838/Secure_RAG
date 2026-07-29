from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .schemas import QueryRequest, QueryResponse, TokenResponse
from .dependencies import get_current_user, create_access_token, verify_password
from services.rag_service import RAGService
from services.benchmark_service import run_benchmark
from services.audit_service import AuditService
from services.security_service import SecurityGuard
from config import settings
import asyncio
from prometheus_client import generate_latest, Counter, Histogram

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

QUERY_COUNT = Counter("query_total", "Total number of queries")
QUERY_LATENCY = Histogram("query_latency_seconds", "Query latency")

rag = RAGService()
audit = AuditService()
security = SecurityGuard()


@app.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and verify_password(
        form_data.password, settings.BCRYPT_HASH
    ):
        token = create_access_token({"sub": form_data.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/query")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD} seconds")
async def query(
    request: Request,
    req: QueryRequest,
    background_tasks: BackgroundTasks,
    user: str = Depends(get_current_user),
):
    QUERY_COUNT.inc()
    with QUERY_LATENCY.time():
        issues = security.scan_query(req.query)
        if issues:
            raise HTTPException(
                status_code=400, detail=f"Query blocked: {issues[0]['name']}"
            )

        pi_score = security.detect_prompt_injection(req.query)

        eval_result = security.should_block_query_advanced(req.query, pi_score)

        if eval_result["blocked"]:
            raise HTTPException(
                status_code=400,
                detail=f"Query blocked: {eval_result['reason']} (Method: {eval_result['method']})",
            )

        safe_query = security.sanitize_input(req.query)
        chunks = rag.retrieve(safe_query, filters=req.filters, k=settings.TOP_K_DENSE)

        if not chunks:
            return QueryResponse(response="No relevant information found.", sources=[])

        chunks = rag.rerank(safe_query, chunks)
        response = await asyncio.to_thread(rag.generate, safe_query, chunks)
        sources = [chunk["source"] for chunk in chunks]

        background_tasks.add_task(
            audit.log,
            user,
            "query",
            {
                "query": req.query,
                "response": response[:200],
                "security_method": eval_result["method"],
            },
        )

        return QueryResponse(response=response, sources=sources)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.get("/benchmark")
def benchmark():
    return run_benchmark()


@app.get("/health")
def health():
    return {"status": "ok"}
