from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import VerifiedGuestOrHigher, require_worker_api_key
from app.api.deps.services import get_agent_container_service
from app.api.services.agent_container import AgentContainerService, AgentContainerServiceError
from app.models.user import UserRole
from app.schemas.agent_container import (
    AgentContainerCreate,
    AgentContainerListResponse,
    AgentContainerRead,
    AgentContainerUpdate,
)


router = APIRouter()


@router.get("", response_model=AgentContainerListResponse)
def list_agent_containers(
    current_user: VerifiedGuestOrHigher,
    service: AgentContainerService = Depends(get_agent_container_service),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    match_id: UUID | None = None,
    status: str | None = None,
) -> AgentContainerListResponse:
    owner_user_id = None if current_user.role == UserRole.ADMIN else current_user.id

    try:
        items, total, status_counts = service.list_container_page(
            skip=skip,
            limit=limit,
            match_id=match_id,
            status=status,
            owner_user_id=owner_user_id,
        )
    except AgentContainerServiceError as e:
        # The `status` query param shadows fastapi.status here, so use the literal code.
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AgentContainerListResponse(
        data=[AgentContainerRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        status_counts=status_counts,
    )


@router.post("/upsert", response_model=AgentContainerRead, dependencies=[Depends(require_worker_api_key)])
def upsert_agent_container(
    payload: AgentContainerCreate,
    service: AgentContainerService = Depends(get_agent_container_service),
) -> AgentContainerRead:
    """Write latest container telemetry snapshots. Worker API key required."""
    try:
        return service.upsert_container(payload)
    except AgentContainerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{container_id}", response_model=AgentContainerRead, dependencies=[Depends(require_worker_api_key)])
def update_agent_container(
    container_id: str,
    payload: AgentContainerUpdate,
    service: AgentContainerService = Depends(get_agent_container_service),
) -> AgentContainerRead:
    """Update a container record. Worker API key required."""
    try:
        updated = service.update_container(container_id=container_id, payload=payload)
    except AgentContainerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    return updated
