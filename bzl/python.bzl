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
load("@python_third_party_linting//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//python3:image.bzl", "py3_image")
load("@io_bazel_rules_docker//container:container.bzl", "container_bundle", "container_push")

def py_type_test(name, srcs, deps):
    native.py_test(
        name = name,
        main = "@nvidia_isaac_ota_file_service//bzl:pytype.py",
        srcs = ["@nvidia_isaac_ota_file_service//bzl:pytype.py"] + srcs,
        deps = deps + [requirement("mypy")],
        args = ["$(location {})".format(src) for src in srcs],
        tags = ["lint"],
    )

def py_lint_test(name, srcs):
    native.py_test(
        name = name,
        main = "@nvidia_isaac_ota_file_service//bzl:pylint.py",
        srcs = ["@nvidia_isaac_ota_file_service//bzl:pylint.py"] + srcs,
        deps = [requirement("pylint")],
        data = ["@nvidia_isaac_ota_file_service//bzl:pylintrc"],
        args = ["--rcfile=$(location @nvidia_isaac_ota_file_service//bzl:pylintrc)"] +
               ["$(location {})".format(src) for src in srcs],
        tags = ["lint"],
    )

def ota_file_service_py_test(**kwargs):
    native.py_test(**kwargs)
    py_type_test(
        name = kwargs["name"] + "-type-test",
        srcs = kwargs.get("srcs", []),
        deps = kwargs.get("deps", []),
    )
    py_lint_test(
        name = kwargs["name"] + "-lint-test",
        srcs = kwargs.get("srcs", []),
    )

def ota_file_service_py_library(**kwargs):
    native.py_library(**kwargs)
    py_type_test(
        name = kwargs["name"] + "-type-test",
        srcs = kwargs.get("srcs", []),
        deps = kwargs.get("deps", []),
    )
    py_lint_test(
        name = kwargs["name"] + "-lint-test",
        srcs = kwargs.get("srcs", []),
    )

def ota_file_service_py_binary(build_image=True, **kwargs):
    native.py_binary(**kwargs)
    py_type_test(
        name = kwargs["name"] + "-type-test",
        srcs = kwargs.get("srcs", []),
        deps = kwargs.get("deps", []),
    )
    py_lint_test(
        name = kwargs["name"] + "-lint-test",
        srcs = kwargs.get("srcs", []),
    )

    if build_image:
        image_kwargs = dict(**kwargs)
        if "main" not in image_kwargs:
            image_kwargs["main"] = image_kwargs["name"] + ".py"
        image_kwargs["name"] += "-img"
        py3_image(
            base = "@nvidia_isaac_ota_file_service//bzl:python_base",
            **image_kwargs
        )

        container_bundle(
            name = image_kwargs["name"] + "-bundle",
            images = {
                "bazel_image": image_kwargs["name"],
            },
            visibility = ["//visibility:public"],
        )
