from dataclasses import dataclass
from app.repositories.menu_repository import MenuRepository
from app.utils.text_normalizer import normalize_text, tokens


@dataclass
class Resolution:
    status: str  # EXACT | AMBIGUOUS | NOT_FOUND
    query: str
    candidates: list[dict]
    score: int = 0


class MenuService:
    def __init__(self, repository: MenuRepository):
        self.repository = repository

    def search(self, query: str) -> Resolution:
        q = normalize_text(query)
        q_tokens = set(tokens(q))
        scored: list[tuple[int, dict]] = []

        for item in self.repository.all_items():
            if not item.get("available", True):
                continue
            names = [normalize_text(item.get("name", ""))]
            keywords = [normalize_text(k) for k in item.get("keywords", [])]
            best = 0
            for candidate in names + keywords:
                if candidate == q:
                    best = max(best, 100)
                elif q and (candidate == q or q in candidate or candidate in q):
                    best = max(best, 80)
                else:
                    overlap = len(q_tokens.intersection(set(tokens(candidate))))
                    if overlap:
                        best = max(best, 20 + overlap * 10)
            if best:
                scored.append((best, item))

        scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        if not scored:
            return Resolution("NOT_FOUND", query, [])

        top_score = scored[0][0]
        # Exact semantic/name match wins over weaker keyword matches.
        top = [item for score, item in scored if score == top_score]
        if top_score >= 100:
            if len(top) == 1:
                return Resolution("EXACT", query, top, top_score)
            return Resolution("AMBIGUOUS", query, top[:10], top_score)

        # If there is one clear candidate substantially ahead, resolve it.
        if len(scored) == 1 or (len(scored) > 1 and scored[0][0] >= scored[1][0] + 20):
            return Resolution("EXACT", query, [scored[0][1]], scored[0][0])

        # Return a compact candidate list for UI clarification.
        candidates = [item for _, item in scored[:10]]
        return Resolution("AMBIGUOUS", query, candidates, top_score)
