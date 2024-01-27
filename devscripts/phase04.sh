#!/usr/bin/bash

# run once forever
# ./src/wpixdry/phase04_stream.py -c secure_params.yml -i -1

# run once forever (in dry run mode -> no ffmpeg)
# ./src/wpixdry/phase04_stream.py -c secure_params.yml -i -1 --dry-run
#
# Run on repeat logging crashes to a specific file
for i in {1..30}
do
	echo "Run $i $(date)"
	echo "Run $i $(date)" >> phase04_output.txt
	./src/wpixdry/phase04_stream.py -c secure_params.yml -i -1 >> phase04_output.txt 2>&1
	echo -e "\n\n" >> phase04_output.txt
done
