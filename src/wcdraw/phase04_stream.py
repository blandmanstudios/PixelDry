#!/usr/bin/env python3
import argparse
import yaml
import time
from datetime import datetime, timedelta
import subprocess
import shutil
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, get_top_n_prompt_ids, RenderOutputEvent

LOOP_LENGTH = 3
LOOK_AHEAD = 2
VIDEO_LIST_FILE = "video_list.txt"


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - stream video")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="secure_params.yml",
        help="path to parameters file",
    )
    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=-1,
        help="number of loop iterations, -1 for infinite",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        help="dont run stream, just consume videos",
    )
    args = parser.parse_args()
    with open(args.config, "r") as file:
        params = yaml.safe_load(file)
    dry_run = args.dry_run
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    primary_stream_url = params["primary_stream_url"]
    stream_key = params["stream_key"]

    # put together a map of the video fnames in the loop
    index_to_video = []
    with open(f"outdir/{VIDEO_LIST_FILE}") as file:
        for i, line in enumerate(file.readlines()):
            video_name = line.split("'")[1]
            index_to_video.append(video_name)

    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)

    n_queued = queue_up_enough_videos(engine, LOOK_AHEAD, index_to_video)
    last_video_name = index_to_video[0]
    if not dry_run:
        process = launch_ffmpeg(primary_stream_url, stream_key)
        # TODO: I need a try catch block that will kill process in any error
    else:
        process = None
    print(f"n_queued={n_queued}, last_video_name={last_video_name}")
    print(f"process_is_alive={is_process_alive(process)}")

    i = 0
    while args.iterations < 0 or i < args.iterations:
        # restart ffmpeg if it is not running
        if not is_process_alive(process):
            print("ffmpeg has died, we gotta start over")
            n_queued = queue_up_enough_videos(
                engine, LOOK_AHEAD, index_to_video
            )
            last_video_name = index_to_video[0]
            if not dry_run:
                process = launch_ffmpeg(primary_stream_url, stream_key)

        video_name = get_ffmpeg_location()
        print(
            f"last_video_name={last_video_name}, video_name={video_name}, n_queued={n_queued}, NEXT_SLOT={n_queued % LOOP_LENGTH}"
        )

        # if you get a valid location that ffmpeg is reading and ffmpeg has
        # clearly moved onto the next file, we need to queue another one up
        if video_name is not None and video_name != last_video_name:
            n = queue_up_enough_videos(engine, 1, index_to_video, n_queued)
            n_queued += n
            last_video_name = video_name

        time.sleep(1)
        i = i + 1
    if not dry_run:
        process.kill()


def queue_up_enough_videos(
    engine, video_count, index_to_video, n_previously_queued=0
):
    prompt_ids = get_top_n_prompt_ids(engine, video_count, ready=True)
    number = 0
    for i, prompt_id in enumerate(prompt_ids):
        output_video_slot = index_to_video[
            (i + n_previously_queued) % LOOP_LENGTH
        ]
        input_video_path = f"outdir/prompt_{prompt_id}_output.mp4"
        shutil.copy(
            input_video_path,
            f"outdir/{output_video_slot}",
        )
        print(f"queueing up a video at slot {output_video_slot}")
        # Log the time we have added this to the circular queue to stream
        event = RenderOutputEvent(
            prompt_id=prompt_id,
            timestamp=datetime.utcnow(),
            duration=get_video_duration(input_video_path),
            output_video_slot=output_video_slot,
        )
        with Session(engine) as session:
            session.add(event)
            session.commit()
        number += 1
    return number


def get_video_duration(filename):
    result = subprocess.check_output(
        f"ffprobe -v quiet -show_streams -select_streams v:0 -of json {filename}",
        shell=True,
    ).decode()
    fields = json.loads(result)["streams"][0]
    duration = float(fields["duration"])
    print(f"duration was{duration}")
    return duration


def get_ffmpeg_location():
    cmd = "fuser outdir/vid00*"
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    # print(f'fuser output was stdout={stdout}, stderr={stderr}')
    outstrings = stderr.decode("UTF-8").split("\n")
    outstrings = [x for x in outstrings if x != ""]
    if len(outstrings) > 1:
        print("mutliple files are being read im confused")
        return None
    if len(outstrings) == 0:
        print("no files being read")
        return None
    file_being_read = outstrings[0].split("/")[-1].rstrip(":")
    return file_being_read


def launch_ffmpeg(stream_url, stream_key):
    # create the start command
    cmd = [
        "ffmpeg",
        "-re",
        "-stream_loop",
        "-1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        VIDEO_LIST_FILE,
        "-stream_loop",
        "-1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "audio_list.txt",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-threads",
        "2",
        "-shortest",
        "-qscale",
        "0",
        "-g",
        "90",
        "-f",
        "flv",
        f"rtmp://{stream_url}/{stream_key}",
    ]
    return subprocess.Popen(
        cmd,
        cwd="outdir",
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL,
    )


def is_process_alive(proc):
    # for dry run mode proc is None, simulate alive
    if proc is None:
        return True

    # poll returns None when still running
    return proc.poll() is None


if __name__ == "__main__":
    main()
