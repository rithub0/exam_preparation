# exam_preparation/exam/logic/selector.py

from __future__ import annotations  # Pythonの将来のバージョンとの互換性のための記述（主に型アノテーション向け）
import random  # リストをシャッフルするために使用
from typing import List  # 戻り値の型注釈（List[int]など）に使う
from exam.models import Question  # DBモデルのQuestionをインポート

# 各章における公式出題数（合計40問になる設計）
CHAPTER_QUOTA = {
    1: 1,   # 第1章からは1問
    2: 2,   # 第2章からは2問
    3: 7,   # 第3章からは7問（最多）
    4: 3,
    5: 2,
    6: 4,
    7: 0,   # 第7章は出題しない
    8: 2,
    9: 5,
    10: 2,
    11: 2,
    12: 0,  # 第12章は出題しない
    13: 2,
    14: 2,
    15: 0,  # 第15章は出題しない
    16: 3,
    17: 2,
    18: 1,
    19: 0   # 第19章は出題しない
}

def build_mock_set_ids() -> List[int]:
    """
    公式出題数（CHAPTER_QUOTA）に基づき、ランダムに問題IDを選出してリストで返す。
    各章の問題が不足している場合は、取得できる分だけ採用し、不足章はスキップする。
    """
    picked_ids: List[int] = []  # 選ばれた問題IDを格納するリストを初期化

    for ch, n in CHAPTER_QUOTA.items():  # 各章番号と必要な問題数nをループ
        if n == 0:  # 出題数0の章はスキップ
            continue

        # 対象章(ch)で「除外されていない」問題（is_excluded=False）をランダム順でn件取得
        qs = Question.objects.filter(
            chapter__num=ch, is_excluded=False  # 章番号が一致 & 除外されていない問題
        ).order_by("?")[:n]  # ランダムに並べて、最大n件を取得

        # 取得した問題のIDだけを抽出し、リストに追加
        picked_ids.extend(qs.values_list("id", flat=True))

    # 全ての章から集めた問題IDリストをシャッフルして順番をランダム化（章横断的なランダム性）
    random.shuffle(picked_ids)

    return list(picked_ids)  # 最終的な問題IDリストを返す（最大40件、章の在庫次第で不足可）
