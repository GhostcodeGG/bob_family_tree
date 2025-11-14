"""FastAPI application exposing family tree functionality."""

from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas, services
from .config import get_settings
from .database import engine, get_session

models.Base.metadata.create_all(bind=engine)

settings = get_settings()
app = FastAPI(title=settings.app_name)


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
    if payload.family is not None and payload.family_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either family_id or family payload, not both",
        )

    family_id = payload.family_id
    if payload.family is not None:
        family = models.Family(**payload.family.model_dump())
        session.add(family)
        session.flush()
        family_id = family.id
    else:
        _ensure_family_exists(session, family_id)

    data = payload.model_dump(exclude={"locations", "family", "family_id"})
    data["family_id"] = family_id
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
