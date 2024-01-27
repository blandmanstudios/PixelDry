#!/usr/bin/env python3
import argparse
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import select, desc, func
from common import Base, Prompt, RenderOutputEvent


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - find prompts")
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
    # print(channel_ids)
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)

    # Do an placeholder sql query
    with Session(engine) as session:
        q = session.query(Prompt.id).limit(1)
        prompt_discovered = session.query(q.exists()).scalar()
        if prompt_discovered:
            print("one prompt certainly does exist in the database")


if __name__ == "__main__":
    main()
