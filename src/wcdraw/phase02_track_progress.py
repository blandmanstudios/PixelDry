#!/usr/bin/env python3
import argparse
import yaml
import time
import requests
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, Prompt, RenderStage

API_ENDPOINT = "https://discord.com/api/v10"


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - track progress")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="secure_params.yml",
        help="path to parameters file",
    )
    args = parser.parse_args()
    # print(args)
    with open(args.config, "r") as file:
        params = yaml.safe_load(file)
    discord_access_token = params["discord_access_token"]
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    # main loop execution will go here
    print('done')
    return


if __name__ == "__main__":
    main()
