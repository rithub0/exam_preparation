# exam_preparation/exam/views.py

from __future__ import annotations  # 未来の型注釈仕様を使うためのimport（Python 3.7+で利用可能）

import random  # ランダム操作用モジュール

from django.contrib.auth.forms import UserCreationForm  # ユーザー登録用フォーム
from django.shortcuts import render, redirect, get_object_or_404  # ビューでのレンダリング・リダイレクト・存在チェック
from django.contrib.auth.decorators import login_required  # ログイン必須デコレーター
from django.contrib import messages  # ユーザへのメッセージ送信機能
from django.utils import timezone  # タイムゾーン対応の現在時刻取得
import logging  # ロギング機能

# ロガーの取得
logger = logging.getLogger(__name__)
from django.db.models import Count, Q  # 集約関数Countと条件付きクエリ用Qオブジェクト
from django.views.decorators.csrf import csrf_protect  # CSRF保護デコレーター

from .models import Question, Choice, Attempt, Chapter  # 自作モデルのインポート

from .logic.selector import build_mock_set_ids  # 出題セットIDを作成するロジック関数
from .logic.quality import quota_deficits, total_quota  # 問題数不足検知や合計問題数計算関数
from .logic.smart_explain import build_diff_html, extract_hints  # ★追加


EXAM_DURATION_SEC = 75 * 60  # 試験時間は75分（秒数に換算）


# 進捗パーセントを 0–100 の整数に正規化（%記号なし）
def _progress_percent(now: int, total: int) -> int:
    try:
        now_i = max(int(now), 0)  # nowを整数化し0未満なら0にする
    except Exception:
        now_i = 0  # 整数変換失敗時は0
    try:
        total_i = max(int(total or 0), 0)  # totalを整数化し0未満なら0にする
    except Exception:
        total_i = 0  # 整数変換失敗時は0

    if total_i > 0:
        pct = int(round(now_i * 100.0 / total_i))  # 進捗率をパーセントで計算
    else:
        pct = 0  # totalが0なら0％
    return max(0, min(100, pct))  # 0〜100の範囲に収めて返す


def _get_shuffled_choices_for_question(request, question):
    """
    表示順を毎回ランダム化。ただし同一設問内では固定したいので、
    セッションに順序(choicesのid列)を保存して再利用する。
    """
    key = f"choice_order_{question.id}"  # セッションキーを問題IDに基づいて作成
    order = request.session.get(key)  # セッションから順序を取得
    if not order:  # セッションに順序がなければ
        order = list(question.choices.values_list("id", flat=True))  # 選択肢IDリストを取得
        random.shuffle(order)  # ランダムに並べ替え
        request.session[key] = order  # セッションに保存

    # order に従って並べ替えた Choice インスタンスのリストを返す
    choices = list(question.choices.all())  # 全選択肢を取得
    pos = {cid: i for i, cid in enumerate(order)}  # id→順序の辞書作成
    choices.sort(key=lambda c: pos.get(c.id, 10**9))  # orderに従って並び替え。なければ最後尾扱い
    return choices


@login_required  # ログイン必須
def dashboard(request):
    q_count = Question.objects.filter(is_excluded=False).count()
    # 除外されていない問題の総数を取得

    ch_coverage = Chapter.objects.annotate(
        n=Count("question", filter=Q(question__is_excluded=False))
    ).order_by("num")
    # 章ごとに出題可能な問題数(n)を集計し、章番号順に並べる

    total_quota_val = sum(ch.official_quota for ch in ch_coverage)
    # 全章の公式問題数合計を計算

    total_stock_for_quota = sum(min(ch.n, ch.official_quota) for ch in ch_coverage)
    # 問題数と問題数の少ない方を足し合わせた実際の出題可能数合計

    deficits = quota_deficits()  # 問題数不足の章のリストを取得（カスタム関数）
    has_deficit = len(deficits) > 0  # 不足があるかどうか真偽値判定

    return render(
        request,
        "exam/dashboard.html",
        {
            "q_count": q_count,
            "ch_coverage": ch_coverage,
            "total_quota": total_quota_val,
            "total_stock_for_quota": total_stock_for_quota,
            "deficits": deficits,  # 問題数不足章情報
            "has_deficit": has_deficit,  # 不足有無フラグ
        },
    )


@csrf_protect  # CSRF攻撃防止を有効にする
def signup(request):
    if request.method == "POST":  # フォーム送信時
        form = UserCreationForm(request.POST)  # 送信データでフォームを生成
        if form.is_valid():  # 入力チェックが通れば
            form.save()  # ユーザー登録を実施（自動ログインなし）
            messages.success(
                request, "ユーザー登録が完了しました。ログインしてください。"
            )  # 登録成功メッセージ表示
            return redirect("login")  # ログイン画面へリダイレクト
    else:
        form = UserCreationForm()  # 空の登録フォームを作成
    return render(request, "registration/signup.html", {"form": form})  # 登録ページ表示


