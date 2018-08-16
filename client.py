import requests
import untangle
import sys
import sqlite3
import os.path
import datetime
import time
import logging
import random

reload(sys) # just to be sure
sys.setdefaultencoding('utf-8')

import argparse

LOGGER = logging.getLogger("bgg")

def load_collection(user):

    url = "https://www.boardgamegeek.com/xmlapi2/collection?username={}".format(user)

    r = requests.get(url)

    while r.status_code == 202:
        LOGGER.debug("Wait ....")
        time.sleep(1)
        r = requests.get(url)

    conn = sqlite3.connect('cache.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS collection (id INTEGER PRIMARY KEY, name text, minplayers int, maxplayers int, mintime int, maxtime int);
    ''')

    obj = untangle.parse(r.text)
    boardgames = [item for item in obj.items.item if item['subtype'] == "boardgame"]

    for boardgame in boardgames:
        oid = boardgame['objectid']
        if boardgame.status['own'] != "1":
            LOGGER.debug("Not own")
            continue

        name = boardgame.name.cdata

        try:
            c.execute('''
            INSERT INTO collection VALUES (?, ?, 0, 0, 0, 0);
            ''', (oid, name))
        except sqlite3.IntegrityError as error:
            pass

    conn.commit()
    conn.close()

def load_game(id, conn):
    url = "https://www.boardgamegeek.com/xmlapi/" + "boardgame" + "/" + str(id)

    c = conn.cursor()

    c.execute('SELECT * FROM collection WHERE id = ?', (id,))

    game = c.fetchone()

    if game[2] > 0:
        LOGGER.debug("Cache")
        return


    r = requests.get(url)

    obj = untangle.parse(r.text)

    minplayers = obj.boardgames.boardgame.minplayers.cdata
    maxplayers = obj.boardgames.boardgame.maxplayers.cdata

    mintime = obj.boardgames.boardgame.minplaytime.cdata
    maxtime = obj.boardgames.boardgame.maxplaytime.cdata

    categories = [category.cdata for category in obj.boardgames.boardgame.boardgamecategory]

    c.execute('''
    UPDATE collection set minplayers = ?, maxplayers = ?, mintime = ?, maxtime = ? where collection.id = ?;
    ''', (minplayers, maxplayers, mintime, maxtime, id))

    c.execute('''
    UPDATE collection set maxplayers = ? where collection.id = ?;
    ''', (maxplayers, id))

    c.execute('''
    UPDATE collection set mintime = ? where collection.id = ?;
    ''', (mintime, id))

    c.execute('''
    UPDATE collection set maxtime = ? where collection.id = ?;
    ''', (maxtime, id))

def find(players, atime, mintime):
    conn = sqlite3.connect('cache.db')
    c = conn.cursor()

    games = [game[1] for game in c.execute('SELECT  * FROM collection;') if (
        game[2] <= players and
        game[3] >= players and
        game[4] <= atime and
        game[4] >= mintime)]

    print games
    print random.choice(games)


def main():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('-vvv', '--verbose', action='store_true', default=False)
    parser.add_argument('--flush', action='store_true', default=False)
    parser.add_argument('--mintime', type=int, default=0)

    parser.add_argument('user', type=str)
    parser.add_argument('players', type=int)
    parser.add_argument('time', type=int)

    args = parser.parse_args()
    try:
        if args.flush:
            os.remove('cache.db')
    except:
        pass

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not os.path.isfile('cache.db'):
        load_collection(args.user)

    conn = sqlite3.connect('cache.db')
    c = conn.cursor()

    for row in c.execute('SELECT * FROM collection;'):
        LOGGER.info("Load %s", row[1])
        load_game(row[0], conn)
        conn.commit()
    conn.close()

    find(args.players, args.time, args.mintime)

if __name__ == "__main__":
    main()
