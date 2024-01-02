#!/usr/bin/env python3
import unittest
from wcdraw.common import timestring_to_datetime, Prompt, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class TestMethods(unittest.TestCase):
    def test_characters_to_mysql(self):
        # Test inserting non-ascii unicode characters to ensure db is configured correctly
        special_string = "ﺖﻳ  and 设 and sław and ך"
        engine = create_engine(
            f"mariadb+pymysql://testuser:testpassword@localhost/wcddbtest?charset=utf8mb4",
        )
        Base.metadata.create_all(engine)
        session = Session(engine)
        session.begin()
        prompt = Prompt(
            prompt_text=special_string,
            author_id="doesntmatter",
            author_username=special_string[-4:] + "author",
            author_discriminator="0",
            timestamp=timestring_to_datetime("2023-12-30T02:04:29.52+00:00"),
            message_id="doesntmatter",
            channel_id="doesntmatter",
        )
        session.add(prompt)
        session.commit()

    def test_strings_to_timestamps(self):
        typical_time = "2023-12-30T02:04:29.52+00:00"
        atypical_time = "2023-12-30T02:04:29+00:00"
        timestamp = timestring_to_datetime(typical_time)
        timestamp = timestring_to_datetime(atypical_time)


if __name__ == "__main__":
    unittest.main()
