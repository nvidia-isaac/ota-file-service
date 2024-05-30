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

import multiprocessing
import os
import signal
import time
from typing import Any

from app.classes.config import OTAFileServiceConfig
from app.tests import test_utils

# The TCP port for the api server to listen on
API_PORT = 9005
# The TCP port for the MQTT broker to listen on
MQTT_PORT_TCP = 1883
# The WEBSOCKET port for the MQTT broker to listen on
MQTT_PORT_WEBSOCKET = 9001
# The transport mechanism("websockets", "tcp") for MQTT
MQTT_TRANSPORT = "tcp"
# The path for the websocket if "mqtt_transport" is "websockets""
MQTT_WS_PATH = "/mqtt"
# The port for the MQTT broker to listen on
MQTT_PORT = MQTT_PORT_TCP if MQTT_TRANSPORT == "tcp" else MQTT_PORT_WEBSOCKET
# Starting PostgreSQL Db on this port
POSTGRES_PORT = 5432
DAEMON_PORT = 9000

SERVICE_CONFIG_DIR = os.environ.get("WORKSPACE", "")+"/app/config"
DAEMON_CONFIG_DIR = os.environ.get("WORKSPACE", "")+"/daemon/config"

class TestContext:
    """OTA File Service text context"""
    crashed_process = False

    def __init__(self, name="test context",
                 config_file="path/to/config_file.yaml"):
        self._name = name
        self.processes = []
        if TestContext.crashed_process:
            raise ValueError("Can't run test due to previous failure")
        self.config = OTAFileServiceConfig("app" + config_file)

        # Register signal handler
        signal.signal(signal.SIGUSR1, self.catch_signal)

        # Start the Mosquitto broker
        self._mqtt_process, self._mqtt_address = self.run_docker(
            "//app/tests/test_utils:mosquitto-img-bundle",
            args=[str(MQTT_PORT_TCP), str(MQTT_PORT_WEBSOCKET)],
            docker_args=[])

        test_utils.wait_for_port(
            host=self._mqtt_address, port=MQTT_PORT, timeout=120)
        self.processes.append(self._mqtt_process)

        # Start postgreSQL db
        self._postgres_database, postgres_address = \
            self.run_docker(image="//app/tests/test_utils:postgres-database-img-bundle",
                            docker_args=["--network", "host",
                                         "-p", f"{POSTGRES_PORT}:{POSTGRES_PORT}",
                                         "-e", "POSTGRES_PASSWORD=postgres",
                                         "-e", "POSTGRES_DB=file",
                                         "-e", "POSTGRES_INITDB_ARGS=\
                    --auth-host=scram-sha-256 --auth-local=scram-sha-256"],
                            args=["postgres"])
        test_utils.wait_for_port(
            host=postgres_address, port=POSTGRES_PORT, timeout=120)
        self.processes.append(self._postgres_database)

        # Start OTA File Service
        self._ota_service_process, self._ota_service_address = self.run_docker(
            "//app:ota-file-service-img-bundle",
            docker_args=["--network", "host", "-v",
                         f"{SERVICE_CONFIG_DIR}:/config",
                         "-e", f"MQTT_HOST={self._mqtt_address}",
                         "-e", f"MQTT_PORT={MQTT_PORT}",
                         "-e", f"S3_ID={os.environ.get('S3_ID', '')}",
                         "-e", f"S3_ACCESS_KEY={os.environ.get('S3_ACCESS_KEY', '')}",
                         "-e", f"S3_ENDPOINT_URL={os.environ.get('S3_ENDPOINT_URL', '')}"],
            args=["--config", config_file])
        test_utils.wait_for_port(
            host=self._ota_service_address, port=API_PORT, timeout=120)
        self.processes.append(self._ota_service_process)

        self.ota_service_client = test_utils.BaseAPIClient(
            {"base_url": f"http://127.0.0.1:{API_PORT}"})

        # Start daemon
        self._daemon_process, self._daemon_address = self.run_docker(
            "//daemon:ota-file-daemon-img-bundle",
            docker_args=["--network", "host", "-v",
                         f"{DAEMON_CONFIG_DIR}:/config",
                         "-e", f"MQTT_HOST={self._mqtt_address}",
                         "-e", f"MQTT_PORT={MQTT_PORT}",
                         "-e", f"S3_ID={os.environ.get('S3_ID', '')}",
                         "-e", f"S3_ACCESS_KEY={os.environ.get('S3_ACCESS_KEY', '')}",
                         "-e", f"S3_ENDPOINT_URL={os.environ.get('S3_ENDPOINT_URL', '')}"],
            args=["--config", config_file])
        test_utils.wait_for_port(
            host=self._ota_service_address, port=DAEMON_PORT, timeout=120)
        self.processes.append(self._daemon_process)

    def run_docker(self, image: str, args: list[str], docker_args: list[str],
                   delay: int = 0) -> tuple[multiprocessing.Process, str]:
        pid = os.getpid()
        queue: Any = multiprocessing.Queue()

        def wrapper_process():
            docker_process, address = \
                test_utils.run_docker_target(
                    image, args=args, docker_args=docker_args, delay=delay)
            queue.put(address)
            docker_process.wait()
            os.kill(pid, signal.SIGUSR1)

        process = multiprocessing.Process(target=wrapper_process, daemon=True)
        process.start()
        return process, queue.get()

    def catch_signal(self, s, f):
        TestContext.crashed_process = True
        raise OSError("Child process crashed!")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        for i in reversed(range(len(self.processes))):
            if self.processes[i] is not None:
                self.processes[i].terminate()
                self.processes[i].join()
        time.sleep(5)
        print(f"Context closed: {self._name}", flush=True)
