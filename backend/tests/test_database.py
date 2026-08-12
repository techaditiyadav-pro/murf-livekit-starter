import importlib
from pathlib import Path

import database


def test_farmer_memory_survives_module_reload_and_merges(
    tmp_path: Path, monkeypatch
) -> None:
    """A profile remains available after a simulated agent restart and later updates merge."""
    database_path = tmp_path / "krishimitra.db"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)

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
    # Reloading represents a fresh agent process loading the same SQLite file.
    restarted_database = importlib.reload(database)
    monkeypatch.setattr(restarted_database, "DATABASE_PATH", database_path)
    profile = restarted_database.lookup_farmer("farmer_123")

    assert profile is not None
    assert profile["name"] == "Ramesh"
    assert profile["facts"]["crops_grown"] == "cotton"

    restarted_database.save_farmer_memory(
        "farmer_123", None, None, {"crops_grown": "cotton, soybean"}
    )
    updated = restarted_database.lookup_farmer("farmer_123")

    assert updated is not None
    assert updated["facts"]["crops_grown"] == "cotton, soybean"
    assert updated["facts"]["land_size"] == "5 acres"
