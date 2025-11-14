from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_person_crud_flow(client: TestClient, session: Session) -> None:
    family_response = client.post("/families", json={"name": "Smith", "description": "Test family"})
    assert family_response.status_code == 201
    family_id = family_response.json()["id"]

    birthplace = client.post(
        "/locations",
        json={"name": "Townsville", "city": "Townsville", "country": "Wonderland"},
    )
    assert birthplace.status_code == 201
    birthplace_id = birthplace.json()["id"]

    residence = client.post(
        "/locations",
        json={"name": "City Center", "city": "Metropolis", "country": "Wonderland"},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]

    create_payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "biography": "Explorer",
        "family_id": family_id,
        "locations": [{"role": "birthplace", "location_id": birthplace_id}],
    }
    create_response = client.post("/people", json=create_payload)
    assert create_response.status_code == 201
    person_data = create_response.json()
    assert person_data["first_name"] == "Alice"
    assert person_data["locations"][0]["location"]["id"] == birthplace_id
    person_id = person_data["id"]

    list_response = client.get("/people")
    assert list_response.status_code == 200
    assert any(item["id"] == person_id for item in list_response.json())

    update_payload = {
        "last_name": "Johnson",
        "biography": None,
        "locations": [
            {"role": "birthplace", "location_id": birthplace_id},
            {"role": "residence", "location_id": residence_id},
        ],
    }
    update_response = client.put(f"/people/{person_id}", json=update_payload)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["last_name"] == "Johnson"
    assert len(updated["locations"]) == 2

    invalid_update = client.put(
        f"/people/{person_id}",
        json={"locations": [{"role": "burial", "location_id": 9999}]},
    )
    assert invalid_update.status_code == 404

    delete_response = client.delete(f"/people/{person_id}")
    assert delete_response.status_code == 204

    list_after_delete = client.get("/people")
    assert all(item["id"] != person_id for item in list_after_delete.json())
