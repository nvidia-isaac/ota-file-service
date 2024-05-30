"""
SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classes import models, schemas

def get_files(db: Session, *conditions, **criterias):
    """Get files from table according to criteria

    Args:
        db (Session): A database session.
        conditions: Parameter for sqlalchemy.select.filter(). Used for more complicated search,
                    e.g., File.file_metadata['type'].astext == 'test'
        criteria: Parameter for sqlalchemy.select.filter_by().
                  Filtering criterions, e.g., s3_object_name='test'
    Returns:
        Sequence: A list of files filtered by criteria
    """
    statement = select(models.File).filter(*conditions)
    statement = statement.filter_by(**criterias)
    statement = statement.order_by(models.File.timestamp.desc())
    return db.scalars(statement).all()

def create_file(db: Session, file: schemas.FileCreate, file_name: Optional[str],
                sha256: str,
                timestamp: datetime):
    """Create an entry in the 'file' table

    Args:
        db (Session): A database session
        file (schemas.FileCreate): File info
        file_name: file name
        sha256: hash code
        timestamp: timestamp
    Returns:
        models.File: The file entry created
    """
    db_file = models.File(
        robot_id=file.robot_id,
        robot_type=file.robot_type,
        robot_version=file.robot_version,
        file_name=file_name,
        sha256=sha256,
        timestamp=timestamp,
        deploy_path=file.deploy_path,
        s3_bucket=file.s3_bucket,
        s3_object_name = file.s3_object_name,
        file_metadata = file.file_metadata,
        valid=True
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def update_file(db: Session, db_file: models.File, file_info: schemas.FileCreate,
                timestamp: Optional[datetime] = None,
                file_name: Optional[str] = None,
                sha256: Optional[str] = None,
                valid: Optional[bool] = None):
    """Update an entry in the 'file' table

    Args:
        db (Session): A database session
        db_file (models.File): database object to update
        file_info (schemas.FileCreate): File info
        sha256 (Optional[str]): hash code
        timestamp: timestamp
        valid (Optional[bool]): Update the valid field
    Returns:
        models.File: The file entry updated
    """
    update_data = file_info.model_dump(exclude_unset=True)
    for field in update_data:
        setattr(db_file, field, update_data[field])
    if timestamp:
        db_file.timestamp = timestamp
    if sha256:
        db_file.sha256 = sha256
    if file_name:
        db_file.file_name = file_name
    if valid is not None:
        db_file.valid = valid
    db.commit()
    db.refresh(db_file)
    return db_file

def delete_file(db: Session, s3_object_name: str, s3_bucket: str):
    """delete a file entry

    Args:
        s3_object_name (str): S3 object name to delete
        s3_bucket (str): S3 bucket that stores the file
        db (Session): A database session.
    """
    db_file = db.get(models.File, (s3_bucket, s3_object_name))
    db.delete(db_file)
    db.commit()
    return db_file

def create_or_update_deploy_target(db: Session, robot_id: str, deploy_path: str,
                                   s3_bucket: str, s3_object_name: str):
    """Create or update an entry in the 'deploy_target' table.

    Args:
        db (Session): A database session
        robot_id (str): Robot id
        deploy_path (str): Path to deploy
        s3_bucket (str): S3 bucket to store the file
        s3_object_name (str): S3 object name to store the file

    Returns:
        models.DeployTarget: The entry created
    """
    statement = select(models.DeployTarget).filter_by(robot_id=robot_id, deploy_path=deploy_path)
    db_deploy_target = db.scalars(statement).first()
    if db_deploy_target:
        db_deploy_target.s3_bucket = s3_bucket
        db_deploy_target.s3_object_name = s3_object_name
    else:
        db_deploy_target = models.DeployTarget(
            robot_id=robot_id,
            deploy_path=deploy_path,
            s3_bucket=s3_bucket,
            s3_object_name=s3_object_name
        )
        db.add(db_deploy_target)
    db.commit()
    return db_deploy_target

def get_deploy_target_by_robot_id(db: Session, robot_id: str):
    statement = select(models.DeployTarget).filter_by(robot_id=robot_id)
    return db.scalars(statement).all()

def get_jobs(db: Session, robot_id: str, limit: Optional[int] = None):
    """Get jobs for a robot

    Args:
        db (Session): A database session
        robot_id (str): Robot id
        limit (Optional[int]): The number of jobs to return
    """
    statement = select(models.DeployJob).filter_by(robot_id=robot_id)
    statement = statement.order_by(models.DeployJob.timestamp.desc())
    if limit is not None and limit > 0:
        statement = statement.limit(limit)
    return db.scalars(statement).all()

def get_running_jobs(db: Session, robot_id: str):
    """Get running jobs for a robot

    Args:
        db (Session): A database session
        robot_id (str): Robot id
    """
    statement = select(models.DeployJob).filter_by(robot_id=robot_id)
    statement = select(models.DeployJob).where(
        models.DeployJob.status!=models.JobStatus.COMPLETED,
        models.DeployJob.status!=models.JobStatus.FAILED)
    statement = statement.order_by(models.DeployJob.timestamp.asc())
    return db.scalars(statement).all()

def update_job_status(db: Session, job_id: str, status: models.JobStatus,
                      error_msg: Optional[str] = None):
    """Update the status of a job

    Args:
        db (Session): A database session
        job_id (str): Unique job id
        status (models.JobStatus): New status
        error_msg (Optional[str]): Error message for FAILED jobs
    """
    statement = select(models.DeployJob).filter_by(job_id=job_id)
    job = db.scalars(statement).one()
    job.status = status
    if error_msg:
        job.error_msg = error_msg
    db.commit()

def create_job(db: Session, job_id: str, robot_id: str, deploy_path: str, deploy_msg: str):
    job = models.DeployJob(job_id=job_id, status=models.JobStatus.PENDING,
                           robot_id=robot_id, deploy_path=deploy_path, deploy_msg=deploy_msg,
                           timestamp=datetime.now().astimezone())
    db.add(job)
    db.commit()

def get_job_by_id(db: Session, job_id: str):
    """Get job by job_id

    Args:
        db (Session): A database session
          job_id (str): Unique job id
    Returns:
        DeployJob: The job wanted
    """
    statement = select(models.DeployJob).filter_by(job_id=job_id)
    return db.scalars(statement).one()
