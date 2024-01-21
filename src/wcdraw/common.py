#!/usr/bin/env python3

import json
import requests
import shutil
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy import ForeignKey, select, func, case, desc
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session

Base = declarative_base()

API_ENDPOINT = "https://discord.com/api/v10"


class Prompt(Base):
    __tablename__ = "prompt"
    id = Column(Integer, primary_key=True)
    render_id = Column(Text)
    final_url = Column(Text)
    final_message_id = Column(Text)
    prompt_text = Column(Text)
    message_id = Column(Text)
    author_id = Column(Text)
    author_username = Column(Text)
    author_discriminator = Column(Text)
    channel_id = Column(Text)
    timestamp = Column(DateTime)
    is_abandoned = Column(Boolean, default=False)
    n_tries = Column(Integer, default=0)
    local_video_path = Column(Text)
    render_stages = relationship("RenderStage")

    def as_dict(self):
        return dict(
            message_id=self.message_id,
            prompt_text=self.prompt_text,
            author_id=self.author_id,
            author_username=self.author_username,
            author_discriminator=self.author_discriminator,
            channel_id=self.channel_id,
            timestamp=self.timestamp.isoformat(),
        )

    def as_json(self):
        return json.dumps(self.as_dict())


class RenderStage(Base):
    __tablename__ = "render_stage"
    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompt.id"))
    percentage = Column(Integer)
    image_url = Column(Text)
    local_path = Column(Text)

    def as_dict(self):
        return dict(
            prompt_id=self.prompt_id,
            percentage=self.percentage,
            image_url=image_url,
        )

    def as_json(self):
        return json.dumps(self.as_dict())


class RenderOutputEvent(Base):
    __tablename__ = "render_output_event"
    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompt.id"))
    timestamp = Column(DateTime)
    duration = Column(Float)
    output_video_slot = Column(Text)

    def as_dict(self):
        return dict(prompt_id=self.prompt_id, timestamp=self.timestamp)

    def as_json(self):
        return json.dumps(self.as_dict())


def download_image(url, filepath):
    response = requests.get(url, stream=True)
    with open(filepath, "wb") as outfile:
        shutil.copyfileobj(response.raw, outfile)
    return response.status_code != 404


def timestring_to_datetime(timestring):
    # if there is no millisecond value, lets assume 00
    if "." not in timestring:
        timestring = timestring.replace("+", ".00+")
    return datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S.%f%z")


def get_percentage_from_content(content_string):
    # Parse out the progress percentage
    special_string = content_string.split(" ")[-2:-1][0]
    if "(" in special_string and ")" in special_string:
        segment = (
            special_string.replace("(", "").replace(")", "").replace("%", "")
        )
        return int(segment) if segment.isdigit() else None
    return None


def safe_get_discord_messages(token, channel_id, message_id=None, count=100):
    headers = {"Authorization": token}
    try:
        url = f"{API_ENDPOINT}/channels/{channel_id}/messages?limit={count}"
        if message_id is not None:
            url += f"&around={message_id}"
        resp = requests.get(
            url,
            headers=headers,
            timeout=10,
        )
        messages = resp.json()
    except requests.exceptions.ReadTimeout as ex:
        warn(
            f"Network failure (likely because we are disconnected from the internet), ex={ex}"
        )
        return []
    except requests.exceptions.SSLError as ex:
        warn(
            f"Network failure (likely because we are disconnected from the internet), ex={ex}"
        )
        return []
    except requests.exceptions.ConnectionError as ex:
        warn(
            f"Network failure (likely because we are disconnected from the internet), ex={ex}"
        )
        return []
    return messages


def get_top_n_prompt_ids(engine, n_prompts=5, ready=False):
    # in the future you'll be able to pass ready=True to get the top prompts that are ready to stream
    minimum_viable_stages = 4

    # this query will give you back prompt ids for a set of prompts which are a good choice to stream next based on things like
    # - how many times they've been on the stream recently
    # - how many times they've been on the stream in total
    # - how recently they've been on the stream
    # - how recently they've been created
    # The goal is to stream stuff that has never been seen and created recently (first)
    #   and if there is non of that, fallback to something that will feel trivial to a viewer
    with Session(engine) as session:
        subq = session.query(
            Prompt.id.label("id"),
            Prompt.local_video_path.label("local_video_path"),
            Prompt.timestamp.label("create_timestamp"),
            func.count(RenderStage.id).label("render_stages"),
            Prompt.final_url.label("final_url"),
        )
        if ready:
            subq = subq.filter(Prompt.local_video_path.is_not(None))
        subq = subq.outerjoin(RenderStage).group_by(Prompt.id).subquery()
        q = (
            select(
                subq.c.id,
                subq.c.create_timestamp,
                func.count(RenderOutputEvent.id).label("times_streamed"),
                func.count(
                    case(
                        (
                            RenderOutputEvent.timestamp
                            > datetime.utcnow() - timedelta(hours=24),
                            1,
                        )
                    )
                ).label("times_streamed_last24"),
                func.max(RenderOutputEvent.timestamp).label(
                    "most_recent_stream"
                ),
            )
            .where(
                (subq.c.render_stages >= minimum_viable_stages)
                & (subq.c.final_url != None)
            )
            .select_from(subq)
            .outerjoin(RenderOutputEvent)
            .group_by(subq.c.id)
            .order_by(
                "times_streamed_last24",
                "times_streamed",
                "most_recent_stream",
                desc("create_timestamp"),
            )
            .limit(n_prompts)
        )
        results = []
        for row in session.execute(q):
            results.append(row.id)
        return results


def debug(message):
    print(message)


def info(message):
    print(message)


def warn(message):
    print(message)


def error(message):
    print(message)


def json_pretty_print(in_val):
    print(json.dumps(in_val, indent=4))
