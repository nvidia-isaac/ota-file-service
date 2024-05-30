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
import enum

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine

from app.classes import api_v1, models
from app.classes.database import SessionLocal
from app.classes.config import OTAFileServiceConfig
from app.classes.ota_file_service import OTAFileService

class VerbosityOptions(enum.Enum):
    INFO = 'INFO'
    WARN = 'WARN'
    DEBUG = 'DEBUG'

parser = argparse.ArgumentParser(description='OTA File Service Prototype')
parser.add_argument('--config', '-c', type=str, default='app/config/defaults.yaml',
                    help='Path to the yaml config file.')
parser.add_argument('--verbose', type=VerbosityOptions,
                    default=VerbosityOptions.INFO, choices=list(
                        VerbosityOptions),
                    help='Verbosity level')
parser.add_argument('--host', type=str,
                    default='0.0.0.0', help='OTA File Service host.')
parser.add_argument('--port', type=int,
                    default=9005, help='OTA File Service port.')
parser.add_argument('--root-path', default='',
                    help='If mission dispatch is hosted behind a reverse proxy ' \
                    'set this to the url it is routed to')
# Argument for enabling or disabling tracebacks and code lines
parser.add_argument('--dev', action='store_true',
                    help='Enable tracebacks')

args = parser.parse_known_args()[0]

app = FastAPI(debug=True, root_path=args.root_path)

@app.on_event('startup')
def startup():
    config = OTAFileServiceConfig(args.config)
    postgres_config = config.postgres_config

    sqlalchemy_database_url = (f'postgresql+psycopg2://{postgres_config.user}:'
                               f'{postgres_config.password}@{postgres_config.host}:'
                               f'{postgres_config.port}/{postgres_config.db_name}')
    engine = create_engine(sqlalchemy_database_url)
    SessionLocal.configure(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    OTAFileService(config)

def main():
    app.mount('/api/v1', api_v1.get_ota_file_service_app())
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
