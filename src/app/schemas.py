"""Pydantic schemas for API serialization and validation."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import LocationRole, RelationshipType


class LocationBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=128)
    state: Optional[str] = Field(default=None, max_length=128)
    country: Optional[str] = Field(default=None, max_length=128)


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=128)
    state: Optional[str] = Field(default=None, max_length=128)
    country: Optional[str] = Field(default=None, max_length=128)


class LocationRead(LocationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PersonLocationAssignment(BaseModel):
    role: LocationRole = Field(
        ...,
        description=(
            "Role describing how the person is connected to the location. "
            "Accepted values are: 'birthplace' (where the person was born), "
            "'residence' (a place they lived), and 'burial' (their resting place)."
        ),
        examples=["birthplace"],
    )
    location_id: int = Field(
        ..., description="Identifier of an existing location record.", examples=[3]
    )


class PersonLocationRead(BaseModel):
    role: LocationRole
    location: LocationRead

    model_config = ConfigDict(from_attributes=True)


class PersonBase(BaseModel):
    first_name: str = Field(
        ...,
        max_length=64,
        description="Given name of the person.",
        examples=["Alice"],
    )
    last_name: str = Field(
        ...,
        max_length=64,
        description="Family name or surname of the person.",
        examples=["Johnson"],
    )
    birth_date: Optional[date] = Field(
        default=None,
        description="Date of birth in ISO 8601 format (YYYY-MM-DD).",
        examples=["1984-05-12"],
    )
    death_date: Optional[date] = Field(
        default=None,
        description="Date of death in ISO 8601 format, if applicable.",
        examples=["2035-09-01"],
    )
    biography: Optional[str] = Field(
        default=None,
        description="Narrative summary or key facts about the person's life.",
        examples=[
            "Alice was an avid gardener who moved to Springfield in the early 2000s."
        ],
    )
    family_id: Optional[int] = Field(
        default=None,
        description="Identifier of the family this person belongs to, if any.",
        examples=[1],
    )


class PersonCreate(PersonBase):
    locations: List[PersonLocationAssignment] = Field(
        default_factory=list,
        description="List of location assignments describing key places in the person's life.",
        examples=[
            [
                {"role": "birthplace", "location_id": 2},
                {"role": "residence", "location_id": 5},
            ]
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Alice",
                "last_name": "Johnson",
                "birth_date": "1984-05-12",
                "death_date": None,
                "biography": "Alice was an avid gardener who moved to Springfield in the early 2000s.",
                "family_id": 1,
                "locations": [
                    {"role": "birthplace", "location_id": 2},
                    {"role": "residence", "location_id": 5},
                ],
            }
        }
    )


class PersonUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=64)
    last_name: Optional[str] = Field(default=None, max_length=64)
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    biography: Optional[str] = None
    family_id: Optional[int] = Field(default=None, description="Identifier of the family")
    locations: Optional[List[PersonLocationAssignment]] = None


class PersonRead(PersonBase):
    id: int
    locations: List[PersonLocationRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FamilyBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None


class FamilyCreate(FamilyBase):
    pass


class FamilyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = None


class FamilyRead(FamilyBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RelationshipBase(BaseModel):
    from_person_id: int
    to_person_id: int
    type: RelationshipType


class RelationshipCreate(RelationshipBase):
    pass


class RelationshipUpdate(BaseModel):
    type: RelationshipType


class RelationshipRead(RelationshipBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
