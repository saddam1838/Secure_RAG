import os
import threading
import time
import uvicorn
from api.routes import app as fastapi_app

def warm_up_dashboard_cache():
    """Pre-loads expensive dashboard calculations during startup so users wait 0 seconds."""
    print("🔥 Warming up dashboard cache (preloading for instant user experience)...")
    try:
        from services.security_scorer import (
            _get_cached_benchmark,
            _get_cached_rag_quality,
            _get_cached_document_security
        )
        # Force cache population
        _get_cached_benchmark()
        _get_cached_document_security()
        _get_cached_rag_quality()
        print("✅ Dashboard cache warmed up successfully! Users will experience instant load times.")
    except Exception as e:
        print(f"⚠️ Dashboard cache warm-up failed: {e}")

def keep_cache_warm_in_background():
    """Enterprise feature: Silently refresh cache every 12 hours so it NEVER expires."""
    while True:
        time.sleep(43200)  # Sleep for 12 hours
        try:
            from services.security_scorer import (
                _get_cached_benchmark,
                _get_cached_rag_quality,
                _get_cached_document_security
            )
            _get_cached_benchmark()
            _get_cached_document_security()
            _get_cached_rag_quality()
            print("✅ Background: Dashboard cache refreshed and ready!")
        except Exception as e:
            print(f"⚠️ Background cache refresh failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Enterprise Secure RAG (FastAPI + React)...")
    
    # 1. Warm up cache immediately on startup (blocks until done, ensuring it's ready)
    warm_up_dashboard_cache()
    
    # 2. Start background thread to keep it warm forever
    cache_thread = threading.Thread(target=keep_cache_warm_in_background, daemon=True)
    cache_thread.start()
    
    # 3. Launch FastAPI
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