@login_required
def mock_start(request):
    # ★ 追加：開始前チェック
    deficits = quota_deficits()  # 問題数不足章を確認
    if deficits:
        msg = "問題数不足の章があります：" + ", ".join(
            [f"Ch{d['ch']}不足{d['lack']}" for d in deficits]
        )  # 不足章のメッセージ作成
        messages.warning(request, msg)  # 警告メッセージ表示

    ids = build_mock_set_ids()  # 出題問題IDリストを作成
    if not ids:
        messages.error(
            request, "出題可能な問題がありません。管理画面から問題を追加してください。"
        )  # 問題なしエラーメッセージ
        return redirect("dashboard")  # ダッシュボードに戻る

    # ★ 追加：40問に満たない場合の注意
    intended = total_quota()  # 想定問題数（通常40問）
    if len(ids) < intended:
        messages.warning(
            request,
            f"今回は {len(ids)}問です（想定 {intended}問）。不足章のため減少しています。",
        )  # 不足のため問題数が減っている警告

    request.session["mock_ids"] = ids  # 問題IDリストをセッションに保存
    request.session["mock_index"] = 0  # 現在の問題番号を0に初期化
    request.session["mock_correct"] = 0  # 正解数を0に初期化
    request.session["mock_started_at"] = timezone.now().timestamp()  # 開始時刻を保存
    return redirect("mock_session")  # 問題回答画面へリダイレクト


@login_required
def mock_session(request):
    ids = request.session.get("mock_ids")  # 出題問題IDリストをセッションから取得
    idx = request.session.get("mock_index", 0)  # 現在の問題番号（デフォルト0）
    correct_total = request.session.get("mock_correct", 0)  # 現時点の正解数
    started_at_ts = request.session.get("mock_started_at")  # 試験開始タイムスタンプ

    if not ids:
        messages.info(request, "モックを開始してください。")  # 出題セットなしなら案内
        return redirect("dashboard")  # ダッシュボードへ

    # 残り時間の計算（サーバ側で毎回チェック）
    if started_at_ts is None:
        request.session["mock_started_at"] = timezone.now().timestamp()  # 開始時刻をセット
        started_at_ts = request.session["mock_started_at"]

    try:
        elapsed = max(0, int(timezone.now().timestamp() - float(started_at_ts)))
        # 経過秒数を計算。マイナス防止のためmaxで0以上
    except Exception:
        elapsed = 0  # 失敗時は0秒経過とみなす

    remaining = max(0, EXAM_DURATION_SEC - elapsed)  # 残り秒数計算（0未満にならない）
    if remaining <= 0:
        return redirect("mock_result")  # 時間切れなら結果画面へ

    # 全問完了
    if idx >= len(ids):
        return redirect("mock_result")  # 問題全回答済なら結果画面へ

    q = get_object_or_404(Question, pk=ids[idx])  # 現在の問題を取得（存在しなければ404）

    judged = False  # 採点済みフラグ初期化
    was_correct = False  # 正誤フラグ初期化
    chosen_id = None  # 選択された選択肢ID初期化
    # （関数先頭のローカル変数に追加しておくと楽）
    smart_diff_html = ""
    smart_hints = []
    chosen = None  # ★ 既存に無ければ先に定義


    if request.method == 'POST':
        chosen_id = request.POST.get('choice')
        if chosen_id is None and 'next' not in request.POST:
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

            # Attempt保存 …（既存のまま）

            if was_correct:
                correct_total += 1
                request.session['mock_correct'] = correct_total
            else:
                # ★ ここがスマート解説の肝：差分とヒントを生成
                correct_text = " / ".join(
                    q.choices.filter(is_correct=True).values_list("text", flat=True)
                )
                chosen_text = chosen.text if chosen else ""
                smart_diff_html = build_diff_html(chosen_text, correct_text)
                smart_hints = extract_hints(q.stem, correct_text)

            if 'next' in request.POST:
                request.session['mock_index'] = idx + 1
                return redirect('mock_session')


    # 進捗（%はサーバ側で算出してテンプレへ）
    progress = {
        "now": idx + 1,  # 現在の問題番号（1始まり表示）
        "total": len(ids),  # 問題総数
        "score": correct_total,  # 現時点の正解数
        "percent": _progress_percent(idx, len(ids)),  # 現在問題に入る前の達成率（0〜100）
    }

    return render(request, 'exam/session.html', {
        "question": q,
        "judged": judged,
        "was_correct": was_correct,
        "chosen_id": int(chosen_id) if chosen_id else None,
        "progress": progress,
        "remaining_sec": remaining,
        "duration_sec": EXAM_DURATION_SEC,
        "choices": _get_shuffled_choices_for_question(request, q),  # 既存
        "smart_diff_html": smart_diff_html,  # ★追加
        "smart_hints": smart_hints,          # ★追加
    })


@login_required
def mock_result(request):
    """
    結果画面：スコアと簡単な章別内訳（正規化せず、直近セッションの Attempt から概算）
    """
    ids = request.session.get("mock_ids") or []  # 問題IDリストを取得、なければ空リスト
    total = len(ids)  # 問題数
    score = request.session.get("mock_correct", 0)  # 正解数

    # 章別内訳（今回の mock のみを対象に粗集計）
    attempts = Attempt.objects.filter(
        user=request.user, mode=Attempt.MODE_MOCK
    ).order_by("-answered_at")[
        :total
    ]  # 直近 total 件の回答履歴を取得

    ch_stat: dict[int, dict[str, int]] = {}  # 章ごとの正解数・回答数を格納する辞書
    for at in attempts:
        ch = at.question.chapter.num  # 回答問題の章番号
        if ch not in ch_stat:
            ch_stat[ch] = {"c": 0, "n": 0}  # 初期化
        ch_stat[ch]["n"] += 1  # 回答数を加算
        ch_stat[ch]["c"] += int(at.is_correct)  # 正解数を加算（Trueは1、Falseは0）

    # セッションをクリア（任意）
    for k in ("mock_ids", "mock_index", "mock_correct"):
        request.session.pop(k, None)  # セッションから出題情報を削除

    return render(
        request,
        "exam/result.html",  # 結果画面テンプレート
        {
            "total": total,  # 問題総数
            "score": score,  # 正解数
            "ch_stat": ch_stat,  # 章別統計
        },
    )
