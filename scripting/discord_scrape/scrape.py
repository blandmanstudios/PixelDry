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
        resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?limit=10", headers=headers)
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
                        while not finished and count < 1000:
                            resp = requests.get(f"{API_ENDPOINT}/channels/{mjn_chan_id}/messages?around={message_id}&limit=1", headers=headers)
                            res = resp.json()
                            json_formatted_str = json.dumps(res, indent=4)
                            # print(json_formatted_str)
                            for message in res:
                                if 'attachments' in message and len(message['attachments']) > 0:
                                    filename = message['attachments'][0]['filename']
                                    url = message['attachments'][0]['url']
                                    if (prev_filename != filename and prev_url != url):
                                        print(filename)
                                        print(url)
                                        prev_filename = filename
                                        prev_url = url
                                        # Note, there is some trouble getting
                                        # the png, sometimes it wont get an
                                        # image, sometimes it will get the wrong
                                        # image, its probably because of the
                                        # message "around" trick i'm doing above
                                        # we should be doing some checking but
                                        # also figure out if the message id is
                                        # changing
                                        # it does, when they get to the final
                                        # png image they delete the old message
                                        # and create a new message with a new
                                        # message id
                                        # so i need both, i need to be filtering
                                        # on content (or on image_id) to make
                                        # sure I'm looking at the thing i want
                                        # but also i need to add a new search
                                        # that will search new messages for
                                        # my png with the right (either content
                                        # or) message_id
                                        if '.png' in filename:
                                            finished = True
                                            print(f'requests_completed={count}')
                                break
                            count += 1
        print(0.5)


if __name__ == '__main__':
    main()
