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
import argparse
import math


def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--iterations',
                        '-i',
                        type=int,
                        default=-1,
                        help='number of loop iterations, -1 for infinite')
    args = parser.parse_args()
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    clip_con = sqlite3.connect('clip_metadata.db')
    clip_cur = clip_con.cursor()
    query_string = "CREATE TABLE IF NOT EXISTS clips (clip_id INTEGER PRIMARY KEY, content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), render_id varchar(100), n_stitched INTEGER, unique (render_id));"
    clip_cur.execute(query_string)
    os.makedirs('clips', exist_ok=True)
    i = 0
    while args.iterations < 0 or i < args.iterations:
        ending_image = None
        content = None
        render_id = None
        timestamp = None
        author_username = None
        author_discriminator = None
        progression_images = []
        query = "SELECT endings.render_id, endings.filename, endings.content, beginnings.timestamp, endings.author_username, endings.author_discriminator from endings JOIN beginnings on endings.beginning_id = beginnings.beginning_id WHERE endings.is_clipped = 'FALSE' AND endings.is_downloaded = 'TRUE' LIMIT 1"
        cur.execute(query)
        for render_id, filename, content, timestamp, author_username, author_discriminator in cur.fetchall():
            print(render_id)
            print(filename)
            ending_image = filename
            query = f"SELECT endings.render_id, progressions.filename from endings JOIN progressions ON endings.render_id == progressions.render_id WHERE endings.render_id = '{render_id}' ORDER BY percentage ASC"
            cur.execute(query)
            for prog_render_id, prog_filename in cur.fetchall():
                progression_images.append(prog_filename)
        if ending_image is not None and content is not None and len(progression_images) > 3 and len(progression_images) < 16:
            print('gonna proc')
            os.makedirs('renders', exist_ok=True)
            os.makedirs(f'renders/{render_id}', exist_ok=True)
            img = Image.open(f'data/{ending_image}')
            img2 = Image.open(f'data/{ending_image}').convert('RGBA')
            i1 = ImageDraw.Draw(img)
            myFont = ImageFont.truetype('FreeMonoBold.ttf', 20)
            img_width_px, img_height_px = img.size

            text_width_px = img.size[0] - 10
            shadow_overlay = Image.new('RGBA', img2.size, (255, 255, 255, 0))
            text_overlay = Image.new('RGBA', img2.size, (255, 255, 255, 0))
            text_i3 = ImageDraw.Draw(text_overlay)
            shadow_i3 = ImageDraw.Draw(shadow_overlay)
            # text_i3.text((10, 10), content, font=myFont, fill=(255, 0, 0, 255))
            margin = offset = 10
            num_lines = 0
            char_width_px, char_height_px = myFont.getsize("0")
            max_line_length = math.floor((img_width_px - 10 - 10) / char_width_px)
            for line in textwrap.wrap(content, width=max_line_length):
                text_i3.text((margin, offset), line, font=myFont, fill="#000000")
                # offset += myFont.getsize(line)[1]
                offset += char_height_px
                num_lines += 1
            print(num_lines)
            shadow_i3.rectangle((10, 10, img_width_px - 10, 10 + (num_lines * myFont.getsize(line)[1])), fill=(255,255,255, 100))
            img.save(f'renders/{render_id}/gen1_text.png')
            out = Image.alpha_composite(img2, shadow_overlay)
            out = Image.alpha_composite(out, text_overlay)
            out = resize_to_aspect(out, 1920, 1080)
            out.save(f'renders/{render_id}/gen2_text.png')
            print(ending_image)
            print(progression_images)
            index = 0
            for item in progression_images:
                shutil.copy(f'data/{item}', 'renders/%s/seq_image_%03d.webp' % (render_id, index))
                resize_file_in_place('renders/%s/seq_image_%03d.webp' % (render_id, index), 1920, 1080)
                index += 1
                if index <= 5 and len(progression_images) < 10:
                    # stop doubling up when it stops changing so much
                    shutil.copy(f'data/{item}', 'renders/%s/seq_image_%03d.webp' % (render_id, index))
                    resize_file_in_place('renders/%s/seq_image_%03d.webp' % (render_id, index), 1920, 1080)
                    index += 1
            shutil.copy(f'data/{ending_image}', f'renders/%s/seq_image_%03d.png' % (render_id, index))
            proc = subprocess.Popen(["ffmpeg", "-y", "-i", "seq_image_%03d.png" % index, "-c:v", "libwebp", "seq_image_%03d.webp" % index], cwd=f"renders/{render_id}")
            proc.communicate()
            resize_file_in_place('renders/%s/seq_image_%03d.webp' % (render_id, index), 1920, 1080)
            index += 1
            shutil.copy(f'data/{ending_image}', f'renders/%s/seq_image_%03d.png' % (render_id, index))
            proc = subprocess.Popen(["ffmpeg", "-y", "-i", "seq_image_%03d.png" % index, "-c:v", "libwebp", "seq_image_%03d.webp" % index], cwd=f"renders/{render_id}")
            proc.communicate()
            resize_file_in_place('renders/%s/seq_image_%03d.webp' % (render_id, index), 1920, 1080)
            index += 1
            while index < 19:
                shutil.copy(f'renders/{render_id}/gen2_text.png', f'renders/%s/seq_image_%03d.png' % (render_id, index))
                proc = subprocess.Popen(["ffmpeg", "-y", "-i", "seq_image_%03d.png" % index, "-c:v", "libwebp", "seq_image_%03d.webp" % index], cwd=f"renders/{render_id}")
                # resize_file_in_place('renders/%s/seq_image_%03d.webp' % (render_id, index), 1920, 1080)
                proc.communicate()
                index += 1
            # final frame is black
            shutil.copy(f'black_frame.webp', 'renders/%s/seq_image_%03d.webp' % (render_id, index))
            index += 1
            cmd = " ".join(["ffmpeg", "-y", "-framerate", "1", "-pattern_type", "glob", "-i", "'*.webp'", "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", "-preset", "slow", "-crf", "18", f"output.mp4"])
            os.system(f"cd renders/{render_id}; {cmd}")
            print('done')
            shutil.move(f'renders/{render_id}/output.mp4', f'clips/{render_id}.mp4')
            query = f"""
                INSERT OR IGNORE INTO clips (content, author_username, author_discriminator, timestamp, render_id, n_stitched)
                VALUES ('{content}', '{author_username}', '{author_discriminator}', '{timestamp}', '{render_id}', 0);
            """;
            # print(query)
            clip_con.execute(query)
            clip_con.commit()
            shutil.rmtree(f'renders/{render_id}')
        if render_id is not None:
            if len(progression_images) <= 3:
                print('not enough progressions logged! three steps would just be choppy')
            if len(progression_images) >= 16:
                print('too many progressions logged, i didnt plan for this')
            query = f"UPDATE endings SET is_clipped = 'TRUE' WHERE render_id = '{render_id}'"
            cur.execute(query)
            con.commit()
        print('waiting')
        sleep(1)
        i += 1

        
                
    print('done')
    return

