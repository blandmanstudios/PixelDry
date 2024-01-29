#!/usr/bin/env python3
import argparse
import yaml
import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import select, desc, func
from common import Base, Prompt, RenderOutputEvent, download_image
from common import get_top_n_prompt_ids
from phase03_render_clips import (
    get_info_on_prompts,
    convert_png_to_webp,
    resize_file_in_place,
    create_annotated_image,
)


def main():
    parser = argparse.ArgumentParser(prog="wpixdry - command utilities")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="secure_params.yml",
        help="path to parameters file",
    )
    parser.add_argument("--download_top_n_prompts", type=int, default=None)
    parser.add_argument("--render_prompts", type=int, nargs="+", default=None)
    args = parser.parse_args()
    # print(args)
    with open(args.config, "r") as file:
        params = yaml.safe_load(file)
    # print(channel_ids)
    sqldb_username = params["sqldb_username"]
    sqldb_password = params["sqldb_password"]
    engine = create_engine(
        f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4",
        future=True,
    )
    Base.metadata.create_all(engine)

    # Do an placeholder sql query
    with Session(engine) as session:
        q = session.query(Prompt.id).limit(1)
        prompt_discovered = session.query(q.exists()).scalar()
        if prompt_discovered:
            print("one prompt certainly does exist in the database")
    if args.download_top_n_prompts is not None:
        n = args.download_top_n_prompts
        prompt_ids = get_top_n_prompt_ids(engine, n, False)
        print(f"going to download ids={prompt_ids}")
        prompt_info_arr = get_info_on_prompts(prompt_ids, engine)
        for item in prompt_info_arr:
            if item["final_url"] is not None:
                print(f'downloading id={item["prompt_id"]}')
                download_image(
                    item["final_url"],
                    f"workdir/scripting/prompt_final_{item['prompt_id']}.png",
                )
    if args.render_prompts is not None:
        prompt_ids = args.render_prompts
        prompt_info_arr = get_info_on_prompts(prompt_ids, engine)
        print(prompt_info_arr)

        # make the working directory for each prompt
        for item in prompt_info_arr:
            item["workdir"] = f"workdir/scripting/prompt_{item['prompt_id']}"
            if not os.path.exists(item["workdir"]):
                os.mkdir(item["workdir"])

        failures = []
        # Download, format, and convert each of the final images
        for item in prompt_info_arr:
            # Download the final image
            item["final_image_path"] = f"{item['workdir']}/final_image.png"
            # Download the image
            if not download_image(item["final_url"], item["final_image_path"]):
                failures.append(item)
                continue
            # Convert image
            convert_png_to_webp(
                item["workdir"], "final_image.png", "final_image.webp"
            )
            item["final_image_path"] = f"{item['workdir']}/final_image.webp"
            # Resize adding margin as necessary
            resize_file_in_place(item["final_image_path"], 1920, 1080)

        # For instances where the download fails, skip them
        for failure in failures:
            prompt_info_arr.remove(failure)

        # Create an annotated final product image with the right size and filetype
        for item in prompt_info_arr:
            item[
                "annotated_image_path"
            ] = f"{item['workdir']}/annotated_image.png"
            create_annotated_image(
                item["prompt_text"],
                item["final_image_path"],
                item["annotated_image_path"],
            )
            convert_png_to_webp(
                item["workdir"], "annotated_image.png", "annotated_image.webp"
            )
            item[
                "annotated_image_path"
            ] = f"{item['workdir']}/annotated_image.webp"

        # Copy all render stages to the working directory
        for item in prompt_info_arr:
            item["working_stage_paths"] = []
            for i, source_stage_path in enumerate(item["source_stage_paths"]):
                working_stage_path = f"{item['workdir']}/stage_{i}.webp"
                item["working_stage_paths"].append(working_stage_path)
                shutil.copy(source_stage_path, working_stage_path)

        # Resize all the render stage images (adding margin as necessary)
        for item in prompt_info_arr:
            for working_stage_path in item["working_stage_paths"]:
                resize_file_in_place(working_stage_path, 1920, 1080)

        # Arrange the images in order they should render (1 per second)
        for item in prompt_info_arr:
            usable_stages = item["working_stage_paths"]
            index = 0
            # first copy in the render stages
            for stage in usable_stages:
                shutil.copy(
                    stage, f"%s/seq_%04d.webp" % (item["workdir"], index)
                )
                index += 1
            # Copy the final image twice
            for i in range(3):
                shutil.copy(
                    item["final_image_path"],
                    f"%s/seq_%04d.webp" % (item["workdir"], index),
                )
                index += 1
            # Fill the rest of the video with the annotated image
            # Copy the annotated image 3 times
            for i in range(5):
                shutil.copy(
                    item["annotated_image_path"],
                    f"%s/seq_%04d.webp" % (item["workdir"], index),
                )
                index += 1
            # Copy in one black frame to end the video
            shutil.copy(
                "raw_frames/black_frame.webp",
                f"%s/seq_%04d.webp" % (item["workdir"], index),
            )
            index += 1

        # Render each of the image sequences into an mp4 video
        for item in prompt_info_arr:
            item[
                "output_video_path"
            ] = f"{item['workdir']}/output_{item['prompt_id']}.mp4"
            cmd = " ".join(
                [
                    "ffmpeg",
                    "-y",
                    "-framerate",
                    "1",
                    "-pattern_type",
                    "glob",
                    "-i",
                    "'seq_*.webp'",
                    "-c:v",
                    "libopenh264",
                    "-r",
                    "30",
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    "scale=1920:1080",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    f"output_{item['prompt_id']}.mp4",
                ]
            )
            os.system(f"cd {item['workdir']}; {cmd} >/dev/null 2>&1")


if __name__ == "__main__":
    main()
