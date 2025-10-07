# exam_preparation/exam/logic/quality.py

from __future__ import annotations  # 将来のバージョンのアノテーションの互換性を確保（Python 3.7以降用）
from typing import List, Dict  # 型アノテーション用のListとDictをインポート
from django.db.models import Count, Q  # Django ORMで集計・条件指定に使う関数をインポート
from exam.models import Chapter  # DBモデルChapterをインポート
from exam.logic.selector import CHAPTER_QUOTA  # 各章ごとの公式出題数定義をインポート

def quota_deficits() -> List[Dict]:
    """
    公式出題数に対して、章ごとの出題対象在庫（is_excluded=False）が不足している章を返す。
    return例: [{"ch":3, "title":"Chapter 3", "quota":7, "stock":5, "lack":2}, ...]
    """
    qs = Chapter.objects.annotate(
        # 各Chapterに紐づく「除外されていない問題数（is_excluded=False）」をstockとして集計
        stock=Count("question", filter=Q(question__is_excluded=False))
    ).order_by("num")  # 章番号順に並べ替え

    deficits: List[Dict] = []  # 出題数が不足している章のリストを初期化
    for ch in qs:  # 各章をループ
        # 章ごとの公式出題数を取得。定義がなければモデルのofficial_quota、さらになければ0
        quota = CHAPTER_QUOTA.get(ch.num, ch.official_quota or 0)
        stock = getattr(ch, "stock", 0)  # 集計済みのstock属性（出題可能な問題数）を取得。なければ0
        if quota and stock < quota:  # 出題数が定義されていて、在庫が不足している場合
            deficits.append(  # 不足情報を辞書にしてリストに追加
                {
                    "ch": ch.num,  # 章番号
                    "title": ch.title,  # 章タイトル
                    "quota": quota,  # 公式に必要とされる出題数
                    "stock": stock,  # 実際に出題可能な問題数
                    "lack": quota - stock,  # 不足数
                }
            )
    return deficits  # 不足している章のリストを返す

def total_quota() -> int:
    # すべての章における公式出題数の合計を返す
    return sum(v for v in CHAPTER_QUOTA.values())
