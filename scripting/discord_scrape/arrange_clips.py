#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import os
import shutil
from PIL import Image, ImageDraw, ImageFont
import textwrap
import subprocess
from datetime import datetime
from datetime import timedelta

TIME_STEP = 20
N_FILES = 100
N_LEAD_CLIPS = 20
RUN_LOOP_LENGTH = 60*60*4

def main():
    clip_con = sqlite3.connect('clip_metadata.db.test')
    clip_cur = clip_con.cursor()
    query_string = "CREATE TABLE IF NOT EXISTS clips (clip_id INTEGER PRIMARY KEY, content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), render_id varchar(100), n_stitched INTEGER, unique (render_id));"
    clip_cur.execute(query_string)
    os.makedirs('loop_dir', exist_ok=True)

    index = 0
    for i in range(N_LEAD_CLIPS):
        next_clip_fname = get_next_clip_fname(clip_con, clip_cur)
        shutil.copyfile(next_clip_fname, 'loop_dir/vid%04d.mp4' % (index % N_FILES))
        index += 1

    begin = datetime.utcnow()
    prev_time = begin
    i = 0
    while i < RUN_LOOP_LENGTH:
        loop_now = datetime.utcnow()
        diff = loop_now - prev_time
        diff_seconds = diff.total_seconds()
        if diff_seconds > TIME_STEP:
            print((loop_now - begin).total_seconds())
            next_clip_fname = get_next_clip_fname(clip_con, clip_cur)
            shutil.copyfile(next_clip_fname, 'loop_dir/vid%04d.mp4' % (index % N_FILES))
            index += 1
            print(True)
            prev_time += timedelta(seconds=TIME_STEP)
        print(i)
        i += 1
        sleep(1)
    return


def get_next_clip_fname(clip_con, clip_cur):
    query = "SELECT render_id, clip_id, n_stitched FROM clips ORDER BY n_stitched ASC, timestamp DESC LIMIT 1"
    clip_cur.execute(query)
    for render_id, clip_id, n_stitched in clip_cur.fetchall():
        print(render_id)
        query = f"UPDATE clips SET n_stitched = '{n_stitched + 1}' WHERE render_id = '{render_id}'"
        clip_cur.execute(query)
        clip_con.commit()
        return f'clips/{render_id}.mp4'

if __name__ == '__main__':
    main()
