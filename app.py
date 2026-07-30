import os
import threading
import time
import uvicorn
from ui.gradio_app import create_gradio_app
from api.routes import app as fastapi_app


def warm_up_dashboard_cache():
    """Pre-load expensive dashboard calculations during startup."""
    print("🔥 Warming up dashboard cache (this may take 30-60 seconds)...")
    try:
        from services.security_scorer import (
            _get_cached_benchmark,
            _get_cached_rag_quality,
            _get_cached_document_security,
        )
        _get_cached_benchmark()
        _get_cached_document_security()
        _get_cached_rag_quality()
        print("✅ Dashboard cache warmed up successfully!")
    except Exception as e:
        print(f"⚠️ Dashboard cache warm-up failed: {e}")


def keep_cache_warm_in_background():
    """Enterprise feature: Silently refresh cache every 12 hours so it NEVER expires."""
    while True:
        time.sleep(43200)  # Sleep for 12 hours
        print("🔥 Background: Silently refreshing dashboard cache to keep it always warm...")
        try:
            from services.security_scorer import (
                _get_cached_benchmark,
                _get_cached_rag_quality,
                _get_cached_document_security,
            )
            _get_cached_benchmark()
            _get_cached_document_security()
            _get_cached_rag_quality()
            print("✅ Background: Dashboard cache refreshed and ready!")
        except Exception as e:
            print(f"⚠️ Background cache refresh failed: {e}")


if __name__ == "__main__":
    print("🚀 Starting Enterprise Secure RAG...")

    # 1. Warm up cache immediately on startup
    warm_up_dashboard_cache()

    # 2. Start background thread to keep it warm forever
    cache_thread = threading.Thread(target=keep_cache_warm_in_background, daemon=True)
    cache_thread.start()

    # 3. Launch Gradio
    gradio_thread = threading.Thread(
        target=create_gradio_app().launch,
        kwargs={
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "share": False,
            "prevent_thread_lock": True
        },
    )
    gradio_thread.daemon = True
    gradio_thread.start()

    # 4. Launch FastAPI
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
