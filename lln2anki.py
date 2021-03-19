#! /usr/bin/env python3

# ©2021 Jason Lunz <znull@github.com>

import json
import sys
import re
from argparse import ArgumentParser, FileType
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

def find_media_dir():
    md = path.expanduser('~/.local/share/Anki2/User 1/collection.media')
    assert path.isdir(md)
    return md

class Note:

    MEDIA_DIR = find_media_dir()
    MAX_WORDS = 0

    def __init__(self, word):
        context = word['context']
        phrase = context['phrase']
        ref = phrase['reference']
        subtok = phrase['subtitleTokens']
        word_text = word['word']['text']

        self.key = '{}:{}'.format(ref['movieId'], ref['subtitleIndex'])

        for st in chain(*subtok.values()):
            if st['form']['text'] == word_text:
                part_of_speech = parts_of_speech[st['pos']]
                break
        else:
            raise ValueError('{} not found in forms'.format(word_text))

        拼音 = ' '.join(word['word']['pinyin'])
        意思 = '; '.join(word['wordTranslationsArr'])

        self.words = [ (word_text, 拼音, 意思, part_of_speech) ]

        forms = list(map(lambda st: st['form'], subtok['1']))
        sentence = ''.join(map(lambda f: f['text'], forms))
        sentence = re.sub('\s+', ' ', sentence)
        self.sentence = sentence
        self.sentence_拼音 = ' '.join(chain(*map(lambda f: f.get('pinyin') or '', forms)))
        self.sentence_意思 = re.sub('\s+', ' ', phrase['hTranslations']['1'])

        self.files = [
            media(phrase['audio'], ref),
            media(phrase['thumb_prev'], ref, '_prev'),
            media(phrase['thumb_next'], ref, '_next'),
        ]
        self.audio = '[sound:{}]'.format(self.files[0][0])
        self.image1 = '<img src="{}"/>'.format(self.files[1][0])
        self.image2 = '<img src="{}"/>'.format(self.files[2][0])

    def merge(self, other):
        assert self.key == other.key
        assert self.sentence == other.sentence
        assert self.sentence_拼音 == other.sentence_拼音
        assert self.sentence_意思 == other.sentence_意思
        self.words.extend(other.words)
        Note.MAX_WORDS = max(Note.MAX_WORDS, len(self.words))

    def tsv(self):
        data = [
            self.key,
            self.sentence,
            self.sentence_拼音,
            self.sentence_意思,
            self.audio,
            self.image1,
            self.image2,
        ]
        for word in self.words:
            data.extend(word)

        # pad every line to the same number of fields
        data += [''] * 4 * (Note.MAX_WORDS - len(self.words))

        return '\t'.join(data)

    def export(self, outfh):
        bytes_written = 0
        for name, data in self.files:
            with open(path.join(Note.MEDIA_DIR, name), 'wb') as fh:
                fh.write(data)
            bytes_written += len(data)

        print(self.tsv(), file=outfh)

        return len(self.files), bytes_written

    def fields(self):
        return chain(enumerate(self.words), [
            ('key', self.key),
            ('sentence', self.sentence),
            ('sentence_pinyin', self.sentence_拼音),
            ('sentence_meaning', self.sentence_意思),
            ('audio', self.audio),
            ('image1', self.image1),
            ('image2', self.image2),
        ])

    def dump(self, fh):
        print('\n'.join(map(str, self.fields())) + '\n', file=fh)

def media(data, ref, suffix=''):
    data = data['dataURL']
    tag, bits = data.split(',', 1)
    assert tag.startswith('data:')
    tag = tag[5:].split(';', 1)[0]
    bits = b64decode(bits)

    name = '{}_{}'.format(ref['title'], ref['subtitleIndex'])
    name = re.sub('\W+', '_', name).lower() + suffix + ext[tag]

    return name, bits

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('lln_json', metavar='lln.json', type=FileType('r'),
        help='Language Learning for Netflix json export file')
    Args = parser.parse_args()

    lln_data  = json.load(Args.lln_json)

    notes = {}
    for word in lln_data:
        note = Note(word)
        if note.key in notes:
            notes[note.key].merge(note)
        else:
            notes[note.key] = note

    files = bytes_written = 0
    for i, note in enumerate(notes.values()):
        f, b = note.export(sys.stdout)
        files += f
        bytes_written += b

        if Args.verbose:
            print(i+1, file=sys.stderr)
            note.dump(sys.stderr)

    word_count = sum(len(n.words) for n in notes.values())
    print('exported {} notes with {} cards'.format(len(notes), word_count), file=sys.stderr)
    print('wrote {} bytes of media to {} files'.format(bytes_written, files), file=sys.stderr)
