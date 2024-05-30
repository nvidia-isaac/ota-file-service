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
from enum import Enum
from typing import Dict, Optional

import json
from pydantic import BaseModel, model_validator

DEFAULT_BUCKET = 'files'

class FileBase(BaseModel):
    s3_bucket: str = DEFAULT_BUCKET
    s3_object_name: Optional[str] = ''
    robot_id: Optional[str] = ''
    deploy_path: Optional[str] = ''

class FileCreate(FileBase):
    """Attributes while creating a file"""
    robot_type: Optional[str] = ''
    robot_version: Optional[str] = ''
    file_metadata: Optional[Dict[str, str]] = {}

class FormBody(BaseModel):
    """A class with a validator to get construct object from Json string.
    With this feature, a FastAPI endpoint can accept UploadFile and Json
    object at the same time."""
    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

class FileCreateList(FormBody):
    """A list of file upload info"""
    file_list: list[FileCreate]

class FileDeploy(FileCreate):
    deploy_path: str
    robot_id: str

class FileDeployList(FormBody):
    """A list of file deploy info"""
    file_list: list[FileDeploy]

class TaskState(str, Enum):
    """State of file upload or deploy"""
    UPLOADED = 'UPLOADED'
    PENDING = 'PENDING'
    FAILED = 'FAILED'

class FileUploadResponse(FileBase):
    """Response model for upload api"""
    filename: str
    state: TaskState = TaskState.UPLOADED
    error_msg: Optional[str] = None

class FileDeployResponse(FileUploadResponse):
    """Response model for deploy api"""
    job_id: str = ''
    state: TaskState = TaskState.PENDING

class FileUpdate(FileCreate, FormBody):
    """Attributes to update a file"""
    s3_object_name: str
