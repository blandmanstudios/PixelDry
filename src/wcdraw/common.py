#!/usr/bin/env python3

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy import ForeignKey, select, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


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
    render_stages = relationship("RenderStage")

    @hybrid_property
    def is_complete(self):
        for stage in self.render_stages:
            if stage.percentage == 100:
                return True
        return False

    @is_complete.expression
    def is_complete(cls):
        return (
            select(func.count(RenderStage.id) > 0)
            .where(
                (RenderStage.prompt_id == cls.id)
                & (RenderStage.percentage == 100)
            )
            .label("is_complete")
        )
        pass

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


def json_pretty_print(in_val):
    print(json.dumps(in_val, indent=4))
