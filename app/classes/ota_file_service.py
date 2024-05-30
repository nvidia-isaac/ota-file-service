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

import json
import logging
import re
import socket
import time
from typing import Optional, BinaryIO
import uuid

import boto3
import paho.mqtt.client as mqtt_client
from sqlalchemy import exc

from app.classes import models
from app.classes.config import OTAFileServiceConfig
from app.classes.database import SessionLocal
from app.classes.utils import OTAFileServiceError
from app.classes import crud

# How long to wait in seconds before trying to reconnect to the mqtt broker
MQTT_RECONNECT_PERIOD = 0.5

class OTAFileService:
    """Class to manage s3 and mqtt client """
    _instance = None

    @staticmethod
    def get_instance():
        """ Static access method. """
        if not OTAFileService._instance:
            raise OTAFileServiceError('OTA File Service has not been created!')
        return OTAFileService._instance

    def __init__(self, config: OTAFileServiceConfig):
        self._s3_client = boto3.client(
            service_name='s3',
            region_name=config.s3_config.region_name,
            endpoint_url=config.s3_config.endpoint_url,
            aws_access_key_id=config.s3_config.aws_access_key_id,
            aws_secret_access_key=config.s3_config.aws_secret_access_key)
        self._mqtt_config = config.mqtt_config
        self._mqtt_client = self._connect_to_mqtt(host=config.mqtt_config.host,
                                                  port=config.mqtt_config.port,
                                                  transport=config.mqtt_config.transport,
                                                  ws_path=config.mqtt_config.ws_path)
        self._mqtt_client.loop_start()
        OTAFileService._instance = self

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        logging.warning('MQTT connected.')
        client.subscribe(self._mqtt_config.get_state_topic('+'))

    def _mqtt_on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.warning('MQTT Unexpected disconnection: %d.', rc)

    def _mqtt_on_message(self, client, userdata, msg):
        """Process deployment state message from the robot"""
        match = re.match(self._mqtt_config.get_state_topic('(.*)'), msg.topic)
        if match is None:
            logging.warning("Got message from unrecognized topic '%s'", msg.topic)
            return
        robot_id = match.groups()[0]
        with SessionLocal() as db:
            jobs = crud.get_running_jobs(db, robot_id)
        states = json.loads(msg.payload)
        # Resend the deploy message if the job state is not received
        for job in jobs:
            if job.job_id not in states:
                # Resend the job
                deploy_topic = self._mqtt_config.get_deploy_topic(robot_id)
                self._mqtt_client.publish(topic=deploy_topic, payload=job.deploy_msg)
        # Update job status
        for job_id, status in states.items():
            with SessionLocal() as db:
                try:
                    crud.update_job_status(db, job_id,
                                           getattr(models.JobStatus, status['status']),
                                           status.get('error_msg', None))
                except exc.NoResultFound:
                    logging.warning("Received state of unknown job_id '%s'", job_id)

            if status['status'] in ('COMPLETED', 'FAILED'):
                ack_topic = self._mqtt_config.get_ack_topic(robot_id)
                self._mqtt_client.publish(topic=ack_topic,
                                          payload=f'{job_id}')
                if status['status'] == 'COMPLETED':
                    # Update deploy_target table when the file is deployed.
                    with SessionLocal() as db:
                        db_job = crud.get_job_by_id(db, job_id)
                        deploy_info = json.loads(db_job.deploy_msg)
                        crud.create_or_update_deploy_target(db, db_job.robot_id,
                                                            db_job.deploy_path,
                                                            deploy_info['s3_bucket'],
                                                            deploy_info['s3_object_name'])


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
            except (ConnectionRefusedError, ConnectionResetError):
                logging.error('Failed to connect to mqtt broker, retrying in %fs',
                              MQTT_RECONNECT_PERIOD)
                time.sleep(MQTT_RECONNECT_PERIOD)
            except socket.gaierror:
                logging.error('Could not resolve mqtt hostname %s, retrying in %fs',
                              host, MQTT_RECONNECT_PERIOD)
                time.sleep(MQTT_RECONNECT_PERIOD)
        return client

    def upload_file(self, file: BinaryIO, bucket: str, object_name: str):
        self._s3_client.upload_fileobj(file, bucket, object_name)

    def download_file(self, s3_bucket: str, s3_object_name: str, path: str):
        self._s3_client.download_file(s3_bucket, s3_object_name, path)

    def get_s3_object(self, s3_bucket: str, s3_object_name: str):
        return self._s3_client.get_object(Bucket=s3_bucket, Key=s3_object_name)['Body'].read()

    def create_presigned_url(self, s3_bucket: str, s3_object_name):
        return self._s3_client.generate_presigned_url('get_object',
                                                      Params={'Bucket': s3_bucket,
                                                              'Key': s3_object_name},
                                                      ExpiresIn=3600)


    def deploy_file(self, s3_bucket: str, s3_object_name: str, robot_id: str, deploy_path: str):
        job_id = str(uuid.uuid4())
        deploy_info = {
            'job_id': job_id,
            's3_bucket': s3_bucket,
            's3_object_name': s3_object_name,
            'deploy_path': deploy_path
        }
        deploy_msg = json.dumps(deploy_info)
        with SessionLocal() as db:
            crud.create_job(db, job_id, robot_id, deploy_path, deploy_msg)
        self._mqtt_client.publish(topic=f'ota/{robot_id}/deploy',
                                  payload=deploy_msg)
        return job_id

    def delete_file(self, s3_bucket: str, s3_object_name: str):
        self._s3_client.delete_object(Bucket=s3_bucket, Key=s3_object_name)
