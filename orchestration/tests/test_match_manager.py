import asyncio

import pytest

from lib import match_manager


def test_completed_build_jobs_newest_first_filters_and_sorts():
    jobs = [
        {
            "id": "old",
            "status": "completed",
            "image_tag": "agent-old:latest",
            "created_at": "2026-06-01T22:01:59+00:00",
        },
        {
            "id": "failed-newer",
            "status": "failed",
            "image_tag": "agent-failed:latest",
            "created_at": "2026-06-03T14:10:00+00:00",
        },
        {
            "id": "new",
            "status": "completed",
            "image_tag": "agent-new:latest",
            "created_at": "2026-06-03T14:08:09+00:00",
        },
        {
            "id": "missing-tag",
            "status": "completed",
            "created_at": "2026-06-04T14:08:09+00:00",
        },
    ]

    sorted_jobs = match_manager._completed_build_jobs_newest_first(jobs)

    assert [job["id"] for job in sorted_jobs] == ["new", "old"]


def test_get_agent_image_tags_skips_missing_newest_image(monkeypatch):
    class FakeAPI:
        async def get_agent(self, agent_id):
            return {"active_submission_id": "submission-1"}

        async def get_submission(self, submission_id):
            return {
                "build_jobs": [
                    {
                        "id": "old-missing",
                        "status": "completed",
                        "image_tag": "agent-old:latest",
                        "created_at": "2026-06-01T22:01:59+00:00",
                    },
                    {
                        "id": "new-existing",
                        "status": "completed",
                        "image_tag": "agent-new:latest",
                        "created_at": "2026-06-03T14:08:09+00:00",
                    },
                ]
            }

    monkeypatch.setattr(match_manager, "_image_exists", lambda tag: tag == "agent-new:latest")

    assert asyncio.run(match_manager._get_agent_image_tags(["agent-1"], FakeAPI())) == ["agent-new:latest"]


def test_get_agent_image_tags_falls_back_to_older_existing_image(monkeypatch):
    class FakeAPI:
        async def get_agent(self, agent_id):
            return {"active_submission_id": "submission-1"}

        async def get_submission(self, submission_id):
            return {
                "build_jobs": [
                    {
                        "id": "old-existing",
                        "status": "completed",
                        "image_tag": "agent-old:latest",
                        "created_at": "2026-06-01T22:01:59+00:00",
                    },
                    {
                        "id": "new-missing",
                        "status": "completed",
                        "image_tag": "agent-new:latest",
                        "created_at": "2026-06-03T14:08:09+00:00",
                    },
                ]
            }

    monkeypatch.setattr(match_manager, "_image_exists", lambda tag: tag == "agent-old:latest")

    assert asyncio.run(match_manager._get_agent_image_tags(["agent-1"], FakeAPI())) == ["agent-old:latest"]


def test_get_agent_image_tags_reports_all_missing_images(monkeypatch):
    rebuild_calls = []

    class FakeAPI:
        async def get_agent(self, agent_id):
            return {"active_submission_id": "submission-1"}

        async def get_submission(self, submission_id):
            return {
                "build_jobs": [
                    {
                        "id": "old-missing",
                        "status": "completed",
                        "image_tag": "agent-old:latest",
                        "created_at": "2026-06-01T22:01:59+00:00",
                    },
                    {
                        "id": "new-missing",
                        "status": "completed",
                        "image_tag": "agent-new:latest",
                        "created_at": "2026-06-03T14:08:09+00:00",
                    },
                ]
            }

        async def rebuild_submission(self, submission_id):
            rebuild_calls.append(submission_id)
            return {"id": "rebuild-1"}

        async def get_build_job(self, job_id):
            return {"id": job_id, "status": "completed", "image_tag": "agent-rebuilt:latest"}

    monkeypatch.setattr(match_manager, "_image_exists", lambda tag: tag == "agent-rebuilt:latest")
    monkeypatch.setattr(match_manager, "IMAGE_REBUILD_POLL_SECONDS", 0)

    image_tags = asyncio.run(match_manager._get_agent_image_tags(["agent-1"], FakeAPI()))

    assert image_tags == ["agent-rebuilt:latest"]
    assert rebuild_calls == ["submission-1"]


def test_get_agent_image_tags_raises_when_rebuild_image_still_missing(monkeypatch):
    class FakeAPI:
        async def get_agent(self, agent_id):
            return {"active_submission_id": "submission-1"}

        async def get_submission(self, submission_id):
            return {
                "build_jobs": [
                    {
                        "id": "missing",
                        "status": "completed",
                        "image_tag": "agent-missing:latest",
                        "created_at": "2026-06-03T14:08:09+00:00",
                    },
                ]
            }

        async def rebuild_submission(self, submission_id):
            return {"id": "rebuild-1"}

        async def get_build_job(self, job_id):
            return {"id": job_id, "status": "completed", "image_tag": "agent-rebuilt:latest"}

    monkeypatch.setattr(match_manager, "_image_exists", lambda tag: False)
    monkeypatch.setattr(match_manager, "IMAGE_REBUILD_POLL_SECONDS", 0)

    with pytest.raises(match_manager.AgentCommunicationError) as exc_info:
        asyncio.run(match_manager._get_agent_image_tags(["agent-1"], FakeAPI()))

    assert "produced image" in str(exc_info.value)
    assert "still not available locally" in str(exc_info.value)