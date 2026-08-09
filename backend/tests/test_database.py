from pathlib import Path

import database


def test_farmer_memory_persists_and_merges(tmp_path: Path, monkeypatch) -> None:
    """A second database access sees the profile and later updates merge into it."""
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "krishimitra.db")

    database.save_farmer_memory(
        "farmer_123",
        "Ramesh",
        "hi",
        {
            "crops_grown": "cotton",
            "land_size": "5 acres",
            "district": "Bhopal",
            "irrigation_type": "borewell",
        },
    )
    profile = database.lookup_farmer("farmer_123")

    assert profile is not None
    assert profile["name"] == "Ramesh"
    assert profile["facts"]["crops_grown"] == "cotton"

    database.save_farmer_memory(
        "farmer_123", None, None, {"crops_grown": "cotton, soybean"}
    )
    updated = database.lookup_farmer("farmer_123")

    assert updated is not None
    assert updated["facts"]["crops_grown"] == "cotton, soybean"
    assert updated["facts"]["land_size"] == "5 acres"
