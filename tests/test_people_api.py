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


def test_duplicate_location_roles_rejected(client: TestClient, session: Session) -> None:
    family_response = client.post("/families", json={"name": "Dupes", "description": "Family"})
    assert family_response.status_code == 201
    family_id = family_response.json()["id"]

    location_one = client.post(
        "/locations",
        json={"name": "Alpha", "city": "Town", "country": "Wonderland"},
    )
    assert location_one.status_code == 201
    location_one_id = location_one.json()["id"]

    location_two = client.post(
        "/locations",
        json={"name": "Beta", "city": "City", "country": "Wonderland"},
    )
    assert location_two.status_code == 201
    location_two_id = location_two.json()["id"]

    person_create = {
        "first_name": "Bob",
        "last_name": "Duperson",
        "family_id": family_id,
        "locations": [{"role": "birthplace", "location_id": location_one_id}],
    }
    create_response = client.post("/people", json=person_create)
    assert create_response.status_code == 201
    person_id = create_response.json()["id"]

    duplicate_payload = {
        "locations": [
            {"role": "residence", "location_id": location_one_id},
            {"role": "residence", "location_id": location_two_id},
        ]
    }
    update_response = client.put(f"/people/{person_id}", json=duplicate_payload)
    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Duplicate location role 'residence' in request"


def test_person_with_death_before_birth_rejected(client: TestClient, session: Session) -> None:
    payload = {
        "first_name": "Temporal",
        "last_name": "Anomaly",
        "birth_date": "2000-01-01",
        "death_date": "1990-01-01",
    }

    response = client.post("/people", json=payload)

    assert response.status_code == 422
    assert any(
        error.get("msg") == "Value error, death_date cannot be earlier than birth_date"
        for error in response.json().get("detail", [])
    )


def test_create_person_with_nested_family_and_locations(
    client: TestClient, session: Session
) -> None:
    existing_location = client.post(
        "/locations",
        json={
            "name": "City Square",
            "city": "Metro City",
            "state": "Central",
            "country": "Freedonia",
        },
    )
    assert existing_location.status_code == 201
    existing_location_id = existing_location.json()["id"]

    payload = {
        "first_name": "Charlie",
        "last_name": "Nested",
        "biography": "Created in one shot",
        "family": {"name": "Nested Family", "description": "Created inline"},
        "locations": [
            {
                "role": "birthplace",
                "new_location": {
                    "name": "Gotham General",
                    "city": "Gotham",
                    "state": "NY",
                    "country": "USA",
                },
            },
            {"role": "residence", "location_id": existing_location_id},
        ],
    }

    response = client.post("/people", json=payload)
    assert response.status_code == 201
    person = response.json()

    assert person["family_id"] is not None
    family_response = client.get(f"/families/{person['family_id']}")
    assert family_response.status_code == 200
    assert family_response.json()["name"] == "Nested Family"

    locations_by_role = {loc["role"]: loc["location"] for loc in person["locations"]}
    assert locations_by_role["birthplace"]["name"] == "Gotham General"
    assert locations_by_role["residence"]["id"] == existing_location_id

    new_location_id = locations_by_role["birthplace"]["id"]
    location_lookup = client.get(f"/locations/{new_location_id}")
    assert location_lookup.status_code == 200
    assert location_lookup.json()["name"] == "Gotham General"
