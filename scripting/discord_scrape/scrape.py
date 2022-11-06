#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep



API_ENDPOINT = 'https://discord.com/api/v10'

def main():
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    headers={
            'Authorization': f'{params["access_token"]}'
    }
    mjn_chan_id = '989268312036896818'
    found_a_zero = False
    while not found_a_zero:
        resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=50", headers=headers)
        res = resp.json()
        json_formatted_str = json.dumps(res, indent=4)
        # print(json_formatted_str)
        for item in res:
            if (type(item) is not dict):
                continue
            if item['author']['username'] == 'Midjourney Bot':
                status = item['content'].split(' ')[-2:-1][0]
                print(status)
                other_status = item['content'].split(' ')[-1:]
                if '(' in status and '%)' in status:
                    # this message is in progress
                    if '(0%)' in status:
                        print('foundone')
                        message_id = item['id']
                        finished = False
                        prev_filename = None
                        prev_url = None
                        count = 0
                        this_request_hash = None
                        while not finished and count < 1000:
                            resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?around={message_id}&limit=1", headers=headers)
                            res = resp.json()
                            json_formatted_str = json.dumps(res, indent=4)
                            # print(json_formatted_str)
                            for message in res:
                                if 'attachments' in message and len(message['attachments']) > 0 and (this_request_hash is None or this_request_hash in message['attachments'][0]['filename']):
                                    filename = message['attachments'][0]['filename']
                                    url = message['attachments'][0]['url']
                                    this_request_hash = filename.split('_')[-1].split('.')[0]
                                    if (prev_filename != filename and prev_url != url):
                                        print(filename)
                                        print(url)
                                        prev_filename = filename
                                        prev_url = url
                                        if '.png' in filename:
                                            finished = True
                                            print(f'requests_completed={count}')
                                break
                            resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=50", headers=headers)
                            res = resp.json()
                            json_formatted_str = json.dumps(res, indent=4)
                            # print(json_formatted_str)
                            for message in res:
                                if 'attachments' in message and len(message['attachments']) > 0 and (this_request_hash is not None and this_request_hash in message['attachments'][0]['filename']):
                                    filename = message['attachments'][0]['filename']
                                    url = message['attachments'][0]['url']
                                    print(filename)
                                    print(url)
                                    if '.png' in filename:
                                        finished = True
                                        print('FOUND THE PNG')
                            print('inner-sleep')
                            sleep(3)
                            count += 1
        print('outer-sleep')
        sleep(3)


if __name__ == '__main__':
    main()
