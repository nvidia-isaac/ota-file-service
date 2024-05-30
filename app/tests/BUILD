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
load("//bzl:python.bzl", "ota_file_service_py_library")
load("//bzl:python.bzl", "ota_file_service_py_test")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@python_third_party//:requirements.bzl", "requirement")


ota_file_service_py_library(
    name = "test_context",
    srcs = [
        "test_context.py",
    ],
    data = [
        "//app:ota-file-service-img-bundle",
        "//app/tests/test_utils:mosquitto-img-bundle",
        "//app/tests/test_utils:postgres-database-img-bundle",
        "//app/config:defaults.yaml",
        "//daemon:ota-file-daemon-img-bundle",
    ],
    deps = [
        "//app/classes",
        "//app/tests/test_utils",
    ],
)

ota_file_service_py_test(
    name = "test",
    size = "large",
    srcs = [
        "test.py",
    ],
    deps = [
        ":test_context",
    ],
    tags = [
        "exclusive"
    ],
)
