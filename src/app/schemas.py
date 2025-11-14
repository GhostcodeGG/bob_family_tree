"""Pydantic schemas for API serialization and validation."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    role: LocationRole
    location_id: Optional[int] = Field(default=None, description="Existing location identifier")
    new_location: Optional[LocationCreate] = Field(
        default=None, description="Data for creating a new location"
    )

    @model_validator(mode="after")
    def _validate_location_reference(self) -> "PersonLocationAssignment":
        if self.location_id is None and self.new_location is None:
            raise ValueError("Either location_id or new_location must be provided")
        if self.location_id is not None and self.new_location is not None:
            raise ValueError("Provide only one of location_id or new_location")
        return self


class PersonLocationRead(BaseModel):
    role: LocationRole
    location: LocationRead

    model_config = ConfigDict(from_attributes=True)


class PersonBase(BaseModel):
    first_name: str = Field(..., max_length=64)
    last_name: str = Field(..., max_length=64)
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    biography: Optional[str] = None
    family_id: Optional[int] = Field(default=None, description="Identifier of the family")


class PersonCreate(PersonBase):
    locations: List[PersonLocationAssignment] = Field(default_factory=list)
    family: Optional[FamilyCreate] = Field(
        default=None, description="Optional nested payload to create a family"
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
