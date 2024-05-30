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
load("@io_bazel_rules_docker//repositories:deps.bzl", container_deps = "deps")
load("@io_bazel_rules_docker//container:container.bzl", "container_pull")
load("@io_bazel_rules_docker//python3:image.bzl", _py3_image_repos = "repositories")
load("@python_third_party//:requirements.bzl", python_third_deps = "install_deps")
load("@python_third_party_linting//:requirements.bzl", python_third_linting_deps = "install_deps")
load("@io_bazel_rules_docker//contrib:dockerfile_build.bzl", "dockerfile_image")
load("@io_bazel_rules_docker//container:load.bzl", "container_load")


def ota_file_service_workspace():
    # Install python dependencies from pip
    python_third_deps()
    python_third_linting_deps()

    # Pull dependencies needed for docker containers
    container_deps()

    container_pull(
        name = "mosquitto_base",
        registry = "dockerhub.nvidia.com",
        repository = "eclipse-mosquitto",
        tag = "latest",
    )

    container_pull(
        name = "postgres_database_base",
        registry = "docker.io/library",
        repository = "postgres",
        tag = "14.5",
        digest = "sha256:db3825afa034c78d03e301c48c1e8ed581f70e4b1c0d9dd944e3639a9d4b8b75",
    )

    # Enable python3 based images
    _py3_image_repos()

    # Load dockerfile_image
    dockerfile_image(
        name = "base_docker_image",
        dockerfile = "@nvidia_isaac_ota_file_service//docker:Dockerfile.base",
        visibility = ["//visibility:public"],
    )

    # Load the image tarball.
    container_load(
        name = "loaded_base_docker_image",
        file = "@base_docker_image//image:dockerfile_image.tar",
        visibility = ["//visibility:public"],
    )
