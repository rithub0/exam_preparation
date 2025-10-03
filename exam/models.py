from django.db import models
from django.contrib.auth.models import User


class Chapter(models.Model):
    """
    公式の章を表す。num は 1..19 の整数、official_quota は公式想定の配点（問数）。
    """
    num = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=100)
    official_quota = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["num"]
        indexes = [
            models.Index(fields=["num"]),
        ]

    def __str__(self) -> str:
        return f"Ch{self.num}: {self.title} ({self.official_quota})"


class Question(models.Model):
    """
    選択式問題。出題対象外（公式の除外指定）は is_excluded=True で管理。
    """
    KIND_SINGLE = "single"   # 単一選択
    KIND_MULTI = "multi"     # 複数選択（将来拡張用）
    KIND_JUDGE = "judge"     # 正誤判定
    KIND_CHOICES = [
        (KIND_SINGLE, "single"),
        (KIND_MULTI, "multi"),
        (KIND_JUDGE, "judge"),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_SINGLE)
    stem = models.TextField()                       # 問題文（コード断片含む）
    note = models.TextField(blank=True, default="") # 解説（自作）
    is_excluded = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["chapter"]),
            models.Index(fields=["is_excluded"]),
        ]

    def __str__(self) -> str:
        return f"[Ch{self.chapter.num}] {self.stem[:40]}..."


class Choice(models.Model):
    """
    選択肢。1つ以上が正解になり得る（multi対応のため）。
    """
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["question"]),
            models.Index(fields=["is_correct"]),
        ]

    def __str__(self) -> str:
        mark = "✓" if self.is_correct else " "
        return f"{mark} {self.text[:40]}..."


class Attempt(models.Model):
    """
    受験者の解答履歴。Leitner 法の箱番号(box)で復習間隔を管理。
    mode: 'mock'（本番トレース）, 'rehab'（弱点リハビリ）, 'srs'（直前直上げ）
    """
    MODE_MOCK = "mock"
    MODE_REHAB = "rehab"
    MODE_SRS = "srs"
    MODE_CHOICES = [
        (MODE_MOCK, "mock"),
        (MODE_REHAB, "rehab"),
        (MODE_SRS, "srs"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)
    box = models.PositiveSmallIntegerField(default=0)  # 0..4

    class Meta:
        indexes = [
            models.Index(fields=["user", "answered_at"]),
            models.Index(fields=["question", "answered_at"]),
            models.Index(fields=["mode"]),
        ]

    def __str__(self) -> str:
        mark = "✓" if self.is_correct else "×"
        return f"{self.user.username} {mark} Q{self.question_id} ({self.mode})"
