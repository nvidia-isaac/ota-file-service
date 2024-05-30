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
load("//bzl:python.bzl", "ota_file_service_py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@python_third_party//:requirements.bzl", "requirement")

ota_file_service_py_binary(
    name = "ota-file-daemon",
    srcs = ["main.py"],
    main = "main.py",
    visibility = ["//visibility:public"],
    deps = [
        "//daemon/classes",
        requirement("fastapi"),
        requirement("pydantic"),
        requirement("uvicorn"),
    ]
)

ota_file_service_py_binary(
    build_image = False,
    name = "daemon_builder",
    srcs = ["daemon_builder.py"],
    deps = [
        "ota-file-daemon",
        requirement("pyinstaller"),
        requirement("importlib-metadata"),
    ]
)

run_binary(
    name = "daemon_onedir",
    args = ["$(location ota_daemon_onedir)"],
    outs = ["ota_daemon_onedir"],
    tool = ":daemon_builder",
    srcs = [
        "main.py",
        "ota-file-daemon",
    ]
)

