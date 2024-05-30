#####################################################################################
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
#####################################################################################
# Full OTA file service build arm64 environment for production containers.

FROM ubuntu@sha256:080169816683e6f063d3903434565624287828ecfd06bd2f813b30325e8b1eca

# disable terminal interaction for apt
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io curl git python3-pip ssh \
    wget apt-utils aha rsync xz-utils lsb-release software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
ADD scripts/install_dependencies.sh scripts/
RUN chmod +x scripts/install_dependencies.sh
RUN apt update && scripts/install_dependencies.sh && \
    rm -rf /var/lib/apt/lists/* && rm -rf scripts

CMD ["/bin/bash"]
