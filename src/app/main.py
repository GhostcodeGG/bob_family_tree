"""FastAPI application exposing family tree functionality."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas, services
from .config import get_settings
from .database import engine, get_session

models.Base.metadata.create_all(bind=engine)

settings = get_settings()
app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or response.reason_phrase

    detail = data.get("detail")
    if detail is None:
        return response.text
    if isinstance(detail, list):
        messages = []
        for entry in detail:
            if isinstance(entry, dict):
                messages.append(str(entry.get("msg") or entry))
            else:
                messages.append(str(entry))
        return "; ".join(messages)
    return str(detail)


def _location_role_metadata() -> List[Dict[str, str]]:
    return [
        {
            "value": role.value,
            "label": role.value.replace("_", " ").title(),
        }
        for role in models.LocationRole
    ]


async def _fetch_reference_data() -> tuple[List[dict], List[dict]]:
    async with httpx.AsyncClient(app=app, base_url="http://app") as client:
        families_response, locations_response = await asyncio.gather(
            client.get("/families"), client.get("/locations")
        )

    families = families_response.json() if families_response.status_code == status.HTTP_200_OK else []
    locations = (
        locations_response.json()
        if locations_response.status_code == status.HTTP_200_OK
        else []
    )
    return families, locations


async def _render_person_form(
    request: Request,
    *,
    message: str | None = None,
    message_type: str = "success",
    form_values: Dict[str, str] | None = None,
    created_person: dict | None = None,
) -> HTMLResponse:
    families, locations = await _fetch_reference_data()
    context = {
        "request": request,
        "families": families,
        "locations": locations,
        "location_roles": _location_role_metadata(),
        "message": message,
        "message_type": message_type,
        "form_values": form_values or {},
        "created_person": created_person,
    }
    return templates.TemplateResponse("person_form.html", context)


@app.get("/", response_class=HTMLResponse)
async def person_form(request: Request) -> HTMLResponse:
    return await _render_person_form(request, message_type="success")


@app.post("/ui/people", response_class=HTMLResponse)
async def submit_person_form(request: Request) -> HTMLResponse:
    form = await request.form()
    form_values = dict(form.multi_items())
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()

    errors: List[str] = []
    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")

    birth_date = _clean_optional(form.get("birth_date"))
    death_date = _clean_optional(form.get("death_date"))
    biography = _clean_optional(form.get("biography"))

    existing_family_id_raw = _clean_optional(form.get("existing_family_id"))
    new_family_name = _clean_optional(form.get("new_family_name"))
    new_family_description = _clean_optional(form.get("new_family_description"))

    family_id: int | None = None

    async with httpx.AsyncClient(app=app, base_url="http://app") as client:
        if new_family_name:
            family_payload = {"name": new_family_name, "description": new_family_description}
            family_response = await client.post("/families", json=family_payload)
            if family_response.status_code == status.HTTP_201_CREATED:
                family_id = family_response.json()["id"]
            else:
                errors.append(
                    "Could not create family: " + _extract_error_detail(family_response)
                )
        elif existing_family_id_raw:
            try:
                family_id = int(existing_family_id_raw)
            except ValueError:
                errors.append("Invalid family selection.")

        location_assignments: List[dict] = []
        role_metadata = _location_role_metadata()
        if not errors:
            for role_meta in role_metadata:
                role_value = role_meta["value"]
                label = role_meta["label"]
                existing_location_raw = _clean_optional(form.get(f"{role_value}_location_id"))
                new_location_name = _clean_optional(form.get(f"{role_value}_location_name"))

                location_id: int | None = None
                if new_location_name:
                    location_payload = {
                        "name": new_location_name,
                        "description": _clean_optional(
                            form.get(f"{role_value}_location_description")
                        ),
                        "city": _clean_optional(form.get(f"{role_value}_location_city")),
                        "state": _clean_optional(form.get(f"{role_value}_location_state")),
                        "country": _clean_optional(
                            form.get(f"{role_value}_location_country")
                        ),
                    }
                    location_response = await client.post("/locations", json=location_payload)
                    if location_response.status_code == status.HTTP_201_CREATED:
                        location_id = location_response.json()["id"]
                    else:
                        errors.append(
                            f"Could not create {label.lower()} location: "
                            + _extract_error_detail(location_response)
                        )
                elif existing_location_raw:
                    try:
                        location_id = int(existing_location_raw)
                    except ValueError:
                        errors.append(f"Invalid {label.lower()} location selection.")

                if location_id is not None:
                    location_assignments.append(
                        {"role": role_value, "location_id": location_id}
                    )

        if errors:
            message = " ".join(errors)
            return await _render_person_form(
                request,
                message=message,
                message_type="error",
                form_values=form_values,
            )

        person_payload = {
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "death_date": death_date,
            "biography": biography,
            "family_id": family_id,
            "locations": location_assignments,
        }
        person_response = await client.post("/people", json=person_payload)

    if person_response.status_code == status.HTTP_201_CREATED:
        person_data = person_response.json()
        message = f"Created {person_data['first_name']} {person_data['last_name']}."
        return await _render_person_form(
            request,
            message=message,
            message_type="success",
            form_values={},
            created_person=person_data,
        )

    error_detail = _extract_error_detail(person_response)
    return await _render_person_form(
        request,
        message=f"Could not create person: {error_detail}",
        message_type="error",
        form_values=form_values,
    )


# Families --------------------------------------------------------------------


@app.post("/families", response_model=schemas.FamilyRead, status_code=status.HTTP_201_CREATED)
def create_family(
    payload: schemas.FamilyCreate, session: Session = Depends(get_session)
) -> schemas.FamilyRead:
    family = models.Family(**payload.model_dump())
    session.add(family)
    session.commit()
    session.refresh(family)
    return family


@app.get("/families", response_model=List[schemas.FamilyRead])
def list_families(session: Session = Depends(get_session)) -> List[schemas.FamilyRead]:
    return list(session.scalars(select(models.Family)))


@app.get("/families/{family_id}", response_model=schemas.FamilyRead)
def get_family(family_id: int, session: Session = Depends(get_session)) -> schemas.FamilyRead:
    family = session.get(models.Family, family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    return family


@app.put("/families/{family_id}", response_model=schemas.FamilyRead)
def update_family(
    family_id: int,
    payload: schemas.FamilyUpdate,
    session: Session = Depends(get_session),
) -> schemas.FamilyRead:
    family = session.get(models.Family, family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(family, key, value)

    session.commit()
    session.refresh(family)
    return family


@app.delete("/families/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family(family_id: int, session: Session = Depends(get_session)) -> None:
    family = session.get(models.Family, family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
    session.delete(family)
    session.commit()


# Locations -------------------------------------------------------------------


@app.post("/locations", response_model=schemas.LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: schemas.LocationCreate, session: Session = Depends(get_session)
) -> schemas.LocationRead:
    location = models.Location(**payload.model_dump())
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@app.get("/locations", response_model=List[schemas.LocationRead])
def list_locations(session: Session = Depends(get_session)) -> List[schemas.LocationRead]:
    return list(session.scalars(select(models.Location)))


@app.get("/locations/{location_id}", response_model=schemas.LocationRead)
def get_location(
    location_id: int, session: Session = Depends(get_session)
) -> schemas.LocationRead:
    location = session.get(models.Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@app.put("/locations/{location_id}", response_model=schemas.LocationRead)
def update_location(
    location_id: int,
    payload: schemas.LocationUpdate,
    session: Session = Depends(get_session),
) -> schemas.LocationRead:
    location = session.get(models.Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(location, key, value)

    session.commit()
    session.refresh(location)
    return location


@app.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: int, session: Session = Depends(get_session)) -> None:
    location = session.get(models.Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    session.delete(location)
    session.commit()


# People ----------------------------------------------------------------------


def _ensure_family_exists(session: Session, family_id: int | None) -> None:
    if family_id is None:
        return
    family = session.get(models.Family, family_id)
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")


@app.post("/people", response_model=schemas.PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(
    payload: schemas.PersonCreate, session: Session = Depends(get_session)
) -> schemas.PersonRead:
    _ensure_family_exists(session, payload.family_id)
    data = payload.model_dump(exclude={"locations"})
    person = models.Person(**data)
    session.add(person)
    session.flush()

    services.apply_person_locations(session, person, payload.locations)
    session.commit()
    session.refresh(person)
    return person


@app.get("/people", response_model=List[schemas.PersonRead])
def list_people(session: Session = Depends(get_session)) -> List[schemas.PersonRead]:
    return list(session.scalars(select(models.Person)))


@app.get("/people/{person_id}", response_model=schemas.PersonRead)
def get_person(person_id: int, session: Session = Depends(get_session)) -> schemas.PersonRead:
    person = session.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@app.put("/people/{person_id}", response_model=schemas.PersonRead)
def update_person(
    person_id: int,
    payload: schemas.PersonUpdate,
    session: Session = Depends(get_session),
) -> schemas.PersonRead:
    person = session.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    if payload.family_id is not None:
        _ensure_family_exists(session, payload.family_id)

    update_data = payload.model_dump(exclude_unset=True, exclude={"locations"})
    for key, value in update_data.items():
        setattr(person, key, value)

    if payload.locations is not None:
        services.apply_person_locations(session, person, payload.locations)

    session.commit()
    session.refresh(person)
    return person


@app.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, session: Session = Depends(get_session)) -> None:
    person = session.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    session.delete(person)
    session.commit()


# Relationships ---------------------------------------------------------------


@app.post(
    "/relationships",
    response_model=schemas.RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    payload: schemas.RelationshipCreate, session: Session = Depends(get_session)
) -> schemas.RelationshipRead:
    relationship = services.create_relationship(session, payload)
    session.commit()
    session.refresh(relationship)
    return relationship


@app.get("/relationships", response_model=List[schemas.RelationshipRead])
def list_relationships(
    session: Session = Depends(get_session),
) -> List[schemas.RelationshipRead]:
    return list(session.scalars(select(models.Relationship)))


@app.put("/relationships/{relationship_id}", response_model=schemas.RelationshipRead)
def update_relationship(
    relationship_id: int,
    payload: schemas.RelationshipUpdate,
    session: Session = Depends(get_session),
) -> schemas.RelationshipRead:
    relationship = session.get(models.Relationship, relationship_id)
    if relationship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    relationship = services.update_relationship(session, relationship, payload)
    session.commit()
    session.refresh(relationship)
    return relationship


@app.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    relationship_id: int, session: Session = Depends(get_session)
) -> None:
    relationship = session.get(models.Relationship, relationship_id)
    if relationship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    services.delete_relationship(session, relationship)
    session.commit()
