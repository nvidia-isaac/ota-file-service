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

from pydantic import Field, field_validator

from utils.config import S3Config, MQTTConfig

class OTAFileDaemonConfig(S3Config, MQTTConfig):
    robot_id: str = Field(default='robot_a', env='ROBOT_ID')
    cloud_service_url: str = Field(env='CLOUD_SERVICE_URL')
    @field_validator('robot_id')
    @classmethod
    def robot_id_is_nonempty(cls, v: str) -> str:
        if not v:
            raise ValueError('Robot id is emptry.')
        return v
