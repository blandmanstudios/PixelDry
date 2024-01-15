#!/usr/bin/env python3

import os
from PIL import Image, ImageDraw, ImageFont


def main():
    dirname = "workdir/scripting"
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    videos_to_generate = 30
    images_per_video = 20
    for i in range(videos_to_generate):
        for j in range(images_per_video):
            total_seconds = (i * images_per_video) + j
            minutes = total_seconds / 60
            seconds = total_seconds % 60
            generate_image(
                "vid%02d" % i,
                "second%02d" % j,
                "predicted_time %02d:%02d" % (minutes, seconds),
                f"{dirname}/seq_%03d_frame_%03d.webp" % (i, j),
            )
    for i in range(videos_to_generate):
        output_video_path = "t_vid%04d.mp4" % i
        cmd = " ".join(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "1",
                "-pattern_type",
                "glob",
                "-i",
                "'seq_%03d_frame_*.webp'" % i,
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
                output_video_path,
            ]
        )
        os.system(f"cd {dirname}; {cmd}")
    for item in os.listdir(dirname):
        if ".webp" in item and "seq" in item:
            os.remove(dirname + "/" + item)
    for item in os.listdir(dirname):
        if "t_vid" in item and ".mp4" in item:
            os.rename(dirname + '/' + item, 'outdir/' + item)
    pass


def generate_image(text, subtitle, other_string, outfile):
    img = Image.new(mode="RGBA", size=(1920, 1080), color=(0, 0, 0))
    myFontLarge = ImageFont.truetype("FreeMonoBold.ttf", 120)
    myFontSmall = ImageFont.truetype("FreeMonoBold.ttf", 60)
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), text, font=myFontLarge)
    draw.text((100, 400), subtitle, font=myFontSmall)
    draw.text((100, 600), other_string, font=myFontSmall)
    # img.show()
    img.save(outfile)
    pass


if __name__ == "__main__":
    main()
