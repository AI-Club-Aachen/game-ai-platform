from app.models.job import JobStatus
from app.models.submission import Submission


def submission_has_successful_build(submission: Submission) -> bool:
    return any(
        job.status == JobStatus.COMPLETED and job.image_tag is not None and job.image_id is not None
        for job in submission.build_jobs
    )
