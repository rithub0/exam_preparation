from __future__ import annotations

import random

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_protect

# from django.http import JsonResponse

from .models import Question, Choice, Attempt, Chapter

from .logic.selector import build_mock_set_ids
from .logic.quality import quota_deficits, total_quota

EXAM_DURATION_SEC = 75 * 60  # 75分


# 進捗パーセントを 0–100 の整数に正規化（%記号なし）
def _progress_percent(now: int, total: int) -> int:
    try:
        now_i = max(int(now), 0)
    except Exception:
        now_i = 0
    try:
        total_i = max(int(total or 0), 0)
    except Exception:
        total_i = 0

    if total_i > 0:
        pct = int(round(now_i * 100.0 / total_i))
    else:
        pct = 0
    return max(0, min(100, pct))


def _get_shuffled_choices_for_question(request, question):
    """
    表示順を毎回ランダム化。ただし同一設問内では固定したいので、
    セッションに順序(choicesのid列)を保存して再利用する。
    """
    key = f"choice_order_{question.id}"
    order = request.session.get(key)
    if not order:
        order = list(question.choices.values_list("id", flat=True))
        random.shuffle(order)
        request.session[key] = order

    # order に従って並べ替えた Choice インスタンスのリストを返す
    choices = list(question.choices.all())
    pos = {cid: i for i, cid in enumerate(order)}
    choices.sort(key=lambda c: pos.get(c.id, 10**9))
    return choices


@login_required
def dashboard(request):
    q_count = Question.objects.filter(is_excluded=False).count()

    ch_coverage = Chapter.objects.annotate(
        n=Count("question", filter=Q(question__is_excluded=False))
    ).order_by("num")

    total_quota_val = sum(ch.official_quota for ch in ch_coverage)
    total_stock_for_quota = sum(min(ch.n, ch.official_quota) for ch in ch_coverage)

    deficits = quota_deficits()  # ★ 追加
    has_deficit = len(deficits) > 0

    return render(
        request,
        "exam/dashboard.html",
        {
            "q_count": q_count,
            "ch_coverage": ch_coverage,
            "total_quota": total_quota_val,
            "total_stock_for_quota": total_stock_for_quota,
            "deficits": deficits,  # ★ 追加
            "has_deficit": has_deficit,  # ★ 追加
        },
    )


@csrf_protect
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # ← DBにユーザー作成（ORM経由）
            auth_login(request, user)  # すぐログインさせる場合
            return redirect("dashboard")  # 適宜あなたのトップ/ダッシュボード名へ
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def mock_start(request):
    # ★ 追加：開始前チェック
    deficits = quota_deficits()
    if deficits:
        msg = "クォータ不足の章があります：" + ", ".join(
            [f"Ch{d['ch']}不足{d['lack']}" for d in deficits]
        )
        messages.warning(request, msg)

    ids = build_mock_set_ids()
    if not ids:
        messages.error(
            request, "出題可能な問題がありません。管理画面から問題を追加してください。"
        )
        return redirect("dashboard")

    # ★ 追加：40問に満たない場合の注意
    intended = total_quota()  # 通常40
    if len(ids) < intended:
        messages.warning(
            request,
            f"今回は {len(ids)}問です（想定 {intended}問）。不足章のため減少しています。",
        )

    request.session["mock_ids"] = ids
    request.session["mock_index"] = 0
    request.session["mock_correct"] = 0
    request.session["mock_started_at"] = timezone.now().timestamp()
    return redirect("mock_session")


@login_required
def mock_session(request):
    ids = request.session.get("mock_ids")
    idx = request.session.get("mock_index", 0)
    correct_total = request.session.get("mock_correct", 0)
    started_at_ts = request.session.get("mock_started_at")

    if not ids:
        messages.info(request, "モックを開始してください。")
        return redirect("dashboard")

    # 残り時間の計算（サーバ側で毎回チェック）
    if started_at_ts is None:
        request.session["mock_started_at"] = timezone.now().timestamp()
        started_at_ts = request.session["mock_started_at"]

    try:
        elapsed = max(0, int(timezone.now().timestamp() - float(started_at_ts)))
    except Exception:
        elapsed = 0
    remaining = max(0, EXAM_DURATION_SEC - elapsed)
    if remaining <= 0:
        return redirect("mock_result")

    # 全問完了
    if idx >= len(ids):
        return redirect("mock_result")

    q = get_object_or_404(Question, pk=ids[idx])

    judged = False
    was_correct = False
    chosen_id = None

    if request.method == "POST":
        chosen_id = request.POST.get("choice")
        if chosen_id is None and "next" not in request.POST:
            messages.warning(request, "選択肢を選んでください。")
        else:
            chosen = None
            if chosen_id:
                try:
                    chosen = Choice.objects.get(pk=chosen_id, question=q)
                except Choice.DoesNotExist:
                    chosen = None

            was_correct = bool(chosen and chosen.is_correct)
            judged = True

            Attempt.objects.create(
                user=request.user,
                question=q,
                is_correct=was_correct,
                mode=Attempt.MODE_MOCK,
                box=0,
                answered_at=timezone.now(),
            )

            if was_correct:
                correct_total += 1
                request.session["mock_correct"] = correct_total

            # 「次へ」クリック後に次の設問へ
            if "next" in request.POST:
                request.session["mock_index"] = idx + 1
                return redirect("mock_session")

    # 進捗（%はサーバ側で算出してテンプレへ）
    progress = {
        "now": idx + 1,
        "total": len(ids),
        "score": correct_total,
        "percent": _progress_percent(idx, len(ids)),  # 現在の問題に入る前の達成率
    }

    return render(
        request,
        "exam/session.html",
        {
            "question": q,
            "choices": _get_shuffled_choices_for_question(request, q),
            "judged": judged,
            "was_correct": was_correct,
            "chosen_id": int(chosen_id) if chosen_id else None,
            "progress": progress,
            # 残り秒数をテンプレに渡す（クライアントでカウントダウン表示）
            "remaining_sec": remaining,
            "duration_sec": EXAM_DURATION_SEC,
        },
    )


@login_required
def mock_result(request):
    """
    結果画面：スコアと簡単な章別内訳（正規化せず、直近セッションの Attempt から概算）
    """
    ids = request.session.get("mock_ids") or []
    total = len(ids)
    score = request.session.get("mock_correct", 0)

    # 章別内訳（今回の mock のみを対象に粗集計）
    attempts = Attempt.objects.filter(
        user=request.user, mode=Attempt.MODE_MOCK
    ).order_by("-answered_at")[
        :total
    ]  # 直近 total 件を仮定

    ch_stat: dict[int, dict[str, int]] = {}
    for at in attempts:
        ch = at.question.chapter.num
        if ch not in ch_stat:
            ch_stat[ch] = {"c": 0, "n": 0}
        ch_stat[ch]["n"] += 1
        ch_stat[ch]["c"] += int(at.is_correct)

    # セッションをクリア（任意）
    for k in ("mock_ids", "mock_index", "mock_correct"):
        request.session.pop(k, None)

    return render(
        request,
        "exam/result.html",
        {
            "total": total,
            "score": score,
            "ch_stat": ch_stat,
        },
    )
