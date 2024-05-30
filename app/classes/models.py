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

import datetime
import enum
from typing import Dict

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    type_annotation_map = {
        datetime.datetime: TIMESTAMP(timezone=True),
        Dict[str, str]: JSONB
    }

class File(Base):
    """The mapped class refers to 'files' table """
    __tablename__ = 'files'

    s3_bucket: Mapped[str] = mapped_column(primary_key=True)
    s3_object_name: Mapped[str] = mapped_column(primary_key=True)
    file_name: Mapped[str]
    timestamp: Mapped[datetime.datetime]
    robot_id: Mapped[str]
    robot_type: Mapped[str]
    robot_version: Mapped[str]
    deploy_path: Mapped[str]
    sha256: Mapped[str]
    file_metadata: Mapped[Dict[str, str]]
    valid: Mapped[bool]
    version: Mapped[str] = mapped_column(default='v1')
    deploy_targets: Mapped[list['DeployTarget']] = relationship(cascade='all, delete')

class DeployTarget(Base):
    """The mapped class refers to 'deploy_target' table """
    __tablename__ = 'deploy_target'

    robot_id: Mapped[str] = mapped_column(primary_key=True)
    deploy_path: Mapped[str] = mapped_column(primary_key=True)
    s3_bucket: Mapped[str] = mapped_column()
    s3_object_name: Mapped[str] = mapped_column()
    __table_args__ = (
        ForeignKeyConstraint(
            ['s3_bucket', 's3_object_name'], ['files.s3_bucket', 'files.s3_object_name']
        ),
    )
    version: Mapped[str] = mapped_column(default='v1')

class JobStatus(enum.Enum):
    PENDING = 'PENDING'
    RECEIVED = 'RECEIVED'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class DeployJob(Base):
    """The deploy job"""
    __tablename__ = 'deploy_jobs'

    job_id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[JobStatus]
    robot_id: Mapped[str]
    deploy_path: Mapped[str]
    deploy_msg: Mapped[str]
    timestamp: Mapped[datetime.datetime]
    error_msg: Mapped[str] = mapped_column(nullable=True)
