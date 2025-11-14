from __future__ import annotations

from fastapi.testclient import TestClient


def test_family_endpoints_include_members(client: TestClient) -> None:
    family_response = client.post(
        "/families", json={"name": "Anderson", "description": "Test family"}
    )
    assert family_response.status_code == 201
    family_id = family_response.json()["id"]

    person_payload = {
        "first_name": "Alex",
        "last_name": "Anderson",
        "family_id": family_id,
    }
    person_response = client.post("/people", json=person_payload)
    assert person_response.status_code == 201
    person_id = person_response.json()["id"]

    get_response = client.get(f"/families/{family_id}")
    assert get_response.status_code == 200
    family_detail = get_response.json()
    assert family_detail["id"] == family_id
    assert family_detail["members"], "members list should not be empty"

    member = family_detail["members"][0]
    assert member["id"] == person_id
    assert member["family_id"] == family_id
    assert member["locations"] == []

    list_response = client.get("/families")
    assert list_response.status_code == 200
    listed_families = list_response.json()
    assert any(item["id"] == family_id for item in listed_families)
    for item in listed_families:
        assert "members" in item
