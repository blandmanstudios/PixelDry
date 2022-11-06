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
    found_a_zero = False
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    query_string = "CREATE TABLE IF NOT EXISTS beginnings (beginning_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), processed INTEGER, unique (message_id, channel_id));"
    cur.execute(query_string)
    query_string = "CREATE TABLE IF NOT EXISTS endings (ending_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), render_id varchar(100), filename text, url text, unique (message_id, channel_id));"
    cur.execute(query_string)
    # found = []
    for i in range(100):
        resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=10", headers=headers)
        res = resp.json()
        json_formatted_str = json.dumps(res, indent=4)
        for item in res:
            if (type(item) is not dict):
                continue
            if item['author']['username'] == 'Midjourney Bot':
                status = item['content'].split(' ')[-2:-1][0]
                print(status)
                if 'rate' in status:
                    print(item)
                    return
                other_status = item['content'].split(' ')[-1:]
                if '(' in status and '%)' in status:
                    # this message is in progress
                    if '(0%)' in status:
                        print('foundone')
                        print(item)
                        content = item['content'].split("**")[1]
                        author_username = item['mentions'][0]['username']
                        author_discriminator = item['mentions'][0]['discriminator']
                        timestamp = item['timestamp']
                        print(content)
                        message_id = item['id']
                        channel_id = mjn_chan_id
                        # if (message_id, channel_id) not in found:
                        #     found.append((message_id, channel_id))
                        query = f"""
                            INSERT OR IGNORE INTO beginnings (message_id, channel_id, content, author_username, author_discriminator, timestamp, processed)
                            VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', 'FALSE');
                        """;
                        # print(query)
                        con.execute(query)
                        con.commit()
                else:
                    print('found a done')
                    content = item['content'].split("**")[1]
                    author_username = item['mentions'][0]['username']
                    author_discriminator = item['mentions'][0]['discriminator']
                    timestamp = item['timestamp']
                    message_id = item['id']
                    channel_id = mjn_chan_id
                    if 'attachments' in item and len(item['attachments']) > 0:
                        attachment = item['attachments'][0]
                        filename = attachment['filename']
                        url = attachment['url']
                        if '.png' in filename:
                            render_id = filename.rstrip('.png').split('_')[-1]
                            print(render_id)
                            query = f"""
                                INSERT OR IGNORE INTO endings (message_id, channel_id, content, author_username, author_discriminator, timestamp, render_id, filename, url)
                                VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', '{render_id}', '{filename}', '{url}');
                            """;
                            # print(query)
                            con.execute(query)
                            con.commit()
        # print(found)
        sleep(1)
    print('done')
    return


if __name__ == '__main__':
    main()
