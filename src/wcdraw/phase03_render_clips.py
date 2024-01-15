#!/usr/bin/env python3
import argparse
import yaml
import time
import json
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from common import Base, Prompt, RenderStage, RenderOutputEvent
from common import timestring_to_datetime, json_pretty_print
from common import safe_get_discord_messages, get_top_n_prompt_ids
import os
import requests
import shutil
import math
import textwrap
from PIL import Image, ImageDraw, ImageFont
import subprocess


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
    prompt_ids = get_top_n_prompt_ids(engine, 5, False)
    print(prompt_ids)

    prompt_info_arr = get_info_on_prompts(prompt_ids, engine)

    # make the working directory for each prompt
    for item in prompt_info_arr:
        item["workdir"] = f"workdir/prompt_{item['prompt_id']}"
        if not os.path.exists(item["workdir"]):
            os.mkdir(item["workdir"])

    # Download, format, and convert each of the final images
    for item in prompt_info_arr:
        # Download the final image
        item["final_image_path"] = f"{item['workdir']}/final_image.png"
        # Download the image
        response = requests.get(item["final_url"], stream=True)
        with open(item["final_image_path"], "wb") as outfile:
            shutil.copyfileobj(response.raw, outfile)
        convert_png_to_webp(
            item["workdir"], "final_image.png", "final_image.webp"
        )
        item["final_image_path"] = f"{item['workdir']}/final_image.webp"
        # Resize adding margin as necessary
        resize_file_in_place(item["final_image_path"], 1920, 1080)

    # Create an annotated final product image with the right size and filetype
    for item in prompt_info_arr:
        item["annotated_image_path"] = f"{item['workdir']}/annotated_image.png"
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
        usable_stages = item["working_stage_paths"][-16:]
        index = 0
        # first copy in the render stages (dupes as necessary)
        for stage in usable_stages:
            shutil.copy(stage, f"%s/seq_%04d.webp" % (item["workdir"], index))
            index += 1
            if index <= 5 and len(usable_stages) < 10:
                # reuse the first few images when we dont have a ton
                shutil.copy(
                    stage, f"%s/seq_%04d.webp" % (item["workdir"], index)
                )
                index += 1
        # Copy the final image twice
        shutil.copy(
            item["final_image_path"],
            f"%s/seq_%04d.webp" % (item["workdir"], index),
        )
        index += 1
        shutil.copy(
            item["final_image_path"],
            f"%s/seq_%04d.webp" % (item["workdir"], index),
        )
        index += 1
        # Fill the rest of the video with the annotated image
        while index <= 19:
            shutil.copy(
                item["annotated_image_path"],
                f"%s/seq_%04d.webp" % (item["workdir"], index),
            )
            index += 1
        # Copy in one black frame to end the video
        shutil.copy(
            "scripting/discord_scrape/black_frame.webp",
            f"%s/seq_%04d.webp" % (item["workdir"], index),
        )
        index += 1

    # Render each of the image sequences into an mp4 video
    for item in prompt_info_arr:
        item["output_video_path"] = f"{item['workdir']}/output.mp4"
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
                "slow",
                "-crf",
                "18",
                f"output.mp4",
            ]
        )
        os.system(f"cd {item['workdir']}; {cmd}")

    # Move each output video to a destination folder
    for item in prompt_info_arr:
        shutil.move(item["output_video_path"], item["local_video_path"])
        with Session(engine) as session:
            q = (
                update(Prompt)
                .where(Prompt.id == item["prompt_id"])
                .values(local_video_path=item["local_video_path"])
            )
            session.execute(q)
            session.commit()

    # Cleanup by removing the working directories
    for item in prompt_info_arr:
        shutil.rmtree(item["workdir"])

    # TODO -- cleanup rendered videos which are unlikely to be needed soon
    return


def get_info_on_prompts(prompt_ids, engine):
    result_arr = []
    for prompt_id in prompt_ids:
        final_url = None
        prompt_text = None
        source_stage_paths = []

        with Session(engine) as session:
            q = (
                session.query(Prompt, RenderStage)
                .join(RenderStage)
                .filter(Prompt.id == prompt_id)
            )
            for prompt, stage in q.all():
                final_url = prompt.final_url
                prompt_text = prompt.prompt_text
                if stage.local_path is not None and os.path.isfile(
                    stage.local_path
                ):
                    source_stage_paths.append(stage.local_path)
        local_video_path = f"outdir/prompt_{prompt_id}_output.mp4"
        if (
            prompt_id is not None
            and final_url is not None
            and prompt_text is not None
            and len(source_stage_paths) > 0
            and not os.path.exists(local_video_path)
        ):
            result_arr.append(
                dict(
                    prompt_id=prompt_id,
                    final_url=final_url,
                    prompt_text=prompt_text,
                    source_stage_paths=source_stage_paths,
                    local_video_path=local_video_path,
                )
            )
    return result_arr


def create_annotated_image(prompt_text, input_path, output_path):
    # Create an image which is the annotated final render
    img = Image.open(input_path).convert("RGBA")
    myFont = ImageFont.truetype("FreeMonoBold.ttf", 120)
    img_width_px, img_height_px = img.size
    shadow_overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    text_overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    text_i3 = ImageDraw.Draw(text_overlay)
    shadow_i3 = ImageDraw.Draw(shadow_overlay)
    margin = offset = 10
    num_lines = 0
    char_width_px, char_height_px = myFont.getsize("0")
    max_line_length = math.floor((img_width_px - 10 - 10) / char_width_px)
    for line in textwrap.wrap(prompt_text, width=max_line_length):
        text_i3.text((margin, offset), line, font=myFont, fill="#000000")
        offset += char_height_px
        num_lines += 1
    shadow_i3.rectangle(
        (
            10,
            10,
            img_width_px - 10,
            10 + (num_lines * myFont.getsize(line)[1]),
        ),
        fill=(255, 255, 255, 100),
    )
    out = Image.alpha_composite(img, shadow_overlay)
    out = Image.alpha_composite(out, text_overlay)
    out = resize_to_aspect(out, 1920, 1080)
    out.save(output_path)


def convert_png_to_webp(dirname, infname, outfname):
    # Convert to .webp
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-i", infname, "-c:v", "libwebp", outfname],
        cwd=dirname,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc.communicate()


def resize_to_aspect(in_img, desired_width_px, desired_height_px):
    img_width_px, img_height_px = in_img.size
    aspect = img_width_px / img_height_px
    desired_aspect = desired_width_px / desired_height_px
    if aspect == desired_aspect:
        # print('no-resize-needed')
        return in_img
    elif aspect < desired_aspect:
        # print('add to the sides')
        new_width = math.floor(
            img_width_px
            * (desired_width_px / desired_height_px)
            / (img_width_px / img_height_px)
        )
        diff = new_width - img_width_px
        padded = Image.new(in_img.mode, (new_width, img_height_px), (0, 0, 0))
        padded.paste(in_img, (math.floor(diff / 2), 0))
        # print(new_width)
        return padded
    else:
        # print('add to the top')
        new_height = math.floor(
            img_height_px
            / (desired_width_px / desired_height_px)
            * (img_width_px / img_height_px)
        )
        diff = new_height - img_height_px
        padded = Image.new(in_img.mode, (img_width_px, new_height), (0, 0, 0))
        padded.paste(in_img, (0, math.floor(diff / 2)))
        # print(new_height)
        return padded


def resize_file_in_place(fname, desired_width_px, desired_height_px):
    im = Image.open(fname)
    im = resize_to_aspect(im, desired_width_px, desired_height_px)
    im.save(fname)


if __name__ == "__main__":
    main()
