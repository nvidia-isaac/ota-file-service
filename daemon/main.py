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
import logging
import threading

import uvicorn

from daemon.classes import api_v1
from daemon.classes.daemon import OTAFileDaemon

parser = argparse.ArgumentParser()
parser.add_argument('--config', help='Config file')
parser.add_argument('--host', type=str,
                    default='0.0.0.0', help='Daemon API host.')
parser.add_argument('--port', type=int,
                    default=9000, help='Daemon API port.')
parser.add_argument('--verbose', default='INFO', help='Verbosity level')
args = parser.parse_known_args()[0]
logging.basicConfig(level=getattr(logging, args.verbose))

def run_app():
    app = api_v1.get_app()
    uvicorn.run(app, host=args.host, port=args.port)

def main():
    try:
        ota_daemon = OTAFileDaemon(args.config)
    except ValueError as e:
        logging.warning(e)
        logging.warning('The OTA daemon config file is invalid.'
                        ' Ignore this if you are not using OTA File Service.')
        return
    app_thread = threading.Thread(target=run_app, daemon=True)
    app_thread.start()
    ota_daemon.run()

if __name__ == '__main__':
    main()
