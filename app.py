import os

# AUTOMATIC MEMORY SAFEGUARDS: Prevents OpenMP/MKL thread conflicts that cause BSOD
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import threading
import uvicorn
from ui.gradio_app import create_gradio_app
from api.routes import app as fastapi_app

if __name__ == "__main__":
    print("🚀 Starting Enterprise Secure RAG (Auto-Optimized for 8GB RAM)...")

    # Launch Gradio in a separate thread
    gradio_thread = threading.Thread(
        target=create_gradio_app().launch,
        kwargs={"server_name": "127.0.0.1", "server_port": 7860, "share": False},
    )
    gradio_thread.daemon = True
    gradio_thread.start()

    # Launch FastAPI
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)
