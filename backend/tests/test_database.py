from database import FarmerRepository


def test_farmer_memory_persists_and_merges_updates(tmp_path) -> None:
    database_path = tmp_path / "krishimitra.db"
    repository = FarmerRepository(database_path)
    repository.save_farmer_memory(
        "farmer_123",
        "Ramesh",
        "hi",
        {"crops_grown": "cotton", "land_size": "5 acres"},
    )

    restarted_repository = FarmerRepository(database_path)
    restarted_repository.save_farmer_memory(
        "farmer_123", None, None, {"crops_grown": "cotton, soybean"}
    )
    farmer = restarted_repository.lookup_farmer("farmer_123")

    assert farmer is not None
    assert farmer["name"] == "Ramesh"
    assert farmer["facts"] == {
        "crops_grown": "cotton, soybean",
        "land_size": "5 acres",
    }
