from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from lugnut.auth.deps import DB
from lugnut.auth.routes import Reader, Writer
from lugnut.records.models import JobType

router = APIRouter(prefix="/api/job-types")


class JobTypeIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class JobTypeOut(JobTypeIn):
    id: int
    builtin: bool


@router.get("")
def list_job_types(_: Reader, db: DB) -> list[JobTypeOut]:
    return [
        JobTypeOut.model_validate(j, from_attributes=True)
        for j in db.scalars(select(JobType).order_by(JobType.id))
    ]


@router.post("", status_code=201)
def create_job_type(body: JobTypeIn, _: Writer, db: DB) -> JobTypeOut:
    j = JobType(name=body.name, builtin=False)
    db.add(j)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Job type {j.name!r} already exists") from None
    return JobTypeOut.model_validate(j, from_attributes=True)


@router.delete("/{job_type_id}", status_code=204)
def delete_job_type(job_type_id: int, _: Writer, db: DB) -> None:
    j = db.get(JobType, job_type_id)
    if j is None:
        raise HTTPException(404, "Job type not found")
    if j.builtin:
        raise HTTPException(409, "Built-in job types can't be deleted")
    db.delete(j)  # line items using it are set to NULL by the foreign key
    db.commit()
