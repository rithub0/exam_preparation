from __future__ import annotations
import json
import pathlib
from typing import Dict, Any, List
from django.core.management.base import BaseCommand
from django.db.models import Prefetch
from exam.models import Chapter, Question, Choice

class Command(BaseCommand):
    help = "Chapter/Question/Choice を単一JSONにエクスポートします。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="questions_export.json",
            help="出力先ファイルパス（既定: questions_export.json）",
        )
        parser.add_argument(
            "--include-excluded",
            action="store_true",
            help="is_excluded=True の問題も含める（既定は除外）。",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="整形出力（インデント付与）。",
        )

    def handle(self, *args, **opts):
        out = pathlib.Path(opts["out"]).resolve()
        include_excluded = opts["include_excluded"]
        pretty = opts["pretty"]

        # 章
        chapters = list(
            Chapter.objects.all().order_by("num").values(
                "num", "title", "official_quota"
            )
        )

        # 問題＋選択肢
        qs = Question.objects.all().order_by("id")
        if not include_excluded:
            qs = qs.filter(is_excluded=False)

        # 選択肢をまとめて取得
        qs = qs.prefetch_related(
            Prefetch("choices", queryset=Choice.objects.order_by("id"))
        )

        questions: List[Dict[str, Any]] = []
        for q in qs:
            questions.append({
                "id": q.id,
                "chapter": q.chapter.num,
                "kind": q.kind,
                "stem": q.stem,
                "note": q.note,
                "is_excluded": q.is_excluded,
                "choices": [
                    {"text": c.text, "correct": bool(c.is_correct)}
                    for c in q.choices.all()
                ],
            })

        bundle = {
            "meta": {
                "version": 1,
                "exported_items": {"chapters": len(chapters), "questions": len(questions)},
                "include_excluded": include_excluded,
            },
            "chapters": chapters,
            "questions": questions,
        }

        if pretty:
            out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            out.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Exported to {out}"))
