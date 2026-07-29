from services.rag_service import RAGService


def test_chunking():
    rag = RAGService()
    chunks = rag._chunk_document("This is a test. " * 20)
    assert len(chunks) > 0
    assert all(len(c) <= 500 for c in chunks)
