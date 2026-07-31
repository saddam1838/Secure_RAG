from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .schemas import QueryRequest, QueryResponse, TokenResponse, LoginRequest, RegisterRequest, ChatRequest, ChatResponse, ScanResponse
from .dependencies import get_current_user, create_access_token, verify_password
from services.rag_service import RAGService
from services.benchmark_service import run_benchmark
from services.audit_service import AuditService
from services.security_service import SecurityGuard
from services.security_scorer import SecurityScorer
from services.llm_evaluator import LLMJudgeEvaluator
from services.config_manager import ConfigManager
from document_scanner import read_file_content, scan_document as doc_scan
from guardrails import Guardrail
from config import settings
from database import register_user, authenticate_user
import asyncio, os, tempfile, shutil, json, re
from prometheus_client import generate_latest, Counter, Histogram

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

QUERY_COUNT = Counter("query_total", "Total number of queries")
QUERY_LATENCY = Histogram("query_latency_seconds", "Query latency")

rag = RAGService()
audit = AuditService()
security = SecurityGuard()
guardrail = Guardrail()
config_manager = ConfigManager()

# ============ AUTH ============
@app.post("/api/auth/login")
async def react_login(req: LoginRequest):
    success, msg, role = authenticate_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=401, detail=msg)
    token = create_access_token({"sub": req.username, "role": role})
    return {"access_token": token, "token_type": "bearer", "username": req.username, "role": role}

@app.post("/api/auth/register")
async def react_register(req: RegisterRequest):
    success, msg = register_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/token", response_model=TokenResponse)
