# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

load("@python_third_party//:requirements.bzl", "requirement")
load("//bzl:python.bzl", "ota_file_service_py_library")

ota_file_service_py_library(
    name = "classes",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        "//utils",
        requirement("boto3"),
        requirement("fastapi"),
        requirement("uvicorn"),
        requirement("paho-mqtt"),
        requirement("pydantic"),
        requirement("PyYAML"),
        requirement("requests"),
    ],
)
