#!/usr/bin/env python3

import requests
import yaml
import json
from time import sleep
import sqlite3
import subprocess
import argparse


def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--iterations',
                        '-i',
                        type=int,
                        default=-1,
                        help='number of loop iterations, -1 for infinite')
    args = parser.parse_args()
    con = sqlite3.connect('local_state.db')
    cur = con.cursor()
    i = 0
    while args.iterations < 0 or i < args.iterations:
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
        i += 1

    return


if __name__ == '__main__':
    main()
