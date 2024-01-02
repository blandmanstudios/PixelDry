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
MAX_ATTEMPTS_TO_SCRAPE = 10


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - track progress")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="secure_params.yml",
        help="path to parameters file",
    )
    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=-1,
        help="number of loop iterations, -1 for infinite",
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
    i = 0
    while args.iterations < 0 or i < args.iterations:
        session = Session(engine)
        main_loop_iteration(discord_access_token, session)
        time.sleep(1)
        i += 1
    print("done")
    return


def main_loop_iteration(token, session):
    prompts = (
        session.query(Prompt)
        .filter(Prompt.is_complete == False)
        .filter(Prompt.n_tries < MAX_ATTEMPTS_TO_SCRAPE)
        .filter(Prompt.is_abandoned == False)
        .order_by(Prompt.n_tries.asc(), Prompt.timestamp.asc())
    )
    # loop once through all prompts that arent finished
    for prompt in prompts:
        # use a hack on the messages API to get a message using the messages api
        # because you need a "bot" token to request a specific message
        headers = {"Authorization": token}
        resp = requests.get(
            f"{API_ENDPOINT}/channels/{prompt.channel_id}/messages?limit=3&around={prompt.message_id}",
            headers=headers,
        )
        messages = resp.json()
        found = False
        for message in messages:
            if (
                prompt.message_id == message["id"]
                and prompt.channel_id == message["channel_id"]
            ):
                found = True
                break
        if found == True:
            # we found a render that is in progress, this is where we should
            # curl the image and save the "render stage" in the table
            print(
                f"found something in progress message_id={prompt.message_id} username={prompt.author_username}"
            )
        else:
            # give up on this cuz we arent even getting results on that message anymore immediately
            # this happens when a render has finished and midjourney bot deletes the message and
            # replaces it with a new render representing the final image
            print(
                f"abandoned message_id={prompt.message_id} username={prompt.author_username}"
            )
            prompt.is_abandoned = True
        prompt.n_tries += 1
        session.add(prompt)
        session.commit()
        session.commit()
    return


if __name__ == "__main__":
    main()
