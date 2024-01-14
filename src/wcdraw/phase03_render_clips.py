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
    prompt_ids_to_prep = get_top_n_prompt_ids(engine, 5, False)
    print(prompt_ids_to_prep)
    for prompt_id in prompt_ids_to_prep:
        output_file_path = f"outdir/{prompt_id}_video.mp4"
        print(output_file_path)
        if os.path.isfile(output_file_path):
            # if desired output file exists we dont need to recreate it
            continue

        # Find the filenames for the render stages and stuff
        final_url = None
        prompt_text = ""
        stage_images = []
        with Session(engine) as session:
            q = (
                session.query(Prompt, RenderStage)
                .join(RenderStage)
                .filter(Prompt.id == prompt_id)
            )
            for prompt, stage in q.all():
                final_url = prompt.final_url
                prompt_text = prompt.prompt_text
                percentage = stage.percentage
                extension = "webp"
                local_path = f"data/{prompt_id}_{percentage}.{extension}"
                if stage.local_path is None or not os.path.isfile(local_path):
                    # if there is no file or it is missing lets skip it
                    # downloading is unreliable and if I implement a cleanup
                    #   we can do it at the same time
                    continue
                print(stage.image_url)
                stage_images.append(local_path)
        print(stage_images)

        # Download the final image
        local_path = f"workdir/final_image.png"
        # Download the image
        response = requests.get(final_url, stream=True)
        with open(local_path, "wb") as outfile:
            shutil.copyfileobj(response.raw, outfile)
        print(f"downloaded {final_url} to {local_path}")

        # Create an image which is the annotated final render
        img = Image.open(local_path).convert("RGBA")
        myFont = ImageFont.truetype("FreeMonoBold.ttf", 20)
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
        out.save(f"workdir/annotated_image.png")

        # Resize and reformat all the progression images so they match
        for i, item in enumerate(stage_images):
            fname = item.split("/")[1]
            shutil.copy(item, "workdir/" + fname)
            resize_file_in_place("workdir/" + fname, 1920, 1080)

        # copy some of the files in multiple times with funny index math to
        #   make the ending file the right length
        if len(stage_images) > 16:
            # cap the number of stages at 16 (ive seen 18)
            stage_images = stage_images[-16:]
        index = 0
        for i, item in enumerate(stage_images):
            fname = "workdir/seq_%02d.webp" % index
            shutil.copy(item, fname)
            resize_file_in_place(fname, 1920, 1080)
            index += 1
            if index <= 5 and len(stage_images) < 10:
                # reuse the first few images when we dont have a ton
                fname = "workdir/seq_%02d.webp" % index
                shutil.copy(item, fname)
                resize_file_in_place(fname, 1920, 1080)
                index += 1
        # Copy the final image in at least twice
        fname = "seq_%02d.webp" % index
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-i",
                "final_image.png",
                "-c:v",
                "libwebp",
                fname,
            ],
            cwd=f"workdir",
        )
        proc.communicate()
        resize_file_in_place("workdir/" + fname, 1920, 1080)
        index += 1
        fname = "seq_%02d.webp" % index
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-i",
                "final_image.png",
                "-c:v",
                "libwebp",
                fname,
            ],
            cwd=f"workdir",
        )
        proc.communicate()
        resize_file_in_place("workdir/" + fname, 1920, 1080)
        index += 1
        # For the remainder of the 20 seconds copy the annotated image
        while index <= 19:
            fname = "seq_%02d.webp" % index
            proc = subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    "annotated_image.png",
                    "-c:v",
                    "libwebp",
                    fname,
                ],
                cwd=f"workdir",
            )
            proc.communicate()
            resize_file_in_place("workdir/" + fname, 1920, 1080)
            index += 1
        # Copy in a black frame once
        fname = "workdir/seq_%02d.webp" % index
        shutil.copy(f"scripting/discord_scrape/black_frame.webp", fname)
        resize_file_in_place(fname, 1920, 1080)
        index += 1

        # render them each into an output mp4 video
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
        os.system(f"cd workdir; {cmd}")

        # move it off to a finished stuff folder
        shutil.move("workdir/output.mp4", f"outdir/{prompt_id}_output.mp4")

        # save into sql that the finished video exists somewhere (and save the
        #   video render algorithm version number that was used)
        # clear out the old videos that no longer need to exist now that we
        #   have a new top10 (or top N) saved on disk somewhere
        # also clear out old render stage images too (like the one for this
        #   video) because we wont need it for a while
        for file in os.listdir("workdir"):
            os.remove(f"workdir/{file}")

        # this algorithm guarentees we'll always have a the topN videos renders
        #   on disk (not the top N but the topN that are ready)
        # so the phase4 script can do a query to say of the ones that are
        #   rendered give topN (and start subbing those into the stream schedule)
    return


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