async def legacy_login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and verify_password(form_data.password, settings.BCRYPT_HASH):
        token = create_access_token({"sub": form_data.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ============ CHAT ============
@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD} seconds")
async def chat(request: Request, req: ChatRequest, user: str = Depends(get_current_user)):
    QUERY_COUNT.inc()
    with QUERY_LATENCY.time():
        message = security.sanitize_input(req.message)
        
        query_issues = security.scan_query(message)
        if query_issues:
            audit.log(user, "query_blocked", {"query": message[:100], "method": "regex", "issues": [i["name"] for i in query_issues]})
            return ChatResponse(reply="🛑 Query blocked. Matched security policy.", blocked=True, reason=query_issues[0]["name"])
        
        ml_score = security.detect_prompt_injection(message)
        eval_result = security.should_block_query_advanced(message, ml_score)
        if eval_result["blocked"]:
            audit.log(user, "query_blocked", {"query": message[:100], "method": eval_result["method"], "reason": eval_result["reason"], "ml_score": round(ml_score, 3)})
            return ChatResponse(reply=f"🛑 Query blocked. {eval_result['reason']}", blocked=True, reason=eval_result["reason"])
        
        context = rag.retrieve(message, k=settings.TOP_K_DENSE, username=user)
        if not context:
            audit.log(user, "no_context_found", {"query": message[:100]})
            return ChatResponse(reply="No relevant documents found in your knowledge base. Please upload documents to get started.", blocked=False)
        
        response = await asyncio.to_thread(rag.generate, message, context)
        guarded = guardrail.sanitize_output(response)
        
        audit.log(user, "query_answered", {"query": message[:100], "chunks_used": len(context), "sources": [c.get("source", "unknown") for c in context[:3]]})
        return ChatResponse(reply=guarded["cleaned"], blocked=False)

# ============ DOCUMENTS ============
@app.post("/api/documents/upload-and-index")
async def upload_and_index(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        content = read_file_content(tmp_path)
        if not content:
            raise HTTPException(400, "Could not extract text")
        report = doc_scan(content, file.filename)
        if not report["is_safe"]:
            raise HTTPException(400, f"Document blocked: {[i['name'] for i in report['issues']]}")
        
        size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        metadata = {"source": file.filename, "size_mb": size_mb}
        rag.add_document(content, metadata, uploaded_by=user)
        audit.log(user, "document_indexed", {"filename": file.filename})
        return {"success": True, "message": f"Successfully indexed: {file.filename}"}
    finally:
        try: os.unlink(tmp_path)
        except: pass

@app.get("/api/documents")
async def list_documents(user: str = Depends(get_current_user)):
    from services.cloud_storage import cloud_storage
    if cloud_storage.is_cloud_enabled:
        result = cloud_storage.supabase.table("documents").select("id, filename, size_mb, created_at, is_safe").eq("uploaded_by", user).order("created_at", desc=True).execute()
        return result.data
    
    seen = set()
    docs = []
    for m in rag.metadata:
        if m.get("uploaded_by") == user:
            fname = m.get("source", "unknown")
            if fname not in seen:
                seen.add(fname)
                docs.append({"id": fname, "filename": fname, "size_mb": 0, "created_at": "Local", "is_safe": True})
    return docs

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, user: str = Depends(get_current_user)):
    from services.cloud_storage import cloud_storage
    if cloud_storage.is_cloud_enabled:
        success, msg = cloud_storage.delete_document(doc_id, user)
        if success:
            res = cloud_storage.supabase.table("documents").select("filename").eq("id", doc_id).execute()
            if res.data: 
                rag.remove_document_from_memory(os.path.basename(res.data[0]["filename"]))
        return {"success": success, "message": msg}
    
    rag.remove_document_from_memory(doc_id)
    return {"success": True, "message": f"Deleted {doc_id}"}

# ============ DASHBOARD ============
@app.get("/api/dashboard")
async def dashboard(user: str = Depends(get_current_user)):
    return SecurityScorer.calculate_posture_score(user)

# ============ ATTACK SIMULATOR ============
@app.get("/api/attacks/query/types")
async def query_attack_types():
    with open("attacks.json", "r", encoding="utf-8") as f:
        attacks = json.load(f)
    return list(attacks.keys()) + ["Custom"]

@app.post("/api/attacks/query/run")
async def run_query_attack(payload: dict, user: str = Depends(get_current_user)):
    attack_type = payload.get("type", "Prompt Injection")
    custom = payload.get("custom", "")
    
    if attack_type == "Custom" and custom:
        queries = [custom]
    else:
        with open("attacks.json", "r", encoding="utf-8") as f:
            attacks = json.load(f)
        queries = attacks.get(attack_type, [])
    
    results = []
    for q in queries:
        issues = security.scan_query(q)
        ml_score = security.detect_prompt_injection(q)
        blocked = bool(issues) or ml_score > security.get_ml_threshold()
        
        if issues:
            reason = issues[0]["name"]
        elif blocked:
            reason = "ML score exceeded threshold"
        else:
            reason = "Passed all checks"
            
        results.append({"query": q, "blocked": blocked, "reason": reason, "ml_score": round(ml_score, 3)})
    
    return {"attack_type": attack_type, "results": results}

@app.get("/api/attacks/document/types")
async def doc_attack_types():
    with open("document_attacks.json", "r", encoding="utf-8") as f:
        attacks = json.load(f)
    return list(attacks.keys()) + ["Custom"]

@app.post("/api/attacks/document/run")
async def run_doc_attack(payload: dict, user: str = Depends(get_current_user)):
    attack_type = payload.get("type", "Embedded System Prompt")
    custom = payload.get("custom", "")
    
    if attack_type == "Custom" and custom:
        payloads = [(custom, "custom_test.txt")]
    elif attack_type == "Oversized Document":
        payloads = [("A" * (1 * 1024 * 1024), "oversized_test.txt")]
    else:
        with open("document_attacks.json", "r", encoding="utf-8") as f:
            attacks = json.load(f)
        payloads = [(content, f"{attack_type.lower().replace(' ', '_')}_test.txt") for content in attacks.get(attack_type, [])]
    
    results, total, blocked = [], 0, 0
    for content, filename in payloads:
        total += 1
        doc_issues = security.scan_document(content, filename)
        chunk_issues = []
        if not doc_issues and len(content) > 50:
            chunks = [content[i : i + 500] for i in range(0, min(len(content), 1500), 500)]
            try: chunk_issues = security.scan_chunks(chunks)
            except Exception: pass
        
        all_issues = doc_issues + chunk_issues
        if len(all_issues) > 0: blocked += 1
            
        severity_order = {"high": 0, "medium": 1, "low": 2}
        top_issue = min(all_issues, key=lambda x: severity_order.get(x.get("severity", "low"), 3)) if all_issues else {}
        
        results.append({
            "filename": filename, "blocked": len(all_issues) > 0,
            "layer": "Regex Scanner" if top_issue in doc_issues else "ML Chunk Scanner" if all_issues else "None",
            "severity": top_issue.get("severity", "none").upper() if top_issue else "NONE",
            "details": top_issue.get("name", "No threats detected")[:60] if top_issue else "No threats detected"
        })
        
    return {"attack_type": attack_type, "results": results, "detection_rate": round((blocked / total * 100) if total > 0 else 0, 1), "total": total, "blocked": blocked}

# ============ SECURITY CONFIG ============
@app.get("/api/security/rules")
async def get_rules(): return config_manager.load_security_rules()

@app.get("/api/security/thresholds")
async def get_thresholds(): return config_manager.get_current_thresholds()

@app.put("/api/security/thresholds")
async def update_threshold(payload: dict, user: str = Depends(get_current_user)):
    success, msg = config_manager.update_threshold(payload.get("key"), payload.get("value"))
    return {"success": success, "message": msg}

@app.post("/api/security/test-pattern")
async def test_pattern(payload: dict):
    pattern, text = payload.get("pattern", ""), payload.get("text", "")
    if not pattern or not text: return {"valid": False, "error": "Please provide both pattern and text"}
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        matches = compiled.findall(text)
        return {"valid": True, "matches": len(matches), "matched_text": [str(m)[:100] for m in matches[:5]], "message": f"{len(matches)} match(es) found."}
    except re.error as e: return {"valid": False, "error": str(e)}

# ============ COMPLIANCE ============
@app.get("/api/compliance")
async def compliance(): return config_manager.get_compliance_details()

# ============ EVALUATE ============
@app.post("/api/evaluate")
async def evaluate(user: str = Depends(get_current_user)):
    user_docs = [m for m in rag.metadata if m.get("uploaded_by") == user]
    if not rag.corpus or len(rag.metadata) == 0:
        return {"has_documents": False, "error": "No documents found. Please upload documents first."}
    if not user_docs:
        return {"has_documents": False, "error": f"No documents for '{user}'. Please upload documents first."}
    
    evaluator = LLMJudgeEvaluator()
    return evaluator.run_dynamic_evaluation(rag, num_queries=3, k=3)

# ============ METRICS & HEALTH ============
@app.get("/metrics")
def metrics(): return Response(generate_latest(), media_type="text/plain")

@app.get("/benchmark")
def benchmark(): return run_benchmark()

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/documents/scan")
async def scan_document_only(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    """Step 1: Scan document for threats WITHOUT indexing."""
    import tempfile, os
    from document_scanner import read_file_content, scan_document as doc_scan
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        content = read_file_content(tmp_path)
        if not content:
            return {"is_safe": False, "filename": file.filename, "size_mb": 0, "issues": [], "message": "Could not extract text"}
        
        report = doc_scan(content, file.filename)
        size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        
        audit.log(user, "document_scan", {
            "filename": file.filename,
            "size_mb": round(size_mb, 2),
            "is_safe": report["is_safe"],
            "issues_count": len(report["issues"])
        })
        
        return {
            "is_safe": report["is_safe"],
            "filename": file.filename,
            "size_mb": round(size_mb, 2),
            "issues": report["issues"],
            "message": "✅ SECURE - No threats detected" if report["is_safe"] else "🛑 BLOCKED - Threats detected"
        }
    finally:
        try: os.unlink(tmp_path)
        except: pass
