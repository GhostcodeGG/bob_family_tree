from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def test_submit_person_form_does_not_create_aux_records_on_error(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/ui/people",
        data={
            "first_name": "Charlie",
            "last_name": " ",  # trigger required last name validation
            "new_family_name": "Temp Family",
            "new_family_description": "Should not persist",
            "birthplace_location_name": "Temporary Birthplace",
            "birthplace_location_city": "Nowhere",
            "birthplace_location_country": "Noland",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "First name is required." not in response.text
    assert "Last name is required." in response.text

    families = session.scalars(select(models.Family)).all()
    locations = session.scalars(select(models.Location)).all()

    assert families == []
    assert locations == []
