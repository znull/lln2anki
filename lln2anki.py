#! /usr/bin/env python3

import json
import sys
import re
from base64 import b64decode
from itertools import chain
from os import path

parts_of_speech = {
    '_': '',
    'ADJ': 'adjective',
    'AUX': 'auxiliary verb',
    'CCONJ': 'coordinating conjunction',
    'NOUN': 'noun',
    'PROPN': 'proper noun',
    'VERB': 'verb',
}

ext = {
    'audio/mpeg': '.mp3',
    'image/jpeg': '.jpeg',
}

def media(ref, data, suffix=''):
    tag, bits = data.split(',', 1)
    assert tag.startswith('data:')
    tag = tag[5:].split(';', 1)[0]
    bits = b64decode(bits)

    name = '{}_{}'.format(ref['title'], ref['subtitleIndex'])
    name = re.sub('\W+', '_', name).lower() + suffix + ext[tag]

    return name, bits

def tsv(card):
    return '\t'.join(v for k, v in sorted(card.items()))

def word_to_card(word):
    text = word['word']['text']
    context = word['context']
    phrase = context['phrase']
    ref = phrase['reference']
    subtok = phrase['subtitleTokens']

    forms = list(map(lambda st: st['form'], subtok['1']))
    pinyin = ' '.join(chain(*map(lambda f: f.get('pinyin') or '', forms)))
    sentence = ''.join(map(lambda f: f['text'], forms))
    sentence = re.sub('\s+', ' ', sentence)
    meaning = re.sub('\s+', ' ', phrase['hTranslations']['1'])

    mp3name, audio = media(ref, phrase['audio']['dataURL'])
    imgp_name, img_prev = media(ref, phrase['thumb_prev']['dataURL'], '_prev')
    imgn_name, img_next = media(ref, phrase['thumb_next']['dataURL'], '_next')

    card = {
        'a.key': '{}:{}:{}'.format(ref['movieId'], ref['subtitleIndex'], context['wordIndex']),
        'b.simplified': text,
        'c.pinyin.1': ' '.join(word['word']['pinyin']),
        'd.meaning': '; '.join(word['wordTranslationsArr']),
        'e.sentence': sentence,
        'f.sentence.pinyin': pinyin,
        'g.sentence.meaning': meaning,
        'h.audio': '[sound:{}]'.format(mp3name),
        'i.image.1': '<img src="{}"/>'.format(imgp_name),
        'j.image.2': '<img src="{}"/>'.format(imgn_name),
        'k.pos': '',
    }
    for st in chain(*subtok.values()):
        if st['form']['text'] == text:
            card['k.pos'] = parts_of_speech[st['pos']]
            break

    files = {
        mp3name: audio,
        imgp_name: img_prev,
        imgn_name: img_next,
    }
    return card, files.items()

def dump_files(files):
    media_dir = path.expanduser('~/.local/share/Anki2/User 1/collection.media')
    assert path.isdir(media_dir)
    for name, data in files:
        with open(path.join(media_dir, name), 'wb') as fh:
            fh.write(data)
            print('wrote {}'.format(name), file=sys.stderr)

export = json.load(sys.stdin)
for i, word in enumerate(export):
    #print(i, file=sys.stderr)
    card, files = word_to_card(word)
    print(tsv(card))
    dump_files(files)

    #print('\n'.join(map(str, sorted(card.items()))))
    #print()
