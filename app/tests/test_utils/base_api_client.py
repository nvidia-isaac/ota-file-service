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

import requests

from requests.exceptions import HTTPError


class BaseAPIClient:
    """Base class for Isaac API clients with logging support"""

    _base_url: str = ""
    _config: dict = {}

    def __init__(self, config: dict):
        self._config = config
        self._base_url = config["base_url"]

    @property
    def base_url(self):
        return self._base_url

    def make_request_with_logs(self, method_name, endpoint, error_msg, success_msg, **kwargs):
        try:
            method = getattr(requests, method_name)
            response = method(self._base_url + endpoint, **kwargs)
            response.raise_for_status()
        except (HTTPError) as exc:
            logging.error("endpoint %s HTTPError failure", endpoint)
            if response:
                logging.error("%s, %s", error_msg, response.text)
            else:
                logging.error("%s, %s", error_msg, exc)
            raise

        logging.info(success_msg)
        logging.debug(response.json())
        return response.json()
