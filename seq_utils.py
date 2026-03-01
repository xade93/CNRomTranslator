#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sequence / numeral utilities (separately toggleable, adhoc heuristics).

This module contains functions for extracting sequel/number tokens,
converting Chinese/Roman numerals, and performing sequence-aware
normalization. Keep heuristics here so they can be enabled/disabled
from the main script.
"""
import re

_CN_NUM_MAP = {'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}


def chinese_numeral_to_int(token: str):
    token = token.strip()
    if not token:
        return None
    if token.isdigit():
        return int(token)
    if token == '十':
        return 10
    if '十' in token:
        parts = token.split('十')
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ''
        total = 0
        if left == '':
            total += 10
        else:
            total += _CN_NUM_MAP.get(left, 0) * 10
        if right:
            total += _CN_NUM_MAP.get(right, 0)
        return total
    if len(token) == 1 and token in _CN_NUM_MAP:
        return _CN_NUM_MAP[token]
    return None


_ROMAN_MAP = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}


def roman_to_int(token: str):
    t = token.upper()
    return _ROMAN_MAP.get(t)


def extract_seq_tokens(s: str):
    out = set()
    for m in re.findall(r"\d{1,2}", s):
        v = int(m)
        if 1 <= v <= 99:
            out.add(str(v))
    for m in re.findall(r"[一二两三四五六七八九十]{1,3}", s):
        v = chinese_numeral_to_int(m)
        if v and 1 <= v <= 99:
            out.add(str(v))
    for m in re.findall(r"\b(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\b", s, flags=re.I):
        v = roman_to_int(m)
        if v and 1 <= v <= 99:
            out.add(str(v))
    return out


def seq_normalize(s: str):
    # replace chinese numerals with arabic and simple roman numerals
    def _rep_cn(m):
        v = chinese_numeral_to_int(m.group(0))
        return str(v) if v is not None else m.group(0)

    s = re.sub(r"[一二两三四五六七八九十]{1,3}", _rep_cn, s)

    def _rep_rom(m):
        v = roman_to_int(m.group(0))
        return str(v) if v is not None else m.group(0)

    s = re.sub(r"\b(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\b", _rep_rom, s, flags=re.I)
    return s
