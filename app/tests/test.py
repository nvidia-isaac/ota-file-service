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
import tempfile
import time
import unittest
from app.tests import test_context


DEPLOY_TIMEOUT=10
COMPLETED_STATUS = "COMPLETED"

class TestOTAFileService(unittest.TestCase):
    """Tests for OTA File Service"""
    def test_health(self):
        with test_context.TestContext(config_file="/config/defaults.yaml") as ctx:
            ctx.ota_service_client.make_request_with_logs(
                "get", "/api/v1/health", "OTA File Service: Error",
                "OTA File Service: Running"
            )

    def test_apis(self):
        with test_context.TestContext(config_file="/config/defaults.yaml") as ctx:
            temp_file = tempfile.NamedTemporaryFile(mode="w")
            temp_file.write("test")

            # Test POST /file/upload
            files = [("files", open(temp_file.name, "rb"))]
            file_info_list = {"file_list": [{"s3_bucket": "files"}]}
            response = ctx.ota_service_client.make_request_with_logs(
                "post", "/api/v1/file/upload", "OTA File Service: Error",
                "OTA File Service: File Uploaded", files=files,
                data={"file_info_list": json.dumps(file_info_list)}
            )
            s3_object_name = response[0]["s3_object_name"]
            temp_file.close()

            # Test POST /file/deploy_from_s3
            params = {
                "s3_bucket": "files",
                "s3_object_name": s3_object_name,
                "robot_id": "robot_a",
                "deploy_path": "/tmp/test.txt"
            }
            response = ctx.ota_service_client.make_request_with_logs(
                "post", "/api/v1/file/deploy_from_s3", "OTA File Service: Error",
                "OTA File Service: Deploy Job Sent", params=params
            )
            job_id = response["job_id"]

            # Test GET /job_state/{job_id}
            end_time = time.time() + DEPLOY_TIMEOUT
            while time.time() < end_time:
                response = ctx.ota_service_client.make_request_with_logs(
                    "get", f"/api/v1/job_state/{job_id}", "OTA File Service: Error",
                    "OTA File Service: Deploy Job State"
                )
                if response["status"] == COMPLETED_STATUS:
                    break
                time.sleep(1)
            self.assertEqual(response["status"], COMPLETED_STATUS)

            # Test DELETE /file/delete
            params = {"s3_bucket": "files", "s3_object_name": s3_object_name}
            response = ctx.ota_service_client.make_request_with_logs(
                "delete", "/api/v1/file/delete", "OTA File Service: Error",
                "OTA File Service: File Deleted", params=params
            )


if __name__ == "__main__":
    unittest.main()
