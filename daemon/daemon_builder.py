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

import argparse
import os

import PyInstaller.__main__ as pyinstaller  # type: ignore

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='The directory in which to create the "osmo" onedir')
    args = parser.parse_args()

    # Create the top level dir
    os.makedirs(args.dir, exist_ok=True)

    pyinstaller.run(['--onefile', f'{os.getcwd()}/daemon/main.py',
                     '-n', 'ota-daemon',
                     '--distpath', args.dir])


if __name__ == '__main__':
    main()
