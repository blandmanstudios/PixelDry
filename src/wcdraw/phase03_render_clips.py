#!/usr/bin/env python3
import argparse
import yaml
import time
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from common import Base, Prompt, RenderStage, RenderOutputEvent
from common import timestring_to_datetime, json_pretty_print
from common import safe_get_discord_messages, get_top_n_prompt_ids


def main():
    parser = argparse.ArgumentParser(prog="wcdraw - find prompts")
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
    args = parser.parse_args()
    # print(args)
    with open(args.config, "r") as file:
        params = yaml.safe_load(file)
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)
    i = 0
    while args.iterations < 0 or i < args.iterations:
        main_loop_iteration(engine)
        time.sleep(1)
        i = i + 1


def main_loop_iteration(engine):
    prompt_ids_to_prep = get_top_n_prompt_ids(engine, 5, False)
    print(prompt_ids_to_prep)
    for a in prompt_ids_to_prep:
        print(a)
        # check if the videos we want to render already exist and are saved on
        # disk somewhere no need to render it continue out of the loop
        with Session(engine) as session:
            q = (
                session.query(
                    Prompt.id,
                    RenderStage.percentage,
                    RenderStage.image_url,
                    RenderStage.local_path,
                )
                .join(RenderStage)
                .filter(Prompt.id == a)
            )
            for item in q.all():
                print(item.local_path)
                # if local_path is null
                # or if no file exists at local_path
                # redownload the image updating local path if necessary
                # copy each of those files off to a working directory
        # download the Prompt.final_url to that working directory too
        # do some image processing on the ending image and safe it off too
        # resize all the progression images to match
        # copy some of the files in multiple times with funny index math to
        #   make the ending file the right length
        # use ffmpeg to reformat each of the webp images  into png
        # render them each into an output mp4 video
        # move it off to a finished stuff folder
        # save into sql that the finished video exists somewhere (and save the
        #   video render algorithm version number that was used)
        # clear out the old videos that no longer need to exist now that we
        #   have a new top10 (or top N) saved on disk somewhere
        # also clear out old render stage images too (like the one for this
        #   video) because we wont need it for a while

        # this algorithm guarentees we'll always have a the topN videos renders
        #   on disk (not the top N but the topN that are ready)
        # so the phase4 script can do a query to say of the ones that are
        #   rendered give topN (and start subbing those into the stream schedule)
    return


if __name__ == "__main__":
    main()
