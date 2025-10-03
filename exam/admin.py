from django.contrib import admin
from .models import Chapter, Question, Choice, Attempt


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("num", "title", "official_quota")
    list_editable = ("title", "official_quota")
    search_fields = ("title",)
    ordering = ("num",)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "chapter", "kind", "is_excluded", "created_at")
    list_filter = ("chapter", "kind", "is_excluded")
    search_fields = ("stem", "note")
    inlines = [ChoiceInline]
    ordering = ("-id",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "is_correct", "mode", "box", "answered_at")
    list_filter = ("is_correct", "mode", "box", "answered_at")
    search_fields = ("user__username",)
    ordering = ("-answered_at",)
