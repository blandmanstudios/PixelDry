#!/usr/bin/bash
#
#
cd outdir
while :
do
	echo "Run the stream"
	ffmpeg -re -stream_loop 2 -i 't_vid0000.mp4' -stream_loop -1 -i audio0000.mp3 -map 0:v -map 1:a -c:v libopenh264 -shortest -b:v 1k -b:a 128k -qscale 0 -g 90 -f flv rtmp://$STREAM_URL/$STREAM_KEY
	echo "Sleep for 20 seconds"
	sleep 20
done
