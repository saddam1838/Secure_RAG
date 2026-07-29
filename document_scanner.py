import os
from security import SecurityGuard

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".html", ".md"}


class UnsupportedFormatError(Exception):
    pass


class MissingLibraryError(Exception):
    pass


def read_file_content(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        try:
            import pypdf
        except ImportError:
            raise MissingLibraryError(
                "PDF support requires pypdf. Install: pip install pypdf"
            )
        reader = pypdf.PdfReader(filepath)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    elif ext == ".docx":
        try:
            import docx
        except ImportError:
            raise MissingLibraryError(
                "DOCX support requires python-docx. Install: pip install python-docx"
            )
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".html":
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise MissingLibraryError(
                "HTML support requires beautifulsoup4. Install: pip install beautifulsoup4"
            )
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
            return soup.get_text()
    elif ext == ".md":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        raise UnsupportedFormatError(f"Unsupported file type: {ext}")


def scan_document(file_content: str, filename: str) -> dict:
    # Simple scan – in production, call SecurityGuard
    issues = []
    if "ignore previous" in file_content.lower():
        issues.append({"name": "Embedded System Prompt"})
    return {
        "filename": filename,
        "size_mb": len(file_content.encode("utf-8")) / (1024 * 1024),
        "issues": issues,
        "is_safe": len(issues) == 0,
    }
