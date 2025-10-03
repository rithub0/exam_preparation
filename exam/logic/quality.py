# practicum/exam/logic/quality.py
from __future__ import annotations
from typing import List, Dict
from django.db.models import Count, Q
from exam.models import Chapter
from exam.logic.selector import CHAPTER_QUOTA  # 既存の配点定義を使う

def quota_deficits() -> List[Dict]:
    """
    公式クォータに対して、章ごとの出題対象在庫（is_excluded=False）が不足している章を返す。
    return: [{"ch":3, "title":"Chapter 3", "quota":7, "stock":5, "lack":2}, ...]
    """
    qs = (Chapter.objects
          .annotate(stock=Count("question", filter=Q(question__is_excluded=False)))
          .order_by("num"))

    deficits: List[Dict] = []
    for ch in qs:
        quota = CHAPTER_QUOTA.get(ch.num, ch.official_quota or 0)
        stock = getattr(ch, "stock", 0)
        if quota and stock < quota:
            deficits.append({
                "ch": ch.num,
                "title": ch.title,
                "quota": quota,
                "stock": stock,
                "lack": quota - stock
            })
    return deficits

def total_quota() -> int:
    return sum(v for v in CHAPTER_QUOTA.values())
