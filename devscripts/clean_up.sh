#!/usr/bin/bash

echo $1
echo $2
mariadb --user=$1 --password=$2 wcddb --execute "drop table render_stage; drop table prompt;"
rm data/*.webp
rm phase01_output.txt
rm phase02_output.txt
