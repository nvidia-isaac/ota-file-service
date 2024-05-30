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
from collections import defaultdict
import json
import logging
import queue
import os
import threading
import time
from typing import Optional

import botocore
import boto3
import paho.mqtt.client as mqtt_client
from pydantic import BaseModel, ValidationError
import requests
import yaml

from daemon.classes import config
from daemon.classes.schemas import FileInfo

# How long to wait in seconds before trying to connect to the mqtt broker
MQTT_RECONNECT_PERIOD = 0.5
REPORT_STATE_PERIOD = 0.5
UPLOAD_RETRY_PERIOD = 10
UPLOAD_TIME_OUT = 60
HEALTH_TIMEOUT = 3

class DeployJob(BaseModel):
    job_id: str
    s3_bucket: str
    s3_object_name: str
    deploy_path: str

class JobState(BaseModel):
    status: str = 'RECEIVED'
    error_msg: Optional[str] = None

class OTAFileDaemon:
    '''A daemon to process deploy messages'''
    _instance = None

    def __init__(self, config_file: str):
        with open(config_file, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
        daemon_config = config.OTAFileDaemonConfig.load(yaml_data)
        self._logger = logging.getLogger('OTA File Service')
        self._s3_client = boto3.client(service_name='s3',
                                       region_name=daemon_config.region_name,
                                       endpoint_url=daemon_config.endpoint_url,
                                       aws_access_key_id=daemon_config.aws_access_key_id,
                                       aws_secret_access_key=daemon_config.aws_secret_access_key)
        self.cloud_service_url = daemon_config.cloud_service_url
        self._mqtt_deploy_topic = daemon_config.get_deploy_topic(daemon_config.robot_id)
        self._mqtt_state_topic = daemon_config.get_state_topic(daemon_config.robot_id)
        self._mqtt_ack_topic = daemon_config.get_ack_topic(daemon_config.robot_id)
        self._mqtt_client = self._connect_to_mqtt(daemon_config.host,
                                                  daemon_config.port,
                                                  daemon_config.transport,
                                                  daemon_config.ws_path)

        # The queue to keep deployment jobs.
        self._deploy_queue: queue.Queue[DeployJob] = queue.Queue()
         # The queue to keep upload jobs.
        self._upload_queue: queue.Queue[list[FileInfo]] = queue.Queue()
        # A dict to keep job states
        self._jobs: defaultdict[str, JobState] = defaultdict(JobState)
        # The thread to process deployment jobs
        self._deploy_thread = threading.Thread(target=self._deploy_files, daemon=True)
        # The thread to process upload jobs
        self._upload_thread = threading.Thread(target=self._upload_files, daemon=True)
        OTAFileDaemon._instance = self

    @staticmethod
    def get_instance():
        if not OTAFileDaemon._instance:
            raise ValueError('OTAFileDaemon has not been created!')
        return OTAFileDaemon._instance

    def info(self, message: str):
        self._logger.info('[OTA File Daemon] | INFO: %s', message)

    def debug(self, message: str):
        self._logger.debug('[OTA File Daemon] | DEBUG: %s', message)

    def warning(self, message: str):
        self._logger.warning('[OTA File Daemon] | WARNING: %s', message)

    def error(self, message: str):
        self._logger.warning('[OTA File Daemon] | ERROR: %s', message)

    def _connect_to_mqtt(self, host: str, port: int, transport: str, ws_path: Optional[str]) -> \
            mqtt_client.Client:
        client = mqtt_client.Client(transport=transport)
        if transport == 'websockets' and ws_path is not None:
            client.ws_set_options(path=ws_path)
        client.on_connect = self._mqtt_on_connect
        client.on_message = self._mqtt_on_message
        client.on_disconnect = self._mqtt_on_disconnect
        connected = False
        while not connected:
            try:
                client.connect(host, port)
                connected = True
            except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
                self.warning(f'Failed to connect to mqtt broker: {e}, retrying in '
                             f'{MQTT_RECONNECT_PERIOD}s')
                time.sleep(MQTT_RECONNECT_PERIOD)
        return client

    def _mqtt_on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.warning(f'MQTT Unexpected disconnection: {rc}.')

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        self.info('MQTT Connected.')
        client.subscribe(self._mqtt_deploy_topic)
        client.subscribe(self._mqtt_ack_topic)

    def _mqtt_on_message(self, client, userdata, msg):
        self.info(f'Received message: {msg.payload}')
        # Process deploy message
        if msg.topic == self._mqtt_deploy_topic:
            job_info = json.loads(msg.payload)
            try:
                job = DeployJob(**job_info)
            except ValidationError as e:
                self.error(f'Invalid job message: {e}')
            if job.job_id in self._jobs:
                return
            self._jobs[job.job_id].status = 'RECEIVED'
            self._deploy_queue.put(job)
        # Process ack message
        elif msg.topic == self._mqtt_ack_topic:
            job_id = str(msg.payload.decode())
            if job_id in self._jobs:
              del self._jobs[job_id]

    def _deploy_files(self):
        '''Get a job from the queue and deploy the file.'''
        while True:
            job = self._deploy_queue.get()
            filepath = job.deploy_path
            try:
                folder = os.path.dirname(filepath)
                if not os.path.exists(folder):
                    os.makedirs(folder)
                self._s3_client.download_file(job.s3_bucket,
                                              job.s3_object_name,
                                              filepath)
                self.info(f'File deployed at {filepath}')
                self._jobs[job.job_id].status = 'COMPLETED'
            except (OSError, botocore.exceptions.ClientError) as e:
                self._jobs[job.job_id].status = 'FAILED'
                self._jobs[job.job_id].error_msg = str(e)
                self.error(str(e))

    def _upload_files(self):
        '''Get a job from the queue and upload the file'''
        while True:
            job = self._upload_queue.get()
            file_list: dict = {'file_list': []}
            files = []
            for file_info in job:
                try:
                    files.append(('files', open(file_info.local_path, 'rb')))
                except OSError as e:
                    self.error(str(e))
                    continue
                file_create_body = {
                    's3_bucket': file_info.s3_bucket,
                    's3_bucket_name': file_info.s3_bucket,
                    'robot_id': file_info.robot_id,
                    'deploy_path': file_info.deploy_path,
                    'file_metadata': file_info.file_metadata
                }
                file_list['file_list'].append(file_create_body)

            # If the cloud service is not available, retry UPLOAD_RETRY_PERIOD seconds later.
            while True:
                try:
                    response = requests.get(f'{self.cloud_service_url}/health',
                                            timeout=HEALTH_TIMEOUT)
                    if response.status_code != 200:
                        raise requests.exceptions.RequestException(response=response)
                except requests.exceptions.RequestException as e:
                    self.warning(f'Cloud service is not available: {str(e)}')
                    time.sleep(UPLOAD_RETRY_PERIOD)
                else:
                    break

            file_list_json = json.dumps(file_list)
            try:
                response = requests.post(f'{self.cloud_service_url}/file/upload',
                                         data={'file_info_list': file_list_json},
                                         files=files,
                                         timeout=UPLOAD_TIME_OUT)
            except requests.exceptions.RequestException as e:
                self.warning(f'File upload failed: {str(e)}')
            else:
                self.info(str(response))

    def add_upload_job(self, file_info_list: list[FileInfo]):
        self._upload_queue.put(file_info_list)

    def _report_state(self):
        jobs_dict = {key: value.model_dump() for key, value in self._jobs.items()}
        self._mqtt_client.publish(self._mqtt_state_topic, json.dumps(jobs_dict))

    def run(self):
        self._deploy_thread.start()
        self._upload_thread.start()
        self._mqtt_client.loop_start()
        while True:
            time.sleep(REPORT_STATE_PERIOD)
            self._report_state()
