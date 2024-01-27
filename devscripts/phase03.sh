#!/usr/bin/bash

# run once
# ./src/wpixdry/phase03_render_clips.py -c secure_params.yml -i 1

# run once, forever
# ./src/wpixdry/phase03_render_clips.py -c secure_params.yml -i -1

# Run on repeat logging crashes to a specific file
for i in {1..30}
do
	echo "Run $i $(date)"
	echo "Run $i $(date)" >> phase03_output.txt
	./src/wpixdry/phase03_render_clips.py -c secure_params.yml -i -1 >> phase03_output.txt 2>&1
	echo -e "\n\n" >> phase03_output.txt
done
