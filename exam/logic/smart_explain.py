# exam/logic/smart_explain.py
from __future__ import annotations
from difflib import SequenceMatcher
import re
import html
from typing import List, Set, Tuple

# かんたんな知識ベース（必要最低限）
HINTS = {
    "sorted": "sorted(iterable, ...) は新しいリストを返す（元は変更しない）。",
    "list.sort": "list.sort() は就地変更で戻り値は None。",
    "enumerate": "enumerate(iterable) は (index, value) を返す。",
    "zip": "zip(a, b) はタプルのイテレータ。長さは短い方に揃う。",
    "range": "range は遅延評価。list(range(...)) で展開。",
    "dict": "辞書はキー重複不可。3.7+ で挿入順保持。",
    "set": "set は重複なし・順序なし。in で高速会員判定。",
    "tuple": "tuple はイミュータブル。",
    "slice": "s[a:b:c] がスライス。[::-1] は反転。",
    "len": "len(x) は要素数。カスタム型は __len__ 実装で対応。",
    "open": "with open(...) as f: でブロック終了時に自動 close。",
    "with": "with はコンテキストマネージャ（__enter__/__exit__）。",
}

# 単語 or ドット名 or 代表的スライス表現を拾う
TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?|\[\s*:\s*\]|\[\s*:\s*-\s*1\s*\]"
)

# 単語・記号を抽出するための正規表現
WORD_RE = re.compile(r'[\w]+|[^\w\s]+')


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)

def _extract_words(text: str) -> Set[str]:
    """テキストから単語と記号を抽出してセットとして返す"""
    return set(WORD_RE.findall(text.lower()))

def _highlight_unique_words(text: str, correct_words: Set[str]) -> str:
    """
    正解に含まれない単語や記号を赤色でハイライトする
    """
    words = WORD_RE.findall(text)
    result = []
    for word in words:
        if word.lower() not in correct_words:
            # 正解に含まれない単語は赤色でマーク
            result.append(f'<span style="color: red;">{_esc(word)}</span>')
        else:
            result.append(_esc(word))
    return ' '.join(result)


def build_diff_html(chosen_text: str, correct_text: str) -> str:
    """
    差分を表示する改良版。
    - 誤答の場合、選択した不正解の内容を表示
    - 正解に含まれない単語や記号を赤色でハイライト
    """
    if not chosen_text:  # 選択なしの場合
        return f'<div class="correct-answer">正解: {_esc(correct_text)}</div>'

    # 正解テキストから単語を抽出
    correct_words = _extract_words(correct_text)
    
    # 不正解の選択肢をハイライトして表示
    wrong_answer = _highlight_unique_words(chosen_text, correct_words)
    
    result = [f'<div class="wrong-answer">{wrong_answer}</div>']
    
    return ''.join(result)


def extract_hints(stem: str, correct_text: str, max_items: int = 3) -> List[str]:
    """
    問題文と正解文からキーワード抽出 → 知識ベースから最大 max_items 件のヒント。
    """
    text = f"{stem}\n{correct_text}"
    tokens = TOKEN_RE.findall(text)

    def normalize(tok: str) -> str:
        if tok in ("[::-1]", "[:]"):
            return "slice"
        # list.sort のような表記を優先
        if tok == "sort" and "list.sort" in text:
            return "list.sort"
        return tok

    hints: List[str] = []
    seen = set()
    # 出現順を尊重
    for raw in tokens:
        key = normalize(raw)
        if key in HINTS and key not in seen:
            seen.add(key)
            hints.append(HINTS[key])
            if len(hints) >= max_items:
                break
    return hints
