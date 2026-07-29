import re
import tiktoken
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import nltk

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("stopwords")
    nltk.download("punkt")

_stemmer = PorterStemmer()
_stopwords = set(stopwords.words("english"))


def tokenize(text: str):
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return [_stemmer.stem(t) for t in tokens if t not in _stopwords]


def count_tokens(text: str, model="gpt-3.5-turbo"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def truncate_text(text: str, max_tokens: int, model="gpt-3.5-turbo"):
    enc = tiktoken.encoding_for_model(model)
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])
