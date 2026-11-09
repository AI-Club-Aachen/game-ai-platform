from app.models.agent import Agent
from app.models.job import JobStatus
from app.models.submission import Submission


def submission_has_successful_build(submission: Submission) -> bool:
    return any(
        job.status == JobStatus.COMPLETED and job.image_tag is not None and job.image_id is not None
        for job in submission.build_jobs
    )


def agent_is_playable(agent: Agent) -> bool:
    """Whether the agent can be put in a match: its active submission has a working build."""
    return agent.active_submission is not None and submission_has_successful_build(agent.active_submission)
