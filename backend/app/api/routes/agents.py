from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    VerifiedGuestOrHigher,
    VerifiedUserOrHigher,
    WorkerOrVerifiedUser,
    get_agent_service,
)
from app.api.services.agent import AgentNotFoundError, AgentPermissionError, AgentService, AgentValidationError
from app.models.user import UserRole
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate


router = APIRouter()


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_create: AgentCreate,
    current_user: VerifiedUserOrHigher,
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Create a new agent for the current user. Requires the USER role or higher.
    """
    if agent_create.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create agent for another user")
    try:
        return service.create_agent(agent_create)
    except AgentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except AgentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/leaderboard/{game_type}", response_model=list[dict])
def get_leaderboard(
    game_type: str,
    _current_user: VerifiedGuestOrHigher,
    service: AgentService = Depends(get_agent_service),
    limit: int = 100,
) -> list[dict]:
    """
    Get leaderboard for a specific game type. Requires a verified login.
    """
    return service.get_leaderboard(game_type, limit)


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(
    agent_id: UUID,
    actor: WorkerOrVerifiedUser,
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Get an agent by ID. Accessible to the owning user, admins, and the worker
    (via x-api-key; needed by the build/match workers).
    """
    try:
        agent = service.get_agent_by_id(agent_id)
        if (
            not actor.is_worker
            and agent.user_id != actor.user.id
            and actor.user.role != UserRole.ADMIN
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this agent")
        return agent  # noqa: TRY300
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("", response_model=list[AgentRead])
def list_agents(
    current_user: VerifiedGuestOrHigher,
    service: AgentService = Depends(get_agent_service),
    skip: int = 0,
    limit: int = 20,
    all_users: bool = False,
) -> list[AgentRead]:
    """
    List agents. Requires a verified login.
    If all_users is True and user is admin, lists all agents.
    Otherwise lists agents for the current user.
    """
    if all_users and current_user.role == UserRole.ADMIN:
        agents, _ = service.list_agents(skip=skip, limit=limit, user_id=None)
    else:
        agents, _ = service.list_agents(skip=skip, limit=limit, user_id=current_user.id)
    return agents


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    current_user: VerifiedUserOrHigher,
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Update an agent's name or active submission. Requires the USER role or
    higher; only the owner or an admin may update.
    """
    try:
        return service.update_agent(
            agent_id, agent_update, current_user.id, is_admin=current_user.role == UserRole.ADMIN
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AgentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except AgentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    current_user: VerifiedUserOrHigher,
    service: AgentService = Depends(get_agent_service),
) -> None:
    """
    Delete an agent. Requires the USER role or higher; only the owner or an
    admin may delete.
    """
    try:
        service.delete_agent(agent_id, current_user.id, is_admin=current_user.role == UserRole.ADMIN)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AgentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
