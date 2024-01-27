#!/usr/bin/env python3
import argparse
import yaml
import time
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, Prompt, timestring_to_datetime, json_pretty_print
from common import safe_get_discord_messages


CHAN_ID_MAP = {
    24: "989268312036896818",
    54: "997260995883966464",
    84: "997271660900126801",
    8: "989274728155992124",
    18: "995431387333152778",
}


def main():
    parser = argparse.ArgumentParser(prog="wpixdry - find prompts")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="secure_params.yml",
        help="path to parameters file",
    )
    parser.add_argument(
        "--list-channels",
        "-l",
        type=int,
        default=[24],
        nargs="+",
        help="which newbie discord channels to crawl",
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
    channel_ids = list(CHAN_ID_MAP[i] for i in args.list_channels)
    # print(channel_ids)
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)
    i = 0
    while args.iterations < 0 or i < args.iterations:
        main_loop_iteration(discord_access_token, channel_ids, engine)
        time.sleep(1)
        i = i + 1


def main_loop_iteration(token, channel_ids, engine):
    # collect the latest messages from the desired channels
    messages = []
    for item in channel_ids:
        # prelim testing shows a query of 15 doesnt miss much
        messages.extend(get_latest_messages(token, item, 15))
    # print(len(messages))
    # loop through the latest messages
    for message in messages:
        # skip messages that are not dict (I haven't seen this yet)
        if type(message) is not dict:
            continue
        # skip messages that are not from the bot (people text messages)
        if message["author"]["username"] != "Midjourney Bot":
            continue
        # skip messages that dont have bolding that the bot uses
        if "**" not in message["content"]:
            continue
        # bandaid: skip all messages that use any external links
        # because midjourney will hang at 0% for broken links
        if "https" in message["content"]:
            continue
        # bandaid: skip messages using chars that break my sql
        # note: this bandaid is likely obselete
        if "'" in message["content"]:
            continue
        special_string = message["content"].split(" ")[-2:-1][0]
        if "(0%)" in special_string:
            # TODO: We should add "(Waiting to start)" to this condition
            message_is_queued_to_start_soon = True
            info = get_prompt_info(message, engine)
        elif "(" in special_string and "%)" in special_string:
            # There is nothing (very) useful about finding an in-progress render
            # if we cant track it from the beginning, so do nothing with it
            pass
        else:
            # For the images that are finished we check if they are one of our
            # renders and if they are we should save their final info
            info = save_finished_prompts(message, engine)


def get_latest_messages(token, channel_id, count=100):
    return safe_get_discord_messages(
        token=token, channel_id=channel_id, message_id=None, count=count
    )


def get_prompt_info(message, engine):
    prompt_text = message["content"].split("**")[1]
    # TODO need to add an error case for then prompt text contains more than
    # two instances of **. This leads to truncated and even empty prompts shown
    # to the user
    author_id = message["mentions"][0]["id"]
    author_username = message["mentions"][0]["username"]
    author_discriminator = message["mentions"][0]["discriminator"]
    timestamp = timestring_to_datetime(message["timestamp"])
    message_id = message["id"]
    channel_id = message["channel_id"]
    # json_pretty_print(message)
    with Session(engine) as session:
        q = session.query(Prompt.id).filter(Prompt.message_id == message_id)
        prompt_discovered = session.query(q.exists()).scalar()
        print("found one at zero percent")
        if not prompt_discovered:
            # json_pretty_print(message)
            print("it was new")
            prompt = Prompt(
                prompt_text=prompt_text,
                author_id=author_id,
                author_username=author_username,
                author_discriminator=author_discriminator,
                timestamp=timestamp,
                message_id=message_id,
                channel_id=channel_id,
            )
            message = prompt.as_json()
            session.add(prompt)
            session.commit()
            print("added to db")


def save_finished_prompts(message, engine):
    if "attachments" in message and len(message["attachments"]) > 0:
        attachment = message["attachments"][0]
        render_id = attachment["filename"].rstrip(".png").split("_")[-1]
        with Session(engine) as session:
            q = session.query(Prompt).filter(
                (Prompt.render_id == render_id)
                & (Prompt.final_url == None)
                & (Prompt.final_message_id == None)
            )
            prompt = q.first()
            if prompt is not None:
                print(
                    f"found the end of the render with prompt_id={prompt.id}"
                )
                prompt.final_url = attachment["url"]
                prompt.final_message_id = message["id"]
                session.add(prompt)
                session.commit()


if __name__ == "__main__":
    main()
