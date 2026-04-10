from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.deps.services import get_agent_container_service
from app.api.services.agent_container import AgentContainerService, AgentContainerServiceError
from app.models.user import User, UserRole
from app.schemas.agent_container import AgentContainerCreate, AgentContainerRead, AgentContainerUpdate


router = APIRouter()


@router.get("", response_model=list[AgentContainerRead])
def list_agent_containers(
    current_user: Annotated[User, Depends(get_current_user)],
    service: AgentContainerService = Depends(get_agent_container_service),
    skip: int = 0,
    limit: int = 100,
    match_id: UUID | None = None,
    status: str | None = None,
) -> list[AgentContainerRead]:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        return service.list_containers(skip=skip, limit=limit, match_id=match_id, status=status)
    except AgentContainerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/upsert", response_model=AgentContainerRead)
def upsert_agent_container(
    payload: AgentContainerCreate,
    service: AgentContainerService = Depends(get_agent_container_service),
) -> AgentContainerRead:
    """Worker endpoint for writing latest container telemetry snapshots."""
    try:
        return service.upsert_container(payload)
    except AgentContainerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{container_id}", response_model=AgentContainerRead)
def update_agent_container(
    container_id: str,
    payload: AgentContainerUpdate,
    service: AgentContainerService = Depends(get_agent_container_service),
) -> AgentContainerRead:
    try:
        updated = service.update_container(container_id=container_id, payload=payload)
    except AgentContainerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    return updated
