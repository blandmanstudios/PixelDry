#!/usr/bin/bash
#
#
while :
do
	echo "Run the stream"
	ffmpeg -re -stream_loop 4 -i 'vid0004.mp4' -stream_loop -1 -i meizong-salt-mines.mp3 -map 0:v -map 1:a -c:v libopenh264 -shortest -b:v 1k -b:a 128k -qscale 0 -g 1 -f flv rtmp://$STREAM_URL/$STREAM_KEY
	echo "Sleep for 10 seconds"
	sleep 5
done
