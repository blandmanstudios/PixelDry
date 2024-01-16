#!/usr/bin/env python3
import argparse
import yaml
import time
from datetime import datetime, timedelta
import subprocess
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, get_top_n_prompt_ids, RenderOutputEvent

EVENT_DURATION_SEC = 20
LOOP_LENGTH = 30
TRIGGER_PROXIMITY = timedelta(seconds=60)


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
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)

    start_time = datetime.utcnow()
    n_queued = queue_up_enough_videos(start_time, engine, 6)
    if not dry_run:
        process = launch_ffmpeg(primary_stream_url, stream_key)
    else:
        process = None
    print(f"process_is_alive={is_process_alive(process)}")

    i = 0
    while args.iterations < 0 or i < args.iterations:
        # check that ffmpeg is still running, if its not, restart it (queueing up stuff as necessary)
        print(f"process_is_alive={is_process_alive(process)}")

        if not is_process_alive(process):
            print("ffmpeg has died, we gotta start over")
            start_time = datetime.utcnow()
            n_queued = queue_up_enough_videos(start_time, engine, 6)
            if not dry_run:
                process = launch_ffmpeg(primary_stream_url, stream_key)

        # check that we have enought render events queued up to keep ffmpeg entertained by doing now - starttime modulo total time
        good_till_time = start_time + timedelta(
            seconds=n_queued * EVENT_DURATION_SEC
        )
        now = datetime.utcnow()
        good_for_time = good_till_time - now
        print(
            f"the current time is {now} which means we are good for {good_for_time} because we are good till {good_till_time}. should_run={good_for_time < TRIGGER_PROXIMITY}, n_queued={n_queued}"
        )
        if good_for_time < TRIGGER_PROXIMITY:
            n = queue_up_enough_videos(start_time, engine, 1, n_queued)
            n_queued += n
            print(f"queued up {n} new videos because we were getting to close")

        time.sleep(1)
        i = i + 1
    if not dry_run:
        process.kill()


def queue_up_enough_videos(
    start_time, engine, video_count, n_previously_queued=0
):
    prompt_ids = get_top_n_prompt_ids(engine, video_count, ready=True)
    number = 0
    for i, prompt_id in enumerate(prompt_ids):
        output_video_slot = "vid%04d.mp4" % (
            (i + n_previously_queued) % LOOP_LENGTH
        )
        shutil.copy(
            f"outdir/prompt_{prompt_id}_output.mp4",
            f"outdir/{output_video_slot}",
        )
        # log this as a render event that this video got queued up to run at X'oclock
        event = RenderOutputEvent(
            prompt_id=prompt_id,
            timestamp=start_time
            + timedelta(
                seconds=EVENT_DURATION_SEC * (i + n_previously_queued)
            ),
            output_video_slot=output_video_slot,
        )
        with Session(engine) as session:
            session.add(event)
            session.commit()
        number += 1
    return number


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
        "video_list.txt",
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
        "libopenh264",
        "-shortest",
        "-qscale",
        "0",
        "-g",
        "1",
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
