#!/bin/bash
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# SPDX-License-Identifier: Apache-2.0

set -e

# Detect the architecture
ARCH=$(uname -m)
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. >/dev/null 2>&1 && pwd )"
DOCKERFILE="${ROOT}/ci/ota_dev.dockerfile"

if [ ! -d "$HOME/.cache/bazel" ]; then
  # Folder does not exist, so create it
  mkdir "$HOME/.cache/bazel"
fi

if [ "$ARCH" = "aarch64" ]; then
  DOCKERFILE="${ROOT}/ci/ota_dev_arm64.dockerfile"
fi

CONTAINER_NAME="ota-file-service-container"
# Remove any exited containers.
if [ "$(docker ps -a --quiet --filter status=exited --filter name=$CONTAINER_NAME)" ]; then
    docker rm $CONTAINER_NAME > /dev/null
fi

# Re-use existing container.
if [ "$(docker ps -a --quiet --filter status=running --filter name=$CONTAINER_NAME)" ]; then
    echo "Attaching to running container: $CONTAINER_NAME"
    docker exec -i -t  $CONTAINER_NAME /bin/bash $@
    exit 0
fi

docker build --network host -t isaac-ota-service-dev -f ${DOCKERFILE} "${ROOT}/ci/" \
--build-arg docker_id="$(getent group docker | cut -d: -f3)"

docker run -it --rm \
--network host \
--workdir "$PWD" \
--name "$CONTAINER_NAME" \
-e "WORKSPACE=$ROOT" \
-v "$ROOT:$ROOT" \
-v /etc/passwd:/etc/passwd:ro \
-v /etc/timezone:/etc/timezone:ro \
-v /etc/group:/etc/group:ro \
-v "$HOME/.docker:$HOME/.docker:ro" \
-v "$HOME/.docker/buildx:$HOME/.docker/buildx" \
-v "$HOME/.kube:$HOME/.kube:ro" \
-v "/etc/timezone:/etc/timezone:ro" \
-v "$HOME/.cache/bazel:$HOME/.cache/bazel" \
-v /var/run/docker.sock:/var/run/docker.sock \
-u $(id -u) \
--group-add $(getent group docker | cut -d: -f3) \
isaac-ota-service-dev /bin/bash
