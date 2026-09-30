from pathlib import Path
from app.repositories.menu_repository import MenuRepository
from app.services.menu_service import MenuService


def service():
    return MenuService(MenuRepository(Path(__file__).parents[1] / "app/data/menu.json"))


def test_exact_item():
    result = service().search("chicken 65")
    assert result.status == "EXACT"
    assert result.candidates[0]["name"] == "Chicken 65"


def test_biryani_is_ambiguous():
    result = service().search("biryani")
    assert result.status == "AMBIGUOUS"
    assert len(result.candidates) >= 2
