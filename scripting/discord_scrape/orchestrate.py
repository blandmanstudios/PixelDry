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

HOUR_STEP = 60 * 60
STREAM_STEP = 30

def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    stream_url = params["stream_url"]
    stream_key = params["stream_key"]
    parser.add_argument('--iterations',
                        '-i',
                        type=int,
                        default=-1,
                        help='number of loop iterations, -1 for infinite')
    parser.add_argument('-q', '--query_only',
                    action='store_true')
    parser.add_argument('-s', '--stream_only',
                    action='store_true')
    args = parser.parse_args()
    query_only = args.query_only
    stream_only = args.stream_only
    begin = datetime.utcnow()

    commands = dict(
        find1={'cmd': ["./find_new_renders.py", "-c", "24", "-i","-1"], 'cwd': "."},
        find2={'cmd': ["./find_new_renders.py", "-c", "54", "-i","-1"], 'cwd': "."},
        find3={'cmd': ["./find_new_renders.py", "-c", "84", "-i","-1"], 'cwd': "."},
        track1={'cmd': ["./track_new_renders.py", "-i","-1"], 'cwd': "."},
        down1={'cmd': ["./download_images.py", "-i","-1"], 'cwd': "."},
        render1={'cmd': ["./render_clips.py", "-i","-1"], 'cwd': "."},
    )
    if not stream_only:
        for key in commands:
            commands[key]["proc"] = subprocess.Popen(commands[key]["cmd"], cwd=commands[key]["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(commands[key]["proc"].poll())
    if not query_only:
        arrange={'cmd': ["./arrange_clips.py", "-i","-1"], 'cwd': "."}
        arrange["proc"] = subprocess.Popen(arrange["cmd"], cwd=arrange["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(arrange["proc"].poll())
        sleep(3)
        ffmpeg={'cmd': ["ffmpeg", "-re", "-stream_loop", "-1", "-f", "concat", "-safe", "0", "-i", "video_list.txt", "-stream_loop", "-1", "-f", "concat", "-safe", "0", "-i", "audio_list.txt", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-x264-params", "keyint=10:scenecut=0", "-shortest", "-qscale", "0", "-g", "1", "-f", "flv", "-c", "copy", f"rtmp://{stream_url}/{stream_key}"], 'cwd': "loop_dir"}
        ffmpeg["proc"] = subprocess.Popen(ffmpeg["cmd"], cwd=ffmpeg["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(ffmpeg["proc"].poll())


    prev_time = begin
    stream_prev_time = begin
    i = 0
    while args.iterations < 0 or i < args.iterations:
        loop_now = datetime.utcnow()
        diff = loop_now - prev_time
        diff_seconds = diff.total_seconds()
        if diff_seconds > HOUR_STEP and not stream_only:
            print('an hour passed, rerunning scripts that died')
            for key in commands:
                if(commands[key]["proc"].poll() is not None):
                    print(f'{key} died, restarting')
                    commands[key]["proc"] = subprocess.Popen(commands[key]["cmd"], cwd=commands[key]["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f'{(loop_now - begin).total_seconds()} seconds passed')
            prev_time += timedelta(seconds=HOUR_STEP)
        stream_diff_seconds = (loop_now - stream_prev_time).total_seconds()
        if stream_diff_seconds > STREAM_STEP and not query_only:
            print('stream step passed checking to see if stream died')
            if arrange["proc"].poll() is not None or ffmpeg["proc"].poll() is not None:
                print('either the stream or the arrangement died, restart both')
                if arrange["proc"].poll() is None:
                    print('killing arrangement')
                    arrange["proc"].kill()
                else:
                    print('arrangement is dead')
                if ffmpeg["proc"].poll() is None:
                    print('killing stream')
                    ffmpeg["proc"].kill()
                else:
                    print('stream is dead')
                print('starting arrangement')
                arrange["proc"] = subprocess.Popen(arrange["cmd"], cwd=arrange["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(arrange["proc"].poll())
                print('sleep 3')
                sleep(3)
                print('starting stream')
                ffmpeg["proc"] = subprocess.Popen(ffmpeg["cmd"], cwd=ffmpeg["cwd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(ffmpeg["proc"].poll())
            print(f'{(loop_now - begin).total_seconds()} seconds passed')
            stream_prev_time += timedelta(seconds=STREAM_STEP)


        print(f'loop_count {i}')
        sleep(1)
        i += 1

    return


if __name__ == '__main__':
    main()
