#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import argparse



API_ENDPOINT = 'https://discord.com/api/v10'

def main():
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    headers={
            'Authorization': f'{params["access_token"]}'
    }
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--channel',
                        '-c',
                        type=int,
                        default=24,
                        help='newbie discord channel to crawl')
    args = parser.parse_args()
    chan_id_map = dict()
    chan_id_map[24] = '989268312036896818'
    chan_id_map[54] = '997260995883966464'
    chan_id_map[84] = '997271660900126801'
    mjn_chan_id = chan_id_map[args.channel]
    found_a_zero = False
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    query_string = "CREATE TABLE IF NOT EXISTS beginnings (beginning_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), processed INTEGER, num_tries INTEGER, unique (message_id, channel_id));"
    cur.execute(query_string)
    query_string = "CREATE TABLE IF NOT EXISTS endings (ending_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), render_id varchar(100), filename text, url text, beginning_id INTEGER, is_downloaded INTEGER, is_clipped INTEGER, unique (message_id, channel_id), FOREIGN KEY(beginning_id) REFERENCES beginnings(beginning_id));"
    cur.execute(query_string)
    query_string = "CREATE TABLE IF NOT EXISTS progressions (progression_id INTEGER PRIMARY KEY, channel_id varchar(100), message_id varchar(100), content TEXT, author_username varchar(100), author_discriminator varchar(100), timestamp varchar(100), percentage int, render_id varchar(100), beginning_id INTEGER, filename text, url text, is_downloaded INTEGER, unique (message_id, channel_id, percentage), FOREIGN KEY(beginning_id) REFERENCES beginnings(beginning_id));"
    cur.execute(query_string)
    # found = []
    for i in range(60*60):
        resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=100", headers=headers)
        res = resp.json()
        json_formatted_str = json.dumps(res, indent=4)
        for item in res:
            if (type(item) is not dict):
                continue
            if item['author']['username'] == 'Midjourney Bot':
                if '**' not in item['content']:
                    continue
                if 'https' in item['content']:
                    # midjourney wont proc things with broken links
                    # but it will proc good links, i'll just skip this edge case
                    # cuz i dont want to have to check if the job gets stuck
                    # at 0%
                    continue
                if "'" in item['content']:
                    # skip things containing commas cuz it breaks sql
                    continue
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
                            INSERT OR IGNORE INTO beginnings (message_id, channel_id, content, author_username, author_discriminator, timestamp, processed, num_tries)
                            VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', 'FALSE', '0');
                        """;
                        # print(query)
                        con.execute(query)
                        con.commit()
                else:
                    # print('found a done')
                    content = item['content'].split("**")[1]
                    if len(item['mentions']) == 0:
                        continue
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
                            query = f"""
                                select render_id, progressions.beginning_id FROM progressions WHERE render_id = '{render_id}' LIMIT 1;
                            """
                            cur.execute(query)
                            for sql_render_id, sql_beginning_id in cur.fetchall():
                                query = f"UPDATE beginnings SET processed = 'TRUE' WHERE beginning_id = '{sql_beginning_id}' AND processed='FALSE'"
                                cur.execute(query)
                                con.commit()
                                query = f"""
                                    INSERT OR IGNORE INTO endings (message_id, channel_id, content, author_username, author_discriminator, timestamp, render_id, filename, url, beginning_id, is_downloaded, is_clipped)
                                    VALUES ('{message_id}', '{channel_id}', '{content}', '{author_username}', '{author_discriminator}', '{timestamp}', '{render_id}', '{filename}', '{url}', '{sql_beginning_id}', 'FALSE', 'FALSE');
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
