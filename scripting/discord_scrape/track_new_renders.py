#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import argparse



API_ENDPOINT = 'https://discord.com/api/v10'

def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--iterations',
                        '-i',
                        type=int,
                        default=-1,
                        help='number of loop iterations, -1 for infinite')
    args = parser.parse_args()
    chan_id_map = dict()
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    headers={
            'Authorization': f'{params["access_token"]}'
    }
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    speed_factor = 4
    i = 0
    while args.iterations < 0 or i < args.iterations:
        query = "SELECT * from beginnings WHERE processed = 'FALSE' AND num_tries < 100 ORDER BY num_tries ASC LIMIT 1"
        cur.execute(query)
        for beginning_id, channel_id, message_id, content, author_username, author_discriminator, timestamp, processed, num_tries in cur.fetchall():
            resp = requests.get(f"{API_ENDPOINT}/channels/{channel_id}/messages?limit=1&around={message_id}", headers=headers)
            res = resp.json()
            json_formatted_str = json.dumps(res, indent=4)
            for item in res:
                if '**' not in item['content']:
                    continue
                found_content = item['content'].split("**")[1]
                found_timestamp = item['timestamp']
                if found_content == content and found_timestamp == timestamp and 'attachments' in item and len(item['attachments']) > 0:
                    print('we found the in-progress match')
                    attachment = item['attachments'][0]
                    filename = attachment['filename']
                    url = attachment['url']
                    render_id = filename.rstrip('.webp').split('_')[-1]
                    percentage = int(filename.rstrip('.webp').split('_')[-2])
                    query = f"""
                        SELECT * from progressions WHERE message_id = '{message_id}' AND channel_id = '{channel_id}' and percentage = {percentage}
                    """;
                    # print(query)
                    if len(cur.execute(query).fetchall()) == 0:
                        query = f"""
                            INSERT OR IGNORE INTO progressions (message_id, channel_id, content, author_username, author_discriminator, timestamp, percentage, render_id, beginning_id, filename, url, is_downloaded)
                            VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', {percentage}, '{render_id}', '{beginning_id}', '{filename}', '{url}', 'FALSE');
                        """;
                        # print(query)
                        cur.execute(query)
                        con.commit()

            query = f"UPDATE beginnings SET num_tries = '{num_tries + 1}' WHERE beginning_id = '{beginning_id}' AND processed='FALSE'"
            cur.execute(query)
            con.commit()
            sleep(0)
        print('waiting')
        sleep(1.0 / speed_factor)
        i += 1
    
    print('hi')
    return


if __name__ == '__main__':
    main()
