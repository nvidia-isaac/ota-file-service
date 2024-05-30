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
import os
from typing import Optional

from botocore.utils import is_valid_endpoint_url, is_valid_ipv6_endpoint_url # type: ignore
from pydantic import BaseModel, Field, field_validator, validator


class StaticConfig(BaseModel):
    @classmethod
    def load(cls, config_dict):
        for name, field in cls.model_fields.items():
            if field.json_schema_extra:
                env_name = field.json_schema_extra.get('env') # type: ignore
                if env_name is not None and env_name in os.environ:
                    config_dict[name] = os.environ[env_name]
        return cls(**config_dict)

class PostgresConfig(StaticConfig):
    """Postgres Config """
    host: str = Field(
        default='localhost',
        env='POSTGRES_HOST',
        description='The hostname of the postgres server to connect to.')
    port: int = Field(
        default=5432,
        env='POSTGRES_PORT',
        description='The port of the postgres server to connect to.')
    user: str = Field(
        default='postgres',
        env='POSTGRES_USER',
        description='The user of the postgres server.')
    password: str = Field(
        env='POSTGRES_PASSWORD',
        description='The password to connect to the postgres server.')
    db_name: str = Field(
        description='The database name.')

class S3Config(StaticConfig):
    """S3 Database Config """
    region_name: str = Field(
        default='us-east-1', description='S3 region.')
    endpoint_url: str = Field(env='S3_ENDPOINT_URL', description='S3 endpoint url.')
    aws_access_key_id: str = Field(env='S3_ID', description='AWS access key id')
    aws_secret_access_key: str = Field(env='S3_ACCESS_KEY', description='AWS secret access key')

    @field_validator('endpoint_url')
    @classmethod
    def endpoint_url_validator(cls, v: str) -> str:
        if not is_valid_endpoint_url(v) and not is_valid_ipv6_endpoint_url(v):
            raise ValueError('endpoint_url is invalid.')
        return v

class MQTTConfig(StaticConfig):
    """MQTT Config """
    host: str = Field(
        default='localhost',
        env='MQTT_HOST',
        description='The hostname of the MQTT broker.')
    port: int = Field(
        default=1883,
        env='MQTT_PORT',
        description='The port of the MQTT broker.')
    transport: str = 'tcp'
    ws_path: Optional[str] = Field(default=None, description='MQTT websocket path')
    topic_pattern: str = Field(
        default='ota/<robot_id>/<operation>',
        description='MQTT topic pattern. When publishing messages, "<robot_id>" will be replaced '
                    'by a robot_id, "<operation>" will be replaced by one of "deploy", "state", '
                    '"ack".')

    @validator('topic_pattern')
    def validate_robot_id_substring(cls, value):
        if '<robot_id>' not in value:
            raise ValueError('MQTT topic pattern must contain the substring "<robot_id>"')
        if '<operation>' not in value:
            raise ValueError('MQTT topic pattern must contain the substring "<operation>"')
        return value

    def get_deploy_topic(self, robot_id: str):
        robot_id_replaced = self.topic_pattern.replace('<robot_id>', robot_id)
        return robot_id_replaced.replace('<operation>', 'deploy')

    def get_state_topic(self, robot_id: str):
        robot_id_replaced = self.topic_pattern.replace('<robot_id>', robot_id)
        return robot_id_replaced.replace('<operation>', 'state')

    def get_ack_topic(self, robot_id: str):
        robot_id_replaced = self.topic_pattern.replace('<robot_id>', robot_id)
        return robot_id_replaced.replace('<operation>', 'ack')
