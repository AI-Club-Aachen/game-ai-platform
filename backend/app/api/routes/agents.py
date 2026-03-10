from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_agent_service, get_current_user
from app.api.services.agent import AgentNotFoundError, AgentPermissionError, AgentService
from app.models.user import User, UserRole
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate


router = APIRouter()


@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_create: AgentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Create a new agent for the current user.
    Note: In production, consider validating that user_id matches current_user.id.
    """
    if agent_create.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create agent for another user"
        )
    return service.create_agent(agent_create)


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Get an agent by ID.
    """
    try:
        agent = service.get_agent_by_id(agent_id)
        if agent.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this agent"
            )
        return agent  # noqa: TRY300
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/", response_model=list[AgentRead])
def list_agents(
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentService = Depends(get_agent_service),
    skip: int = 0,
    limit: int = 20,
) -> list[AgentRead]:
    """
    List agents for the current user.
    """
    agents, _ = service.list_user_agents(current_user.id, skip, limit)
    return agents


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    """
    Update an agent's active submission or stats.
    """
    try:
        return service.update_agent(
            agent_id,
            agent_update,
            current_user.id,
            is_admin=current_user.role == UserRole.ADMIN
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AgentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentService = Depends(get_agent_service),
) -> None:
    """
    Delete an agent.
    """
    try:
        service.delete_agent(
            agent_id,
            current_user.id,
            is_admin=current_user.role == UserRole.ADMIN
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AgentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
