#!/usr/bin/bash

# ./src/wcdraw/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i 1
# ./src/wcdraw/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i 20

# Run forever
# ./src/wcdraw/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i -1


for i in {1..200}
do
	echo "Run $i"
	echo "Run $i" >> phase01_output.txt
	./src/wcdraw/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i -1 >> phase01_output.txt 2>&1
	echo -e "\n\n" >> phase01_output.txt
done
