#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import subprocess


def main():
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    for i in range(60*60 * 4):
        query = "select filename, url from endings WHERE is_downloaded = 'FALSE';"
        cur.execute(query)
        for filename, url in cur.fetchall():
            pipe = subprocess.Popen(["curl",url,"-o",f"data/{filename}"])
            out_value = pipe.communicate()
            print(out_value)
            query = f"UPDATE endings SET is_downloaded = 'TRUE' WHERE filename='{filename}' and url = '{url}'"
            cur.execute(query)
            con.commit()
        query = "select filename, url from progressions WHERE is_downloaded = 'FALSE';"
        cur.execute(query)
        for filename, url in cur.fetchall():
            pipe = subprocess.Popen(["curl",url,"-o",f"data/{filename}"])
            out_value = pipe.communicate()
            print(out_value)
            query = f"UPDATE progressions SET is_downloaded = 'TRUE' WHERE filename='{filename}' and url = '{url}'"
            cur.execute(query)
            con.commit()
        print('waiting for new images')
        sleep(1)

    return


if __name__ == '__main__':
    main()
