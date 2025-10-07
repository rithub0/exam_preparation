# exam_preparation/exam/admin.py

from django.contrib import admin  # Djangoの管理サイト用モジュールをインポート
from .models import Chapter, Question, Choice, Attempt  # 同じアプリのモデルをインポート


@admin.register(Chapter)  # Chapterモデルをadminに登録し、以下の設定を適用
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("num", "title", "official_quota")  
    # 一覧画面に表示するフィールドを指定（章番号、タイトル、公式出題数）
    list_editable = ("title", "official_quota")  
    # 一覧画面で直接編集可能なフィールド（タイトルと公式出題数）
    search_fields = ("title",)  
    # 検索ボックスでタイトルを対象に検索可能にする
    ordering = ("num",)  
    # デフォルトの並び順を章番号の昇順に設定


class ChoiceInline(admin.TabularInline):
    model = Choice  # Choiceモデルをインライン（親Questionの編集画面に組み込み）
    extra = 0  # 追加の空行（新規Choice入力欄）を表示しない


@admin.register(Question)  # Questionモデルをadminに登録
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "chapter", "kind", "is_excluded", "created_at")  
    # 一覧表示するフィールド（ID、章、種類、除外フラグ、作成日時）
    list_filter = ("chapter", "kind", "is_excluded")  
    # 絞り込みに使うフィルター（章、種類、除外の有無）
    search_fields = ("stem", "note")  
    # 検索対象を問題文(stem)と備考(note)に設定
    inlines = [ChoiceInline]  
    # Question編集画面でChoiceをインライン表示・編集可能に
    ordering = ("-id",)  
    # 一覧のデフォルト並び順をID降順（新しい順）に設定


@admin.register(Attempt)  # Attemptモデルをadminに登録
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "question",
        "is_correct",
        "mode",
        "box",
        "answered_at",
    )  
    # 一覧に表示するフィールド（回答ID、ユーザー、問題、正誤、モード、ボックス、回答日時）
    list_filter = ("is_correct", "mode", "box", "answered_at")  
    # 絞り込みに使うフィルター（正誤、モード、ボックス番号、回答日時）
    search_fields = ("user__username",)  
    # ユーザーのusernameを対象に検索可能にする（外部キーのフィールド指定）
    ordering = ("-answered_at",)  
    # 一覧のデフォルト並び順を回答日時の降順に設定（新しい順）
