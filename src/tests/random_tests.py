#!/usr/bin/env python3
import unittest
from wcdraw.common import timestring_to_datetime, Prompt, Base
from wcdraw.common import get_percentage_from_content
from wcdraw.common import download_image
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
import os


class TestMethods(unittest.TestCase):
    def test_download_image(self):
        local_path = "../workdir/scripting/testfile"
        image_with_no_content = "https://cdn.discordapp.com/attachments/989268312036896818/1196706332808577114/not_a_valid_path.png"
        r = download_image(image_with_no_content, local_path)
        os.remove(local_path)
        self.assertFalse(r)

        image_with_content = "https://upload.wikimedia.org/wikipedia/commons/0/07/An_astronaut_riding_a_horse_%28Hiroshige%29_2022-08-30.png"
        r = download_image(image_with_content, local_path)
        os.remove(local_path)
        self.assertTrue(r)

    def test_array_tricks(self):
        array = [dict(a=1), dict(a=2), dict(a=3), dict(a=4)]
        self.assertEqual(len(array), 4)
        failures = []
        for item in array:
            if item["a"] == 3:
                failures.append(item)
        for failure in failures:
            array.remove(failure)
        self.assertEqual(len(array), 3)
        failures = []
        for item in array:
            if item["a"] == 4:
                failures.append(item)
        for failure in failures:
            array.remove(failure)
        self.assertEqual(len(array), 2)

    def test_some_sql(self):
        # this is a helpful function if you want to practice building queries
        engine = create_engine(
            f"mariadb+pymysql://testuser:testpassword@localhost/wcddbtest?charset=utf8mb4",
        )
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            q = (
                update(Prompt)
                .where(Prompt.id == 10)
                .values(local_video_path="this would be a path")
            )
            print(q)

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

    def test_get_percentage_from_content(self):
        content_string = "**this is where the prompt goes** - <@999999999999999999> (0%) (fast)"
        self.assertEqual(get_percentage_from_content(content_string), 0)
        content_string = "**this is where the prompt goes** - <@999999999999999999> (15%) (fast)"
        self.assertEqual(get_percentage_from_content(content_string), 15)
        content_string = "**this is where the prompt goes** - <@999999999999999999> (46%) (fast)"
        self.assertEqual(get_percentage_from_content(content_string), 46)
        content_string = "**this is where the prompt goes** - <@999999999999999999> (Waiting to start) (fast)"
        self.assertEqual(get_percentage_from_content(content_string), None)
        content_string = "**this is where the prompt goes** - <@999999999999999999> (paused) (fast)"
        self.assertEqual(get_percentage_from_content(content_string), None)


if __name__ == "__main__":
    unittest.main()
