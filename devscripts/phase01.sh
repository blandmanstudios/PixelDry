#!/usr/bin/bash

# ./src/wpixdry/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i 1
# ./src/wpixdry/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 -i 20

# Run forever
# ./src/wpixdry/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 8 18 -i -1

# Run on repeat logging crashes to a specific file
for i in {1..30}
do
	echo "Run $i $(date)"
	echo "Run $i $(date)" >> phase01_output.txt
	./src/wpixdry/phase01_find_prompts.py -c secure_params.yml -l 24 54 84 8 18 -i -1 >> phase01_output.txt 2>&1
	echo -e "\n\n" >> phase01_output.txt
done
