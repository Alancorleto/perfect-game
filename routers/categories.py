import datetime
import uuid

from fastapi import APIRouter, HTTPException, status
from httpx import Request
from sqlmodel import select

from database import SessionDep
from models.category import Category, CategoryCreate, CategoryPublic, CategoryUpdate
from models.category_invitation import (
    CategoryInvitation,
    CategoryInvitationPublic,
    CategoryJoinRequest,
    CategoryJoinRequestPublic,
    RequestStatus,
)
from models.tournament import Tournament
from routers.players import Player, PlayerPublic
from routers.rounds import RoundPublic, RoundState
from routers.users import UserDep

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryPublic])
async def list_categories(session: SessionDep):
    """List all categories"""
    categories = session.exec(select(Category)).all()
    return categories


@router.get("/{category_id}", response_model=CategoryPublic)
async def get_category(category_id: uuid.UUID, session: SessionDep):
    """Get a specific category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return db_category


@router.post("/", response_model=CategoryPublic)
async def create_category(category: CategoryCreate, session: SessionDep, user: UserDep):
    """Create a new category"""

    tournament = session.get(Tournament, category.tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    db_category = Category.model_validate(category)

    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category


@router.patch("/{category_id}", response_model=CategoryPublic)
async def update_category(
    category_id: uuid.UUID, category: CategoryUpdate, session: SessionDep, user: UserDep
):
    """Update a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    category_data = category.model_dump(exclude_unset=True)
    db_category.sqlmodel_update(category_data)

    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    session.delete(db_category)
    session.commit()


@router.post("/{category_id}/players/guest", response_model=list[PlayerPublic])
async def add_guest_player_to_category(
    category_id: uuid.UUID,
    player_id: uuid.UUID,
    session: SessionDep,
    user: UserDep,
):
    """Add a guest player to a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if db_player.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already registered",
        )

    db_category.add_player(db_player)
    session.commit()
    session.refresh(db_category)

    return db_category.get_players_by_nickname()


@router.post("/{category_id}/players/bulk", response_model=list[PlayerPublic])
async def bulk_add_guest_players_to_category(
    category_id: uuid.UUID,
    player_ids: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Bulk add guest players to a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    for player_id in player_ids:
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )

        if db_player.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player with ID {player_id} is already registered",
            )

        db_category.add_player(db_player)

    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category.get_players_by_nickname()


@router.get("/{category_id}/invitations", response_model=list[CategoryInvitationPublic])
async def list_category_invitations(
    category_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """List all invitations for a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this category's invitations",
        )

    invitations: list[CategoryInvitationPublic] = []
    for invitation in db_category.invitations:
        if invitation.issued_at < datetime.datetime.now() - datetime.timedelta(days=1):
            continue

        invitations.append(
            CategoryInvitationPublic(
                category_id=invitation.category_id,
                player=invitation.player,
                status=invitation.status,
            )
        )

    return invitations


@router.post(
    "/{category_id}/invitations/{player_id}/", status_code=status.HTTP_204_NO_CONTENT
)
async def invite_player_to_category(
    category_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Invite a player to a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit this category",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if not db_player.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not registered",
        )

    if db_player in db_category.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the category",
        )

    if db_player.user == user:
        db_category.add_player(db_player)
        session.commit()
        return

    db_invitation = next(
        (
            invitation
            for invitation in db_category.invitations
            if invitation.player_id == player_id
        ),
        CategoryInvitation(category_id=category_id, player_id=player_id),
    )

    db_invitation.status = RequestStatus.PENDING
    session.add(db_invitation)

    session.commit()


@router.post("/{category_id}/invitations/accept")
async def accept_category_invitation(
    category_id: uuid.UUID, session: SessionDep, user: UserDep
):
    player = user.player
    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    db_invitation = session.get(CategoryInvitation, (category_id, player.id))
    if not db_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if db_invitation.status == RequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    db_invitation.status = RequestStatus.ACCEPTED

    db_category.add_player(player)
    session.commit()


