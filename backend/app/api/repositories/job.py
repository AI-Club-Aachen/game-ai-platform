from uuid import UUID

from sqlmodel import Session

from app.models.job import BuildJob, MatchJob


class JobRepository:
    """
    Repository for managing BuildJob and MatchJob entities.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def save_build_job(self, job: BuildJob) -> BuildJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_build_job(self, job_id: str | UUID) -> BuildJob | None:
        return self.session.get(BuildJob, job_id)

    def save_match_job(self, job: MatchJob) -> MatchJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_match_job(self, job_id: str | UUID) -> MatchJob | None:
        return self.session.get(MatchJob, job_id)
