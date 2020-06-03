from flask import Flask, Response, render_template
from flask_caching import Cache
import uuid
import random
import collections
import json
import os
import copy

app = Flask(__name__)

# Cacheインスタンスの作成
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 2,
})


@app.route('/')
def homepage():
    return render_template('index.html')


# create the game group
@app.route('/create/<nickname>')
def create_game(nickname):
    game = {
        'status': 'waiting',
        'players': []}
    player = {}

    gameid = str(uuid.uuid4())
    game['gameid'] = gameid
    player['playerid'] = gameid
    player['nickname'] = nickname
    game['players'].append(player)

    app.logger.debug(gameid)
    app.logger.debug(game)
    cache.set(gameid, game)
    return gameid


# re:wait the game
@app.route('/<gameid>/waiting')
def waiting_game(gameid):
    game = cache.get(gameid)
    game['status'] = 'waiting'
    cache.set(gameid, game)
    return 'reset game status'


# join the game
@app.route('/<gameid>/join')
@app.route('/<gameid>/join/<nickname>')
def join_game(gameid, nickname='default'):
    game = cache.get(gameid)
    if game['status'] == 'waiting':
        player = {}

        playerid = str(uuid.uuid4())
        player['playerid'] = playerid
        if nickname == 'default':
            player['nickname'] = playerid
        else:
            player['nickname'] = nickname
        game['players'].append(player)

        cache.set(gameid, game)
        return playerid + ' ,' + player['nickname'] + ' ,' + game['status']
    else:
        return 'Already started'


# processing the game
@app.route('/<gameid>/start')
def start_game(gameid):
    game = cache.get(gameid)
    game['status'] = 'started'

    game['stocks'] = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    random.shuffle(game['stocks'])

    for player in game['players']:
        player['holdcards'] = list(range(1, 16))
        player['pullcard'] = -999
        player['score'] = 0

    game['openedcard'] = game['stocks'].pop(0)

    cache.set(gameid, game)
    return 'ok'


# next to player the game
@app.route('/<gameid>/open')
def open_cards(gameid):
    game = cache.get(gameid)

    game['status'] =  'open'

    for player in game['players']:
        player['diff'] = 0

    pulledcards = [d.get('pullcard') for d in game['players']]

    if game['openedcard'] >= 0:
        s_pulledcards = sorted(pulledcards, reverse=True)
        c = collections.Counter(s_pulledcards)
    else:
        s_pulledcards = sorted(pulledcards)
        c = collections.Counter(s_pulledcards)

    if c[s_pulledcards[0]] > 1:
        if c[s_pulledcards[0]] != len(s_pulledcards):
            getnumber = s_pulledcards[c[s_pulledcards[0]]]
            pIdx = pulledcards.index(getnumber)

            player = game['players'][pIdx]
            player['score'] += game['openedcard']
            player['diff'] = game['openedcard']
    else:
        getnumber = s_pulledcards[0]
        pIdx = pulledcards.index(getnumber)

        player = game['players'][pIdx]
        player['score'] += game['openedcard']
        player['diff'] = game['openedcard']

    cache.set(gameid, game)
    return 'ok'


# next to player the game
@app.route('/<gameid>/next')
def processing_game(gameid):
    game = cache.get(gameid)

    game['openedcard'] = game['stocks'].pop(0)
    game['status'] = 'started'

    for player in game['players']:
        player['pullcard'] = -999

    players = game['players']

    cache.set(gameid, game)
    return 'ok'


# set the card on the line
@app.route('/<gameid>/<clientid>/set/<int:cardnum>')
def setcard_game(gameid, clientid, cardnum):
    game = cache.get(gameid)
    player = [player for player in game['players'] if player['playerid'] == clientid][0]
    player['pullcard'] = cardnum
    # for cId, pullcard in enumerate(players['holdcards']):
    #     if players['holdcards'][cId] == cardnum:
    #         players['holdcards'].pull(cId)

    player['holdcards'].remove(cardnum)

    cache.set(gameid, game)
    return 'ok'


# all status the game
@app.route('/<gameid>/status')
def game_status(gameid):
    game = cache.get(gameid)

    return json.dumps(game)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
