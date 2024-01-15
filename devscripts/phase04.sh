#!/usr/bin/bash

# run once forever
./src/wcdraw/phase04_stream.py -c secure_params.yml -i -1

# run once forever (in dry run mode -> no ffmpeg)
#./src/wcdraw/phase04_stream.py -c secure_params.yml -i -1 --dry-run
