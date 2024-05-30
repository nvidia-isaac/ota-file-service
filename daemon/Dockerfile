# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
# Dockerfile to build a container to run daemon. Will remove this after adding bazel rules
# to build daemon container.
From ubuntu:20.04

RUN apt update && apt install -y ca-certificates curl software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install python3.11 python3.11-dev -y
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
RUN python3.11 -m pip install --upgrade pip
RUN unlink /usr/bin/python3
RUN ln -s /usr/bin/python3.11 /usr/bin/python3
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN pip install fastapi uvicorn requests pydantic boto3 paho-mqtt PyYAML
COPY . /src/
ENV  PYTHONPATH=/src
ENTRYPOINT ["python", "/src/main.py"]
