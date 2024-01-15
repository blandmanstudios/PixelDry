#!/usr/bin/bash

cd outdir

export DATE=$(date)

echo $DATE
echo $DATE >> date_file_started.txt

# Test to just an output file to verify if network connectivity is the issue
# ffmpeg -re -stream_loop -1 -f concat -safe 0 -i video_list_test30.txt -stream_loop -1 -f concat -safe 0 -i audio_list.txt -map 0:v -map 1:a -c:v libopenh264 -shortest -qscale 0 -g 1 -f flv outputfile.mp4

# Test the actual output stream (to youtube)
ffmpeg -re -stream_loop -1 -f concat -safe 0 -i video_list_test30.txt -stream_loop -1 -f concat -safe 0 -i audio_list.txt -map 0:v -map 1:a -c:v libopenh264 -shortest -qscale 0 -g 1 -f flv rtmp://$STREAM_URL/$STREAM_KEY


