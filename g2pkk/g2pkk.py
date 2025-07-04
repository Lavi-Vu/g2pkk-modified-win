# -*- coding: utf-8 -*-


import os, re, platform, sys, importlib
import subprocess

import nltk
from jamo import h2j
from nltk.corpus import cmudict

# For further info. about cmu dict, consult http://www.speech.cs.cmu.edu/cgi-bin/cmudict.
try:
    nltk.data.find('corpora/cmudict.zip')
except LookupError:
    nltk.download('cmudict')

from g2pkk.special import jyeo, ye, consonant_ui, josa_ui, vowel_ui, jamo, rieulgiyeok, rieulbieub, verb_nieun, balb, palatalize, modifying_rieul
from g2pkk.regular import link1, link2, link3, link4
from g2pkk.utils import annotate, compose, group, gloss, parse_table, get_rule_id2text
from g2pkk.english import convert_eng
from g2pkk.numerals import convert_num


class G2p(object):
    def __init__(self):
        self.check_mecab()
        self.mecab = self.get_mecab()
        self.table = parse_table()

        self.cmu = cmudict.dict() # for English

        self.rule2text = get_rule_id2text() # for comments of main rules
        self.idioms_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idioms.txt")

    def load_module_func(self, module_name):
        tmp = __import__(module_name, fromlist=[module_name])
        return tmp

    def check_mecab(self):
        if platform.system()=='Windows':
           pass
        else:
            spam_spec = importlib.util.find_spec("mecab")
            non_found = spam_spec is None
            if non_found:
                print(f'you have to install python-mecab-ko. install it...')
                p = subprocess.Popen([sys.executable, "-m", "pip", "install", 'python-mecab-ko'])
                p.wait()


    def get_mecab(self):
        if platform.system() == 'Windows':
            try:
                    import MeCab
                    return MeCab.Tagger()
            except Exception as e:
                raise print(f'you have to install mecab. "pip install mecab"')
        else:
            try:
                m = self.load_module_func('mecab')
                return m.MeCab()
            except Exception as e:
                print(f'you have to install python-mecab-ko. "pip install python-mecab-ko"')


    def idioms(self, string, descriptive=False, verbose=False):
        '''Process each line in `idioms.txt`
        Each line is delimited by "===",
        and the left string is replaced by the right one.
        inp: input string.
        descriptive: not used.
        verbose: boolean.

        >>> idioms("지금 mp3 파일을 다운받고 있어요")
        지금 엠피쓰리 파일을 다운받고 있어요
        '''
        rule = "from idioms.txt"
        out = string

        with open(self.idioms_path, 'r', encoding="utf8") as f:
            for line in f:
                line = line.split("#")[0].strip()
                if "===" in line:
                    str1, str2 = line.split("===")
                    out = re.sub(str1, str2, out)
            gloss(verbose, out, string, rule)

        return out

    def __call__(self, string, descriptive=False, verbose=False, group_vowels=False, to_syl=True):
        '''Main function
        string: input string
        descriptive: boolean.
        verbose: boolean
        group_vowels: boolean. If True, the vowels of the identical sound are normalized.
        to_syl: boolean. If True, hangul letters or jamo are assembled to form syllables.

        For example, given an input string "나의 친구가 mp3 file 3개를 다운받고 있다",
        STEP 1. idioms
        -> 나의 친구가 엠피쓰리 file 3개를 다운받고 있다

        STEP 2. English to Hangul
        -> 나의 친구가 엠피쓰리 파일 3개를 다운받고 있다

        STEP 3. annotate
        -> 나의/J 친구가 엠피쓰리 파일 3개/B를 다운받고 있다

        STEP 4. Spell out arabic numbers
        -> 나의/J 친구가 엠피쓰리 파일 세개/B를 다운받고 있다

        STEP 5. decompose
        -> 나의/J 친구가 엠피쓰리 파일 세개/B를 다운받고 있다

        STEP 6-9. Hangul
        -> 나의 친구가 엠피쓰리 파일 세개를 다운받꼬 읻따
        '''
        # 1. idioms
        string = self.idioms(string, descriptive, verbose)

        # 2 English to Hangul
        string = convert_eng(string, self.cmu)

        # 3. annotate
        string = annotate(string, self.mecab)


        # 4. Spell out arabic numbers
        string = convert_num(string)

        # 5. decompose
        inp = h2j(string)

        # 6. special
        for func in (jyeo, ye, consonant_ui, josa_ui, vowel_ui, \
                     jamo, rieulgiyeok, rieulbieub, verb_nieun, \
                     balb, palatalize, modifying_rieul):
            inp = func(inp, descriptive, verbose)
        inp = re.sub("/[PJEB]", "", inp)

        # 7. regular table: batchim + onset
        for str1, str2, rule_ids in self.table:
            _inp = inp
            inp = re.sub(str1, str2, inp)

            if len(rule_ids)>0:
                rule = "\n".join(self.rule2text.get(rule_id, "") for rule_id in rule_ids)
            else:
                rule = ""
            gloss(verbose, inp, _inp, rule)

        # 8 link
        for func in (link1, link2, link3, link4):
            inp = func(inp, descriptive, verbose)

        # 9. postprocessing
        if group_vowels:
            inp = group(inp)

        if to_syl:
            inp = compose(inp)
        return inp

if __name__ == "__main__":
    g2p = G2p()
    g2p("나의 친구가 mp3 file 3개를 다운받고 있다")
