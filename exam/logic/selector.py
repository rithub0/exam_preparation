# practicum/exam/logic/selector.py
from __future__ import annotations
import random
from typing import List
from exam.models import Question

# 公式配点（40問）
CHAPTER_QUOTA = {
    1:1, 2:2, 3:7, 4:3, 5:2, 6:4, 7:0, 8:2, 9:5, 10:2,
    11:2, 12:0, 13:2, 14:2, 15:0, 16:3, 17:2, 18:1, 19:0
}

def build_mock_set_ids() -> List[int]:
    """
    公式クォータを満たす問題ID配列を作る。
    その章に十分な問題が無い場合、ある分だけ採用（不足章は飛ばす）。
    """
    picked_ids: List[int] = []
    for ch, n in CHAPTER_QUOTA.items():
        if n == 0:
            continue
        qs = (Question.objects
              .filter(chapter__num=ch, is_excluded=False)
              .order_by('?')[:n])
        picked_ids.extend(qs.values_list("id", flat=True))
    # 章横断で軽くシャッフル
    random.shuffle(picked_ids)
    return list(picked_ids)  # 目標は40件だが、問題不足なら短くなる
