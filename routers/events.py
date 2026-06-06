import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, status
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.event import (
    Event,
    EventCreate,
    EventPublic,
    EventUpdate,
)
from models.player import Player, PlayerPublic
from models.tournament import TournamentPublic
from routers.users import UserDep

tag_metadata = {
    "name": "events",
    "description": "An event is a collection of competitions that happen at a specified time and location.",
    "externalDocs": {
        "description": "Learn more about events here",
        "url": "https://github.com/Alancorleto/perfect-game/blob/main/entities-reference.md#events",
    },
}

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventPublic])
async def list_events(
    session: SessionDep,
    country_code: str | None = Query(default=None, min_length=2, max_length=2),
):
    """List events, optionally filtered by country code."""
    query = select(Event)

    if country_code is not None:
        query = query.where(Event.country_code == country_code.upper())

    events = session.exec(query).all()
    return events


@router.get("/{event_id}", response_model=EventPublic)
async def get_event(event_id: uuid.UUID, session: SessionDep):
    """Get a specific event."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@router.post("/", response_model=EventPublic)
async def create_event(event: EventCreate, session: SessionDep, user: UserDep):
    """Create a new event. The organizer will be the currently logged-in user."""
    db_event = Event.model_validate(event)
    session.add(db_event)
    session.commit()
    session.refresh(db_event)

    db_event.organizers.append(user)
    session.add(db_event)
    session.commit()
    session.refresh(db_event)

    return db_event


@router.patch("/{event_id}", response_model=EventPublic)
async def update_event(
    event_id: uuid.UUID,
    event: EventUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update an event."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not db_event.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this event",
        )

    event_data = event.model_dump(exclude_unset=True)
    db_event.sqlmodel_update(event_data)
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: uuid.UUID, session: SessionDep, user: UserDep) -> None:
    """Delete an event. An event can only be deleted if no rounds have been started for any of its tournaments."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not db_event.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    session.delete(db_event)
    session.commit()


@router.get("/{event_id}/tournaments", response_model=list[TournamentPublic])
async def list_event_tournaments(event_id: uuid.UUID, session: SessionDep):
    """List all tournaments for an event."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event.tournaments


@router.get("/{event_id}/organizers", response_model=list[PlayerPublic])
async def list_event_organizers(event_id: uuid.UUID, session: SessionDep):
    """List all organizers for an event."""
    db_event = session.get(Event, event_id)

    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return [user.player for user in db_event.organizers if user.player is not None]


@router.post("/{event_id}/organizers/{player_id}", response_model=list[PlayerPublic])
async def add_organizer_to_event(
    event_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Add a player as an organizer to an event.

    The organizer's player_id must be provided."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not db_event.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add organizer to this event",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if db_player.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not registered with a user account",
        )

    if db_player.user in db_event.organizers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Player is already an organizer",
        )

    db_event.organizers.append(db_player.user)

    session.commit()

    return [user.player for user in db_event.organizers if user.player is not None]


@router.delete("/{event_id}/organizers/{player_id}", response_model=list[PlayerPublic])
async def remove_organizer_from_event(
    event_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove an organizer from an event.

    The organizer's player_id must be provided.

    An event must always have at least one organizer."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not db_event.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove organizer from this event",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if db_player.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not registered with a user account",
        )

    if db_player.user not in db_event.organizers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Player is not an organizer"
        )

    if len(db_event.organizers) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last organizer from the event",
        )

    db_event.organizers.remove(db_player.user)

    session.commit()

    return [user.player for user in db_event.organizers if user.player is not None]


@router.post("/{event_id}/logo", response_model=EventPublic)
async def upload_event_logo(
    event_id: uuid.UUID,
    logo: Annotated[bytes, File()],
    session: SessionDep,
    user: UserDep,
):
    """Upload an event logo."""
    db_event = session.get(Event, event_id)
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not db_event.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    file_name = f"{db_event.id}.png"
    db_event.logo_url = await upload_image(logo, file_name, "event_logos")

    session.add(db_event)
    session.commit()
    session.refresh(db_event)

    return db_event
