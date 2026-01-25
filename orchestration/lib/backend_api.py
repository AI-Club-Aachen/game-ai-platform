"""
Tools for calling backend API
Backend URL is in BACKEND_URL environment variable.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackendAPIError(Exception):
    """Base exception for backend API operations."""


class BackendAPI:
    """
    Client for interacting with the backend API.

    This abstraction allows workers to update submission and match status
    without directly accessing the database or importing backend models.
    """

    def __init__(self, backend_url: str | None = None) -> None:
        """
        Initialize backend API client.

        Args:
            backend_url: Backend API base URL. If None, uses BACKEND_URL environment variable
                        or defaults to "http://backend:8000/api/v1"
        """
        if backend_url is None:
            backend_url = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")

        # Remove trailing slash for consistent URL construction
        self.backend_url = backend_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self._client.aclose()

    async def _patch(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Send PATCH request to backend API.

        Args:
            endpoint: API endpoint path (e.g., "/submissions/123")
            data: Request payload

        Returns:
            Response JSON

        Raises:
            BackendAPIError: If request fails
        """
        url = f"{self.backend_url}{endpoint}"
        try:
            response = await self._client.patch(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for PATCH {url}: {e.response.text}")
            raise BackendAPIError(
                f"Failed to PATCH {endpoint}: {e.response.status_code} {e.response.text}"
            ) from e
        except Exception as e:
            logger.error(f"Error calling PATCH {url}: {e}")
            raise BackendAPIError(f"Failed to call {endpoint}: {e}") from e

    async def _get(self, endpoint: str) -> dict[str, Any]:
        """
        Send GET request to backend API.

        Args:
            endpoint: API endpoint path

        Returns:
            Response JSON

        Raises:
            BackendAPIError: If request fails
        """
        url = f"{self.backend_url}{endpoint}"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for GET {url}: {e.response.text}")
            raise BackendAPIError(
                f"Failed to GET {endpoint}: {e.response.status_code} {e.response.text}"
            ) from e
        except Exception as e:
            logger.error(f"Error calling GET {url}: {e}")
            raise BackendAPIError(f"Failed to call {endpoint}: {e}") from e

    # Submission methods

    async def update_submission(
        self,
        submission_id: str,
        status: str,
        logs: str | None = None,
        image_id: str | None = None,
        image_tag: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a submission's status and related fields.

        Args:
            submission_id: Submission UUID
            status: New status (queued, building, completed, failed)
            logs: Optional build logs or error message
            image_id: Optional Docker image ID
            image_tag: Optional Docker image tag

        Returns:
            Updated submission data
        """
        data: dict[str, Any] = {"status": status}
        if logs is not None:
            data["logs"] = logs
        if image_id is not None:
            data["image_id"] = image_id
        if image_tag is not None:
            data["image_tag"] = image_tag

        return await self._patch(f"/submissions/{submission_id}", data)

    async def get_submission(self, submission_id: str) -> dict[str, Any]:
        """
        Get a submission by ID.

        Args:
            submission_id: Submission UUID

        Returns:
            Submission data
        """
        return await self._get(f"/submissions/{submission_id}")

    # Match methods

    async def update_match(
        self,
        match_id: str,
        status: str,
        logs: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update a match's status and related fields.

        Args:
            match_id: Match UUID
            status: New status (queued, running, completed, failed)
            logs: Optional execution logs or error message
            result: Optional match result data (scores, winner, etc.)

        Returns:
            Updated match data
        """
        data: dict[str, Any] = {"status": status}
        if logs is not None:
            data["logs"] = logs
        if result is not None:
            data["result"] = result

        return await self._patch(f"/matches/{match_id}", data)

    async def get_match(self, match_id: str) -> dict[str, Any]:
        """
        Get a match by ID.

        Args:
            match_id: Match UUID

        Returns:
            Match data
        """
        return await self._get(f"/matches/{match_id}")


def get_backend_api(backend_url: str | None = None) -> BackendAPI:
    """
    Factory function to create a BackendAPI instance.

    Args:
        backend_url: Optional backend URL. If None, uses BACKEND_URL env var.

    Returns:
        BackendAPI instance
    """
    return BackendAPI(backend_url=backend_url)
