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
    ch.basic_ack(delivery_tag=method.delivery_tag)
    # channel.basic_publish(
    #    exchange="",
    #    routing_key="wcd_prompts",
    #    body=body,
    #    properties=pika.BasicProperties(
    #        delivery_mode=pika.DeliveryMode.Persistent
    #    ),
    # )


if __name__ == "__main__":
    main()
