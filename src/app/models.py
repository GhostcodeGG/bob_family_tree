"""Database models for the family tree domain."""

from __future__ import annotations

from datetime import date
import enum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()


class RelationshipType(str, enum.Enum):
    """Supported relationship types between two people."""

    parent = "parent"
    child = "child"
    spouse = "spouse"


class LocationRole(str, enum.Enum):
    """Roles that a location can play for a person."""

    birthplace = "birthplace"
    residence = "residence"
    burial = "burial"


class Family(Base):
    """Represents a family unit or surname group."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    members: Mapped[list["Person"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )


class Person(Base):
    """Individual person that can belong to a family and relationships."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date())
    death_date: Mapped[date | None] = mapped_column(Date())
    biography: Mapped[str | None] = mapped_column(Text())
    family_id: Mapped[int | None] = mapped_column(ForeignKey("families.id"), nullable=True)

    family: Mapped[Family | None] = relationship(back_populates="members")
    relationships_from: Mapped[list["Relationship"]] = relationship(
        back_populates="from_person",
        foreign_keys="Relationship.from_person_id",
        cascade="all, delete-orphan",
    )
    relationships_to: Mapped[list["Relationship"]] = relationship(
        back_populates="to_person",
        foreign_keys="Relationship.to_person_id",
        cascade="all, delete-orphan",
    )
    locations: Mapped[list["PersonLocation"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class Relationship(Base):
    """Relationship link between two people."""

    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    to_person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "from_person_id", "to_person_id", "type", name="uq_relationship_pair"
        ),
    )

    from_person: Mapped[Person] = relationship(
        back_populates="relationships_from", foreign_keys=[from_person_id]
    )
    to_person: Mapped[Person] = relationship(
        back_populates="relationships_to", foreign_keys=[to_person_id]
    )


class Location(Base):
    """Physical location that can be attached to people."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    city: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))

    person_links: Mapped[list["PersonLocation"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )


class PersonLocation(Base):
    """Associates a person with a location role."""

    __tablename__ = "person_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[LocationRole] = mapped_column(Enum(LocationRole), nullable=False)

    __table_args__ = (
        UniqueConstraint("person_id", "role", name="uq_person_location_role"),
    )

    person: Mapped[Person] = relationship(back_populates="locations")
    location: Mapped[Location] = relationship(back_populates="person_links")
