#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import subprocess
from datetime import datetime
from datetime import timedelta
import argparse

TIME_STEP = 60 * 60

def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--iterations',
                        '-i',
                        type=int,
                        default=-1,
                        help='number of loop iterations, -1 for infinite')
    args = parser.parse_args()
    begin = datetime.utcnow()

    commands = dict(
        find1={'cmd': ["./find_new_renders.py", "-c", "24", "-i","-1"], 'cwd': "."},
        find2={'cmd': ["./find_new_renders.py", "-c", "54", "-i","-1"], 'cwd': "."},
        find3={'cmd': ["./find_new_renders.py", "-c", "84", "-i","-1"], 'cwd': "."},
        track1={'cmd': ["./track_new_renders.py", "-i","-1"], 'cwd': "."},
        down1={'cmd': ["./download_images.py", "-i","-1"], 'cwd': "."},
        render1={'cmd': ["./render_clips.py", "-i","-1"], 'cwd': "."},
    )
    for key in commands:
        commands[key]["proc"] = subprocess.Popen(commands[key]["cmd"], cwd=commands[key]["cwd"], stdout=subprocess.DEVNULL)
        print(commands[key]["proc"].poll())


    prev_time = begin
    i = 0
    while args.iterations < 0 or i < args.iterations:
        loop_now = datetime.utcnow()
        diff = loop_now - prev_time
        diff_seconds = diff.total_seconds()
        if diff_seconds > TIME_STEP:
            print('an hour passed, rerunning scripts that died')
            for key in commands:
                if(commands[key]["proc"].poll() is not None):
                    print(f'{key} died, restarting')
                    commands[key]["proc"] = subprocess.Popen(commands[key]["cmd"], cwd=commands[key]["cwd"], stdout=subprocess.DEVNULL)
            print(f'{(loop_now - begin).total_seconds()} seconds passed')
            prev_time += timedelta(seconds=TIME_STEP)


        print(f'loop_count {i}')
        sleep(1)
        i += 1

    return


if __name__ == '__main__':
    main()