@router.post("/{category_id}/invitations/decline")
async def decline_category_invitation(
    category_id: uuid.UUID, session: SessionDep, user: UserDep
):
    player = user.player
    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    db_invitation = session.get(CategoryInvitation, (category_id, player.id))
    if not db_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if db_invitation.status == RequestStatus.DECLINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already declined",
        )

    if db_invitation.status == RequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    db_invitation.status = RequestStatus.DECLINED

    session.commit()


@router.get(
    "/{category_id}/join_requests", response_model=list[CategoryJoinRequestPublic]
)
async def list_category_join_requests(
    category_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """List all join requests for a category"""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit category",
        )

    join_requests: list[CategoryJoinRequestPublic] = []
    for request in category.join_requests:
        if request.issued_at < datetime.datetime.now() - datetime.timedelta(days=1):
            continue

        join_requests.append(
            CategoryJoinRequestPublic(
                player_id=request.player_id,
                category=request.category,
                status=request.status,
            )
        )

    return join_requests


@router.post("/{category_id}/join_requests", status_code=status.HTTP_204_NO_CONTENT)
async def request_join_category(
    category_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Request to join a category"""
    player = user.player

    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if player in db_category.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player already in category",
        )

    if db_category.auto_accept_join_requests:
        db_category.add_player(player)
        session.commit()
        return

    join_request = next(
        (request for request in db_category.join_requests if request.player == player),
        CategoryJoinRequest(category_id=category_id, player_id=player.id),
    )

    join_request.status = RequestStatus.PENDING

    session.add(join_request)

    session.commit()


@router.post("/{category_id}/join_requests/{player_id}/accept")
async def accept_category_join_request(
    category_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this category",
        )

    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if player in db_category.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the category",
        )

    join_request = next(
        (
            request
            for request in db_category.join_requests
            if request.player_id == player_id
        ),
        None,
    )
    if not join_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found"
        )

    if join_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Join request is not pending",
        )

    join_request.status = RequestStatus.ACCEPTED

    db_category.add_player(player)

    session.commit()


@router.post("/{category_id}/join_requests/{player_id}/decline")
async def decline_category_join_request(
    category_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this category",
        )

    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if player in db_category.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the category",
        )

    join_request = next(
        (
            request
            for request in db_category.join_requests
            if request.player_id == player_id
        ),
        None,
    )
    if not join_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found"
        )

    if join_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Join request is not pending",
        )

    join_request.status = RequestStatus.DECLINED

    session.commit()


@router.get("/{category_id}/players", response_model=list[PlayerPublic])
async def list_players_in_category(category_id: uuid.UUID, session: SessionDep):
    """List all players in a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return db_category.get_players_by_nickname()


@router.delete("/{category_id}/players/{player_id}", response_model=list[PlayerPublic])
async def remove_player_from_category(
    category_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove a player from a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if db_player not in db_category.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found in category"
        )

    db_category.remove_player(db_player)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category.get_players_by_nickname()


@router.get("/{category_id}/rounds", response_model=list[RoundPublic])
async def list_rounds_in_category(
    category_id: uuid.UUID,
    session: SessionDep,
):
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    return db_category.get_rounds_by_order()


@router.put("/{category_id}/rounds/order", response_model=list[RoundPublic])
async def change_round_order_in_category(
    category_id: uuid.UUID,
    round_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Change the order of rounds within a category."""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not db_category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    existing_rounds = {round.id: round for round in db_category.rounds}

    if len(round_order) != len(existing_rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round order must match the number of rounds in the category",
        )

    if set(round_order) != set(existing_rounds.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round order must have the same rounds as the category",
        )

    if any(
        round.state != RoundState.NOT_STARTED
        and round_order[round.order_index] != round_id
        for round_id, round in existing_rounds.items()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change round order for a round that has already started",
        )

    for new_index, round_id in enumerate(round_order):
        round = existing_rounds[round_id]
        if not round:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
            )

        round.order_index = new_index
        session.add(round)

    session.commit()
    session.refresh(db_category)

    return db_category.get_rounds_by_order()
