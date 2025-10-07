# exam_preparation/exam/models.py

from django.db import models  # Djangoのモデル定義用モジュールをインポート
from django.contrib.auth.models import User  # ユーザモデルをインポート


class Chapter(models.Model):
    """
    公式の章を表すモデル。
    num は 1から19までの章番号、official_quota は公式想定の出題数（配点）
    """

    num = models.PositiveSmallIntegerField(unique=True)
    # 章番号。正の小さい整数。ユニーク制約（重複不可）
    title = models.CharField(max_length=100)
    # 章タイトル。最大100文字の文字列
    official_quota = models.PositiveSmallIntegerField(default=0)
    # 公式出題数。0以上。デフォルトは0

    class Meta:
        ordering = ["num"]
        # デフォルトの並び順は章番号昇順
        indexes = [
            models.Index(fields=["num"]),
            # numフィールドにインデックスを設定し検索高速化
        ]

    def __str__(self) -> str:
        # 管理画面やshellで表示するときの文字列表現
        return f"Ch{self.num}: {self.title} ({self.official_quota})"


class Question(models.Model):
    """
    選択式問題モデル。
    出題対象外は is_excluded=True で管理。
    """

    KIND_SINGLE = "single"  # 単一選択
    KIND_MULTI = "multi"  # 複数選択（将来拡張用）
    KIND_JUDGE = "judge"  # 正誤判定
    KIND_CHOICES = [
        (KIND_SINGLE, "single"),
        (KIND_MULTI, "multi"),
        (KIND_JUDGE, "judge"),
    ]
    # 問題の種類の選択肢定義

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    # 章への外部キー。章削除時は紐づく問題も削除
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_SINGLE)
    # 問題の種類。10文字まで。デフォルトは単一選択
    stem = models.TextField()  # 問題文（コード断片を含むこともある）
    note = models.TextField(blank=True, default="")  # 解説。空欄も可でデフォルトは空文字
    is_excluded = models.BooleanField(default=False)
    # 出題除外フラグ。Falseが通常出題対象

    created_at = models.DateTimeField(auto_now_add=True)
    # 作成日時。自動でレコード作成時に設定される

    class Meta:
        indexes = [
            models.Index(fields=["chapter"]),
            # chapterフィールドにインデックス（章単位検索高速化）
            models.Index(fields=["is_excluded"]),
            # is_excludedフィールドにインデックス（除外検索用）
        ]

    def __str__(self) -> str:
        # 表示用。章番号と問題文先頭40文字を表示
        return f"[Ch{self.chapter.num}] {self.stem[:40]}..."


class Choice(models.Model):
    """
    選択肢モデル。
    1問に対し複数の選択肢があり、複数正解の可能性もある（multi対応）
    """

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    # Questionモデルへの外部キー。question.choicesで逆参照可能。
    # Question削除時に紐づくChoiceも削除
    text = models.TextField()
    # 選択肢のテキスト内容
    is_correct = models.BooleanField(default=False)
    # 正解選択肢かどうかのフラグ。Falseがデフォルト

    class Meta:
        indexes = [
            models.Index(fields=["question"]),
            # questionフィールドにインデックス（問題単位で選択肢取得を高速化）
            models.Index(fields=["is_correct"]),
            # 正解・不正解の判定検索用にインデックス
        ]

    def __str__(self) -> str:
        # 表示用。正解なら✓、そうでなければ空白を先頭につけて表示
        mark = "✓" if self.is_correct else " "
        return f"{mark} {self.text[:40]}..."


class Attempt(models.Model):
    """
    受験者の解答履歴モデル。
    Leitner方式の復習間隔管理用のbox番号も保持。
    modeは 'mock'（本番模擬）, 'rehab'（弱点リハビリ）, 'srs'（短期記憶直上げ）を表す。
    """

    MODE_MOCK = "mock"
    MODE_REHAB = "rehab"
    MODE_SRS = "srs"
    MODE_CHOICES = [
        (MODE_MOCK, "mock"),
        (MODE_REHAB, "rehab"),
        (MODE_SRS, "srs"),
    ]
    # 回答モードの選択肢定義

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # 回答者ユーザーへの外部キー。ユーザー削除時に紐づく回答も削除
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    # 回答した問題への外部キー。問題削除時に紐づく回答も削除
    is_correct = models.BooleanField()
    # 回答が正解か否か
    answered_at = models.DateTimeField(auto_now_add=True)
    # 回答日時。自動で設定される
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)
    # 回答モード。最大16文字まで
    box = models.PositiveSmallIntegerField(default=0)  # 0..4
    # 復習ボックス番号。Leitner方式の箱番号で復習レベル管理。0が初期値

    class Meta:
        indexes = [
            models.Index(fields=["user", "answered_at"]),
            # ユーザーごとの回答履歴を日時順に高速検索可能にする複合インデックス
            models.Index(fields=["question", "answered_at"]),
            # 問題ごとの回答履歴を日時順に高速検索可能にする複合インデックス
            models.Index(fields=["mode"]),
            # モード別回答履歴検索を高速化するためのインデックス
        ]

    def __str__(self) -> str:
        # 表示用。ユーザー名、正誤記号、問題ID、モードを表示
        mark = "✓" if self.is_correct else "×"
        return f"{self.user.username} {mark} Q{self.question_id} ({self.mode})"
