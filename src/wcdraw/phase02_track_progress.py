#!/usr/bin/env python3
import argparse
import yaml
import time
import requests
import json
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, Prompt, RenderStage

API_ENDPOINT = "https://discord.com/api/v10"

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost")
)
channel = connection.channel()


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
    channel.queue_declare(queue="wcd_prompts", durable=True)
    session = Session(engine)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="wcd_prompts", on_message_callback=callback)
    channel.start_consuming()


def callback(ch, method, properties, body):
    print(f" [x] Received {body.decode()}")
    time.sleep(body.count(b"."))
    print(" [x] Done")
    # as soon as the message comes in query it to see if we have a new image URL
    # if the stage is a finished product
    #    save the url to the output queue, so someone can curl it
    #    save the stage info to MySQL
    #    ack the message
    # if the stage is 0-99% and has an image URL and we havent seen it before
    #    save the url to the output queue, so someone can curl it
    #    save the stage info to MySQL
    #    schedule a new input task to be requeued to remind me to re-track this
    #      in 10 seconds (incrementing the count)
    #    ack the message
    # if the stage is an image URL we have seen before (i just looked at it)
    #    save nothing to mysql or the output queu
    #    scheudle an input task to remind me to check this in 5 seconds
    #      incrementing the count
    #    ack the message
    # if this prompt has been tracked/queried more than 100 times
    #    save nothing to mysql, dont schedule any input tasks
    #    ack the message (it will never be processed again)
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    main()
