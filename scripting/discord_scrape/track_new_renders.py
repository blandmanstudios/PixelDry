#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3



API_ENDPOINT = 'https://discord.com/api/v10'

def main():
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    headers={
            'Authorization': f'{params["access_token"]}'
    }
    mjn_chan_id = '989268312036896818'
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    query_string = "CREATE TABLE IF NOT EXISTS progressions (progression_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), percentage varchar(100), render_id varchar(100), beginning_id INTEGER, filename text, url text, unique (message_id, channel_id, percentage), FOREIGN KEY(beginning_id) REFERENCES beginnings(beginning_id));"
    cur.execute(query_string)
    for i in range(200):
        query = "SELECT * from beginnings WHERE processed = 'FALSE' AND num_tries < 200"
        cur.execute(query)
        for beginning_id, channel_id, message_id, content, author_username, author_discriminator, timestamp, processed, num_tries in cur.fetchall():
            resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=1&around={message_id}", headers=headers)
            res = resp.json()
            json_formatted_str = json.dumps(res, indent=4)
            for item in res:
                found_content = item['content'].split("**")[1]
                found_timestamp = item['timestamp']
                if found_content == content and found_timestamp == timestamp and 'attachments' in item and len(item['attachments']) > 0:
                    print('we found the in-progress match')
                    attachment = item['attachments'][0]
                    filename = attachment['filename']
                    url = attachment['url']
                    render_id = filename.rstrip('.webp').split('_')[-1]
                    percentage = filename.rstrip('.webp').split('_')[-2]
                    query = f"""
                        SELECT * from progressions WHERE message_id = '{message_id}' AND channel_id = '{channel_id}' and percentage = '{percentage}'
                    """;
                    # print(query)
                    if len(cur.execute(query).fetchall()) == 0:
                        query = f"""
                            INSERT OR IGNORE INTO progressions (message_id, channel_id, content, author_username, author_discriminator, timestamp, percentage, render_id, beginning_id, filename, url)
                            VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', '{percentage}', '{render_id}', '{beginning_id}', '{filename}', '{url}');
                        """;
                        # print(query)
                        cur.execute(query)
                        con.commit()

            query = f"UPDATE beginnings SET num_tries = '{num_tries + 1}' WHERE beginning_id = '{beginning_id}' AND processed='FALSE'"
            cur.execute(query)
            con.commit()
            sleep(1.0)
        print('waiting')
        sleep(1.0)
    
    print('hi')
    return


if __name__ == '__main__':
    main()
