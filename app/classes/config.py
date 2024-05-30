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

import logging
import yaml

from app.classes.utils import OTAFileServiceError
from utils.config import S3Config, PostgresConfig, MQTTConfig

class OTAFileServiceConfig:
    """OTA File Service Config """
    _instance = None

    @staticmethod
    def get_instance():
        """ Static access method. """
        if not OTAFileServiceConfig._instance:
            raise OTAFileServiceError('OTA File Service has not been created!')
        return OTAFileServiceConfig._instance

    def __init__(self, config_file: str):
        """ Loads the config file """
        self._config_file = config_file
        logging.info('Reading configuration from %s...', self._config_file)
        logging.info('Config file: %s', config_file)
        with open(self._config_file, 'r', encoding='utf-8') as configyaml:
            yaml_config = yaml.safe_load(configyaml)
            self._config = yaml_config
        self.postgres_config = PostgresConfig.load(self._config['postgres'])
        self.s3_config = S3Config.load(self._config['s3'])
        self.mqtt_config = MQTTConfig.load(self._config['mqtt'])
        OTAFileServiceConfig._instance = self
