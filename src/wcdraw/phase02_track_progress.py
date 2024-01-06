#!/usr/bin/env python3
import argparse
import yaml
import time
import requests
import json
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import (
    Base,
    Prompt,
    RenderStage,
    json_pretty_print,
    get_percentage_from_content,
    safe_get_discord_messages,
)

MAX_ATTEMPTS_TO_SCRAPE = 100


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
        with Session(engine) as session:
            main_loop_iteration(discord_access_token, session)
        time.sleep(1)
        i += 1
    print("done")
    return


def main_loop_iteration(token, session):
    prompts = (
        session.query(Prompt)
        .filter(Prompt.n_tries < MAX_ATTEMPTS_TO_SCRAPE)
        .filter(Prompt.is_abandoned == False)
        .order_by(Prompt.n_tries.asc(), Prompt.timestamp.asc())
    )
    # loop once through all prompts that arent finished
    for prompt in prompts:
        # use a hack on the messages API to get a message using the messages api
        # because you need a "bot" token to request a specific message
        messages = safe_get_discord_messages(
            token=token,
            channel_id=prompt.channel_id,
            message_id=prompt.message_id,
            count=3,
        )
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
            # json_pretty_print(message)

            # Parse out the progress percentage
            percentage = get_percentage_from_content(message["content"])

            image_url = ""
            # Parse out the image url and filetype
            for attachment in message["attachments"]:
                image_url = attachment["url"]
                render_id = (
                    attachment["filename"].rstrip(".webp").split("_")[0]
                )
                if render_id is not None:
                    prompt.render_id = render_id
            extension = image_url.split(".")[-1].split("?")[0]
            # If the stage hasn't been visited yet, download and add it
            stage = (
                session.query(RenderStage)
                .filter(RenderStage.prompt_id == prompt.id)
                .filter(RenderStage.percentage == percentage)
                .first()
            )
            if stage is None and percentage is not None and image_url != "":
                print(
                    f"downloading the image for prompt_id={prompt.id} percentage={percentage}"
                )
                local_path = f"data/{prompt.id}_{percentage}.{extension}"
                stage = RenderStage(
                    prompt_id=prompt.id,
                    percentage=percentage,
                    image_url=image_url,
                    local_path=local_path,
                )
                try:
                    # Download the image
                    response = requests.get(image_url, stream=True)
                    with open(local_path, "wb") as outfile:
                        shutil.copyfileobj(response.raw, outfile)
                    del response
                    session.add(stage)
                except requests.exceptions.ConnectionError as ex:
                    # this happened in my testing, I suspect it is because the dicord bot changed
                    #   the image associated with this message before we got a chance to download
                    #   it, so the downloading the image fails
                    # thus, for this edge case, we log and move on (no retry)
                    print("failed to download image, skipping ex={ex}")
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
    return


if __name__ == "__main__":
    main()
