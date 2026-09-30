import re
import unicodedata


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^\w\s.-]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def tokens(value: str) -> list[str]:
    return normalize_text(value).replace("-", " ").split()
