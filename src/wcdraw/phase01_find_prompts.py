#!/usr/bin/env python3
import argparse
import yaml
import time
import requests
import json
import pika
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, Prompt
from pika.exceptions import StreamLostError


API_ENDPOINT = "https://discord.com/api/v10"
CHAN_ID_MAP = {
    24: "989268312036896818",
    54: "997260995883966464",
    84: "997271660900126801",
}


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - find prompts")
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
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost", heartbeat=10)
    )
    channel = connection.channel()
    channel.queue_declare(queue="wcd_prompts", durable=True)
    i = 0
    session = Session(engine)
    while args.iterations < 0 or i < args.iterations:
        main_loop_iteration(
            discord_access_token, channel_ids, session, channel
        )
        if i % 2 == 0:
            connection.process_data_events()
        time.sleep(1)
        i = i + 1


def main_loop_iteration(token, channel_ids, session, channel):
    # collect the latest messages from the desired channels
    messages = []
    for item in channel_ids:
        messages.extend(get_latest_messages(token, item, 100))
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
        if "'" in message["content"]:
            continue
        special_string = message["content"].split(" ")[-2:-1][0]
        if "(0%)" in special_string:
            message_is_queued_to_start_soon = True
            # print("FOUNDONE")
            info = get_prompt_info(message, session, channel)
        elif "(" in special_string and "%)" in special_string:
            # There is nothing (very) useful about finding an in-progress render
            # if we cant track it from the beginning
            pass
        else:
            # TODO: we should do something with completed images here if we want
            # to match the old prototype's design
            pass


def get_latest_messages(token, channel_id, count=100):
    headers = {"Authorization": token}
    resp = requests.get(
        f"{API_ENDPOINT}/channels/{channel_id}/messages?limit={count}",
        headers=headers,
    )
    messages = resp.json()
    # json_formatted_str = json.dumps(res, indent=4)
    # print(json_formatted_str)
    return messages


def get_prompt_info(message, session, channel):
    prompt = message["content"].split("**")[1]
    author_id = message["mentions"][0]["id"]
    author_username = message["mentions"][0]["username"]
    author_discriminator = message["mentions"][0]["discriminator"]
    timestamp = datetime.strptime(
        message["timestamp"], "%Y-%m-%dT%H:%M:%S.%f%z"
    )
    message_id = message["id"]
    channel_id = message["channel_id"]
    # json_pretty_print(message)
    q = session.query(Prompt.id).filter(Prompt.message_id == message_id)
    prompt_discovered = session.query(q.exists()).scalar()
    session.commit()
    print("found one at zero percent")
    if not prompt_discovered:
        prompt = Prompt(
            author_id=author_id,
            author_username=author_username,
            author_discriminator=author_discriminator,
            timestamp=timestamp,
            message_id=message_id,
            channel_id=channel_id,
        )
        message = prompt.as_json()
        session.begin()
        try:
            channel.basic_publish(
                exchange="",
                routing_key="wcd_prompts",
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent
                ),
            )
            # print(f" [x] Sent {message}")
            print("added it to the queue")
            session.add(prompt)
        except StreamLostError as ex:
            print(ex)
            print(message)
            session.rollback()
        else:
            session.commit()


def json_pretty_print(in_val):
    print(json.dumps(in_val, indent=4))


if __name__ == "__main__":
    main()
