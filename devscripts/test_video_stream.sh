#!/usr/bin/bash

cd outdir

export DATE=$(date)

echo $DATE
echo $DATE >> date_file_started.txt


ffmpeg -re -stream_loop -1 -f concat -safe 0 -i video_list_test30.txt -stream_loop -1 -f concat -safe 0 -i audio_list.txt -map 0:v -map 1:a -c:v libopenh264 -shortest -qscale 0 -g 1 -f flv rtmp://$STREAM_URL/$STREAM_KEY


