import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.deps.db import get_db
from app.api.deps.users import get_current_user
from app.core.queue import job_queue
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionRead

router = APIRouter()

# Directory to store uploaded zips temporarily or permanently
UPLOAD_DIR = Path("uploads/submissions")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Upload an agent zip file and queue it for building.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed.")

    submission = Submission(
        user_id=current_user.id,
        object_path="pending",
        status="queued"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    safe_filename = f"{submission.id}.zip"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        db.delete(submission)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    submission.object_path = str(file_path.absolute())
    db.add(submission)
    db.commit()
    db.refresh(submission)

    await job_queue.enqueue_build(submission.id, submission.object_path)

    return submission


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: str, # UUID
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Ideally check if user owns submission or is admin
    if submission.user_id != current_user.id and current_user.role != "admin": # assuming role logic
         raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    return submission


@router.get("/", response_model=list[SubmissionRead])
def list_submissions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    query = select(Submission).where(Submission.user_id == current_user.id).offset(skip).limit(limit)
    return db.exec(query).all()
