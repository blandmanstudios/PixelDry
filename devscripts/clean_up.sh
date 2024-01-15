#!/usr/bin/bash

echo $1
echo $2
mariadb --user=$1 --password=$2 wcddb --execute "drop table render_stage; drop table prompt;"
rm data/*.webp
rm phase01_output.txt
rm phase02_output.txt


# To flush the history of what you've streamed in the past do this
# MySQL
# delete from render_output_event where id > 0;


# To delete all the output renders and evidence that you've rendered them
# bash
# rm outdir/prompt_*_output.mp4
# mysql
# update prompt set local_video_path=NULL where local_video_path IS NOT NULL;


