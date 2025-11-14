"""Domain services encapsulating complex operations."""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas

RECIPROCAL_RELATIONSHIPS: dict[models.RelationshipType, models.RelationshipType] = {
    models.RelationshipType.parent: models.RelationshipType.child,
    models.RelationshipType.child: models.RelationshipType.parent,
    models.RelationshipType.spouse: models.RelationshipType.spouse,
}


def _get_person(session: Session, person_id: int) -> models.Person:
    person = session.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


def apply_person_locations(
    session: Session, person: models.Person, assignments: Iterable[schemas.PersonLocationAssignment]
) -> None:
    """Synchronize person location associations with supplied assignments."""

    materialized = list(assignments)

    seen_roles: set[models.LocationRole] = set()
    for assignment in materialized:
        if assignment.role in seen_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate location role '{assignment.role}' in request",
            )
        seen_roles.add(assignment.role)

    existing_by_role = {link.role: link for link in person.locations}
    requested_roles = {assignment.role for assignment in materialized}

    # Remove roles that are no longer present
    for role, link in list(existing_by_role.items()):
        if role not in requested_roles:
            session.delete(link)

    for assignment in materialized:
        if assignment.new_location is not None:
            location = models.Location(**assignment.new_location.model_dump())
            session.add(location)
            session.flush()
        else:
            location = session.get(models.Location, assignment.location_id)
            if location is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location {assignment.location_id} not found",
                )
        link = existing_by_role.get(assignment.role)
        if link is None:
            link = models.PersonLocation(person=person, location=location, role=assignment.role)
            session.add(link)
            existing_by_role[assignment.role] = link
        else:
            link.location = location


def create_relationship(
    session: Session, payload: schemas.RelationshipCreate
) -> models.Relationship:
    """Create a relationship ensuring reciprocal links are maintained."""

    if payload.from_person_id == payload.to_person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create relationship with the same person",
        )

    _get_person(session, payload.from_person_id)
    _get_person(session, payload.to_person_id)

    existing = session.scalar(
        select(models.Relationship).where(
            models.Relationship.from_person_id == payload.from_person_id,
            models.Relationship.to_person_id == payload.to_person_id,
            models.Relationship.type == payload.type,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relationship already exists",
        )

    relationship = models.Relationship(
        from_person_id=payload.from_person_id,
        to_person_id=payload.to_person_id,
        type=payload.type,
    )
    session.add(relationship)

    _ensure_reciprocal(session, relationship)
    session.flush()
    return relationship


def update_relationship(
    session: Session, relationship: models.Relationship, payload: schemas.RelationshipUpdate
) -> models.Relationship:
    """Update relationship type and adjust reciprocal links."""

    if relationship.type == payload.type:
        return relationship

    _remove_reciprocal(session, relationship)
    relationship.type = payload.type
    session.flush()
    _ensure_reciprocal(session, relationship)
    session.flush()
    return relationship


def delete_relationship(session: Session, relationship: models.Relationship) -> None:
    """Remove a relationship and its reciprocal counterpart."""

    _remove_reciprocal(session, relationship)
    session.delete(relationship)


def _ensure_reciprocal(session: Session, relationship: models.Relationship) -> None:
    reciprocal_type = RECIPROCAL_RELATIONSHIPS.get(relationship.type)
    if reciprocal_type is None:
        return

    reciprocal_exists = session.scalar(
        select(models.Relationship).where(
            models.Relationship.from_person_id == relationship.to_person_id,
            models.Relationship.to_person_id == relationship.from_person_id,
            models.Relationship.type == reciprocal_type,
        )
    )
    if reciprocal_exists is None:
        session.add(
            models.Relationship(
                from_person_id=relationship.to_person_id,
                to_person_id=relationship.from_person_id,
                type=reciprocal_type,
            )
        )


def _remove_reciprocal(session: Session, relationship: models.Relationship) -> None:
    reciprocal_type = RECIPROCAL_RELATIONSHIPS.get(relationship.type)
    if reciprocal_type is None:
        return

    reciprocal = session.scalar(
        select(models.Relationship).where(
            models.Relationship.from_person_id == relationship.to_person_id,
            models.Relationship.to_person_id == relationship.from_person_id,
            models.Relationship.type == reciprocal_type,
        )
    )
    if reciprocal is not None:
        session.delete(reciprocal)
