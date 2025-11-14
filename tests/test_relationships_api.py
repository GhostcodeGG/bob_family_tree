from __future__ import annotations

from fastapi.testclient import TestClient


def _create_person(client: TestClient, first_name: str, last_name: str) -> int:
    response = client.post(
        "/people",
        json={"first_name": first_name, "last_name": last_name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_relationship_bidirectional_flow(client: TestClient) -> None:
    parent_id = _create_person(client, "Parent", "Example")
    child_id = _create_person(client, "Child", "Example")

    create_response = client.post(
        "/relationships",
        json={"from_person_id": parent_id, "to_person_id": child_id, "type": "parent"},
    )
    assert create_response.status_code == 201
    relationship_id = create_response.json()["id"]

    list_response = client.get("/relationships")
    assert list_response.status_code == 200
    relationships = {(item["from_person_id"], item["to_person_id"]): item["type"] for item in list_response.json()}
    assert relationships[(parent_id, child_id)] == "parent"
    assert relationships[(child_id, parent_id)] == "child"

    update_response = client.put(
        f"/relationships/{relationship_id}", json={"type": "spouse"}
    )
    assert update_response.status_code == 200

    list_after_update = client.get("/relationships")
    assert list_after_update.status_code == 200
    updated_relationships = {
        (item["from_person_id"], item["to_person_id"]): item["type"]
        for item in list_after_update.json()
    }
    assert updated_relationships[(parent_id, child_id)] == "spouse"
    assert updated_relationships[(child_id, parent_id)] == "spouse"

    invalid_response = client.post(
        "/relationships",
        json={"from_person_id": parent_id, "to_person_id": parent_id, "type": "parent"},
    )
    assert invalid_response.status_code == 400

    delete_response = client.delete(f"/relationships/{relationship_id}")
    assert delete_response.status_code == 204

    list_after_delete = client.get("/relationships")
    assert list_after_delete.json() == []