def resize_file_in_place(fname, desired_width_px, desired_height_px):
    im = Image.open(fname)
    im = resize_to_aspect(im, desired_width_px, desired_height_px)
    im.save(fname)

def resize_to_aspect(in_img, desired_width_px, desired_height_px):
    img_width_px, img_height_px = in_img.size
    aspect = img_width_px / img_height_px
    print(aspect)
    desired_aspect = desired_width_px / desired_height_px
    print(desired_aspect)
    if aspect == desired_aspect:
        print('no-resize-needed')
        return in_img
    elif aspect < desired_aspect:
        print('add to the sides')
        new_width = math.floor(img_width_px * (desired_width_px / desired_height_px) / (img_width_px / img_height_px))
        diff = new_width - img_width_px
        padded = Image.new(in_img.mode, (new_width, img_height_px), (0,0,0))
        padded.paste(in_img, (math.floor(diff / 2), 0))
        print(new_width)
        # padded.save(f'renders/{render_id}/gen3_padded.png')
        return padded
    else:
        print('add to the top')
        new_height = math.floor(img_height_px / (desired_width_px / desired_height_px) * (img_width_px / img_height_px))
        diff = new_height - img_height_px
        padded = Image.new(in_img.mode, (img_width_px, new_height), (0,0,0))
        padded.paste(in_img, (0, math.floor(diff / 2)))
        print(new_height)
        # padded.save(f'renders/{render_id}/gen3_padded.png')
        return padded


if __name__ == '__main__':
    main()
