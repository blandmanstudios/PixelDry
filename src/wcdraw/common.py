#!/usr/bin/env python3

import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Prompt(Base):
    __tablename__ = "prompt"
    id = Column(Integer, primary_key=True)
    message_id = Column(Text)
    author_id = Column(Text)
    author_username = Column(Text)
    author_discriminator = Column(Text)
    channel_id = Column(Text)
    timestamp = Column(DateTime)
    render_stages = relationship("RenderStage")

    def as_dict(self):
        return dict(
            message_id=self.message_id,
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

    def as_dict(self):
        return dict(
            prompt_id=self.prompt_id,
            percentage=self.percentage,
            image_url=image_url,
        )

    def as_json(self):
        return json.dumps(self.as_dict())
