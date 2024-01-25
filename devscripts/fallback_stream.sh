#!/usr/bin/bash
#
#
cd outdir
while :
do
	echo "Run the stream"
	ffmpeg -re -framerate 1 -stream_loop 40 -i 'technical_difficulties_v1.png' -stream_loop -1 -i audio0000.mp3 -map 0:v -map 1:a -c:v libx264 -r 30 -shortest -b:a 128k -qscale 0 -g 10 -preset fast -crf 38 -f flv rtmp://$STREAM_URL/$STREAM_KEY
	echo "Sleep for 20 seconds"
	sleep 20
done
