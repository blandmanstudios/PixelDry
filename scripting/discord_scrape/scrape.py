#!/usr/bin/env python3

import requests
import yaml



API_ENDPOINT = 'https://discord.com/api/v10'

def main():
    with open('secure_params.yml', 'r') as file:
        params = yaml.safe_load(file)
    headers={
            'Authorization': f'{params["access_token"]}'
    }
    message_id = '1038669289051410503'
    channel_id = '1022686221970985084'
    resp = requests.get(f"{API_ENDPOINT}/channels/{channel_id}/messages?limit=50", headers=headers)
    print(resp.json())


if __name__ == '__main__':
    main()
