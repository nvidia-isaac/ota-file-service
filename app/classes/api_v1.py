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
import hashlib
import json
import os
from typing import Optional
import uuid

import botocore
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi import status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session
from sqlalchemy import exc

from app.classes import crud
from app.classes.database import SessionLocal
from app.classes.ota_file_service import OTAFileService
from app.classes import models, schemas

app = FastAPI(title='OTA File Service API')

def get_db():
    """Generate an independent database session for each Fastapi request.

    Yields:
        SessionLocal: A database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def upload_a_file(file: UploadFile,
                  file_info: schemas.FileCreate,
                  timestamp: datetime,
                  db: Session,
                  update: bool = False):
    """Upload a file to s3 database. Common logic for upload and deploy api"""
    user_provided_object_name = file_info.s3_object_name
    if not file_info.s3_object_name:
        if file.filename:
            file_info.s3_object_name = file.filename + '_' + str(uuid.uuid4())
        else:
            file.filename = str(uuid.uuid4())
            file_info.s3_object_name = file.filename
    response = schemas.FileUploadResponse(filename=file.filename, # type: ignore
                                          **file_info.model_dump())

    # Check if a file is already uploaded to the same bucket and object_name
    db_file = crud.get_files(db, s3_bucket=file_info.s3_bucket,
                             s3_object_name=file_info.s3_object_name)
    if db_file and not update:
        response.state = schemas.TaskState.FAILED
        response.error_msg=(f'Object {file_info.s3_object_name} in '
                            f'bucket {file_info.s3_bucket} already exists.')
        return response
    # Calculate sha256
    sha256 = hashlib.sha256()
    while True:
        data = await file.read(65536)  # Read 64KB at a time
        if not data:
            break
        sha256.update(data)
    sha256_value = sha256.hexdigest()
    file.file.seek(0)
    # Check if file with same sha256 and metadata is already uploaded.
    get_files_params = {
        's3_bucket': file_info.s3_bucket,
        'sha256': sha256_value,
        'robot_id': file_info.robot_id,
        'deploy_path': file_info.deploy_path,
        'robot_type': file_info.robot_type,
        'robot_version': file_info.robot_version,
        'file_metadata': json.dumps(file_info.file_metadata)
    }
    if user_provided_object_name:
        get_files_params['s3_object_name'] = user_provided_object_name
    db_file = crud.get_files(db, **get_files_params)
    if db_file:
        file_info.s3_object_name = db_file[0].s3_object_name
        response.s3_object_name = db_file[0].s3_object_name
        return response

    try:
        OTAFileService.get_instance().upload_file(file.file,
                                                  file_info.s3_bucket,
                                                  file_info.s3_object_name)
        if update:
            db_files = crud.get_files(db, s3_bucket=file_info.s3_bucket,
                                      s3_object_name=file_info.s3_object_name)
            return crud.update_file(
                db, db_files[0], file_info, timestamp, file.filename, sha256_value)
        else:
            crud.create_file(db, file_info, file.filename, sha256_value, timestamp)
    except (botocore.exceptions.ClientError, exc.SQLAlchemyError) as e:
        response.state = schemas.TaskState.FAILED
        response.error_msg = str(e)
    return response


@app.get('/file/list')
def file_list(s3_bucket: Optional[str] = None,
              s3_object_name: Optional[str] = None,
              robot_id: Optional[str] = None,
              robot_type: Optional[str] = None,
              deploy_path: Optional[str] = None,
              file_metadata: Optional[str] = None,
              db: Session = Depends(get_db)):
    """List file info according to search criteria.

    Args:
        s3_bucket (Optional[str], optional): S3 bucket that stores the file. Defaults to None.
        s3_object_name (Optional[str], optional): S3 object name. Defaults to None.
        robot_id (Optional[str], optional): Robot id. Defaults to None.
        robot_type (Optional[str], optional): Robot type. Defaults to None.
        deploy_path (Optional[str], optional): Path to deloy. Defaults to None.
        file_metadata (Optional[str], optional): File metadata in Json format. Defaults to None.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        _type_: _description_
    """
    args = locals()
    criteria = {}
    conditions = []
    for arg_name, value in args.items():
        if value is None:
            continue
        if arg_name == 'db':
            continue
        if arg_name == 'file_metadata':
            metadata_json = json.loads(value)
            for metadata_key, metadata_value in metadata_json.items():
                conditions.append(models.File.file_metadata[metadata_key].astext == metadata_value)
        else:
            criteria[arg_name] = value

    db_files = crud.get_files(db, *conditions, **criteria)
    for db_file in db_files:
        db_file.timestamp = db_file.timestamp.astimezone()
    return db_files

@app.post('/file/upload')
async def file_upload(
    file_info_list: schemas.FileCreateList,
    files: list[UploadFile],
    db: Session = Depends(get_db)):
    """API to upload files

    Args:
        files (schemas.FileCreateList): Files to upload
        file_info_list (list[schemas.FileCreate]): Info required to upload a file
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        list[FileUploadResponse]: State of files uploaded.
    """
    if len(files) != len(file_info_list.file_list):
        raise HTTPException(status_code=400,
                            detail='Number of files and file info do not match.')
    timestamp = datetime.now().astimezone()
    responses: list[schemas.FileUploadResponse] = []

    for file, file_info in zip(files, file_info_list.file_list):
        response = await upload_a_file(file, file_info, timestamp, db)
        responses.append(response)

    # If any upload failed, raise an HTTPException with the details.
    if any(response.state == schemas.TaskState.FAILED for response in responses):
        raise HTTPException(
            status_code=400,
            detail=[response.model_dump(exclude_unset=True) for response in responses])
    return responses


@app.patch('/file/update')
async def file_update(
    file_info: schemas.FileUpdate,
    file: list[UploadFile],
    db: Session = Depends(get_db)):
    """API to update a file

    Args:
        file_info (schemas.FileUpdate): Updated file metadata. S3 info is required.
        file (list[UploadFile]): A new file to replace if needed.
        db (Session, optional): Database section. Defaults to Depends(get_db).
    """
    db_files = crud.get_files(db, s3_bucket=file_info.s3_bucket,
                             s3_object_name=file_info.s3_object_name)
    if not db_files:
        raise HTTPException(
            status_code=400,
            detail='The file does not exist.')
    db_file = db_files[0]
    timestamp = datetime.now().astimezone()
    if file:
        return await upload_a_file(file[0], file_info, datetime.now().astimezone(), db, True)
    else:
        return crud.update_file(db, db_file, file_info, timestamp)

@app.post('/file/deploy')
async def file_deploy(file_info_list: schemas.FileDeployList,
                files: list[UploadFile],
                db: Session = Depends(get_db)):
    """API to deploy files. This API will upload the files deloy them to the robot.

    Args:
        files (list[UploadFile]): Files to deploy
        file_info (schemas.FileDeployList): Info required to upload files
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        list[schemas.FileDeployResponse]: States of file deployment.
    """
    timestamp = datetime.now().astimezone()
    responses: list[schemas.FileDeployResponse] = []

    for file, file_info in zip(files, file_info_list.file_list):
        upload_result = await upload_a_file(file, file_info, timestamp, db)
        deploy_result = schemas.FileDeployResponse(**upload_result.model_dump())
        if upload_result.state == schemas.TaskState.UPLOADED:
            if not file_info.robot_id:
                upload_result.state = schemas.TaskState.FAILED
                upload_result.error_msg = 'robot_id is required'
            else:
                try:
                    job_id = OTAFileService.get_instance().deploy_file(file_info.s3_bucket,
                                                                       file_info.s3_object_name,
                                                                       file_info.robot_id,
                                                                       file_info.deploy_path)
                    deploy_result.state = schemas.TaskState.PENDING
                    deploy_result.job_id = job_id
                except (botocore.exceptions.ClientError, exc.SQLAlchemyError) as e:
                    deploy_result.state = schemas.TaskState.FAILED
                    deploy_result.error_msg = str(e)
        responses.append(deploy_result)

    # If any deployment failed, raise an HTTPException with the details.
    if any(response.state == schemas.TaskState.FAILED for response in responses):
        raise HTTPException(
            status_code=400,
            detail=[response.model_dump(exclude_unset=True) for response in responses])
    return responses

@app.get('/file/download')
def file_download(s3_object_name: str, s3_bucket: str = 'files', db: Session = Depends(get_db)):
    """API to download a file

    Args:
        s3_object_name (str): S3 object name to download
        s3_bucket (str, optional): S3 bucket that stores the file. Defaults to 'files'.

    Returns:
        Response: File content
    """
    db_files = crud.get_files(db, s3_bucket=s3_bucket, s3_object_name=s3_object_name)
    if not db_files:
        raise HTTPException(status_code=404, detail='File not found')
    try:
        filename = db_files[0].file_name
        OTAFileService.get_instance().download_file(s3_bucket, s3_object_name, filename)
    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return  FileResponse(path=filename, filename=filename,
                         media_type='application/octet-stream',
                         background=BackgroundTask(lambda: os.remove(filename)))

@app.post('/file/deploy_from_s3')
def file_deploy_from_s3(robot_id: str,
                s3_bucket: str,
                s3_object_name: str,
                deploy_path: Optional[str] = None,
                db: Session = Depends(get_db)):
    """API to deploy a file from s3 to a robot. Will publish a mqtt message.

    Args:
        robot_id (str): Robot id
        s3_bucket (str): S3 bucket that stores the file
        s3_object_name (str): S3 object name to download
        deploy_path (str, optional): Absolute path to deploy the file. If not provided, use the
                                     deploy_path set when the file was uploaded. Raise an error if
                                     the deploy_path is not available.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        schemas.FileDeployResponse
    """
    db_files = crud.get_files(db, s3_bucket=s3_bucket, s3_object_name=s3_object_name)
    if not db_files:
        raise HTTPException(status_code=404, detail='File not found')
    db_file = db_files[0]
    if deploy_path:
        db_file.deploy_path = deploy_path
    if not db_file.deploy_path:
        raise HTTPException(status_code=404, detail='Parameter deploy_path is required.')
    response = schemas.FileDeployResponse(s3_bucket=db_file.s3_bucket,
                                          s3_object_name=db_file.s3_object_name,
                                          robot_id=robot_id,
                                          deploy_path=db_file.deploy_path,
                                          filename=db_file.file_name,
                                          error_msg=None,
                                          job_id='')
    try:
        job_id = OTAFileService.get_instance().deploy_file(db_file.s3_bucket,
                                                        db_file.s3_object_name,
                                                        robot_id,
                                                        db_file.deploy_path)
        response.job_id = job_id
    except (botocore.exceptions.ClientError, exc.SQLAlchemyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return response

@app.get('/deploy_state/{robot_id}', tags=['Debugging'])
def deploy_state(robot_id: str,
                 db: Session = Depends(get_db)):
    """Get the deployment state for a robot. The API returns a list of files deployed on the robot

    Args:
        robot_id (str): Unique robot id
        db (Session, optional): A database session. Defaults to Depends(get_db).
    """
    deployed = crud.get_deploy_target_by_robot_id(db, robot_id)
    return deployed

@app.get('/job_state/{job_id}')
def job_state(job_id: str,
                 db: Session = Depends(get_db)):
    """Get the state of the job.

    Args:
        job_id (str): Unique job id
        db (Session, optional): A database session. Defaults to Depends(get_db).
    """
    job = crud.get_job_by_id(db, job_id)
    return job

@app.put('/file/validate')
def file_validate(s3_bucket: str, s3_object_name: str, db: Session = Depends(get_db)):
    """API to set valid field to True.

    Args:
        s3_object_name (str): S3 object name to delete
        s3_bucket (str): S3 bucket that stores the file
        db (Session, optional): A database session. Defaults to Depends(get_db).
    """
    db_files = crud.get_files(db, s3_bucket=s3_bucket, s3_object_name=s3_object_name)
    if not db_files:
        raise HTTPException(status_code=404, detail='File not found')

    return crud.update_file(db, db_files[0], schemas.FileCreate(), valid=True)

@app.put('/file/invalidate')
def file_invalidate(s3_bucket: str, s3_object_name: str, db: Session = Depends(get_db)):
    """API to set valid field to False.

    Args:
        s3_object_name (str): S3 object name to delete
        s3_bucket (str): S3 bucket that stores the file
        db (Session, optional): A database session. Defaults to Depends(get_db).
    """
    db_files = crud.get_files(db, s3_bucket=s3_bucket, s3_object_name=s3_object_name)
    if not db_files:
        raise HTTPException(status_code=404, detail='File not found')

    return crud.update_file(db, db_files[0], schemas.FileCreate(), valid=False)

@app.delete('/file/delete')
def file_delete(s3_bucket: str, s3_object_name: str, db: Session = Depends(get_db)):
    """API to delete a file.

    Args:
        s3_object_name (str): S3 object name to delete
        s3_bucket (str): S3 bucket that stores the file
        db (Session, optional): A database session. Defaults to Depends(get_db).
    """
    db_files = crud.get_files(db, s3_bucket=s3_bucket, s3_object_name=s3_object_name)

    if not db_files:
        raise HTTPException(status_code=404, detail='File not found')

    crud.delete_file(db, s3_object_name, s3_bucket)
    OTAFileService.get_instance().delete_file(s3_bucket, s3_object_name)

@app.get('/health', status_code=status.HTTP_200_OK)
def ota_file_service_healthcheck():
    """ Check if service is healthy """
    return {'status': 'OTA File Service: Running'}

def get_ota_file_service_app():
    """ App itself """
    return app
