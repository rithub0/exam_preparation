from __future__ import annotations
import json
import pathlib
from typing import Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from exam.models import Chapter, Question, Choice

class Command(BaseCommand):
    help = "export_questions で出力した単一JSONバンドルをインポートします。"

    def add_arguments(self, parser):
        parser.add_argument("bundle", help="エクスポートJSONファイルのパス")
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="インポート前に既存の Question/Choice を全削除（Chapterは上書き更新）。",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = pathlib.Path(opts["bundle"]).resolve()
        if not path.exists():
            raise CommandError(f"ファイルが見つかりません: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        if "chapters" not in data or "questions" not in data:
            raise CommandError("不正なバンドル形式です（chapters, questions が必要）。")

        chapters = data["chapters"]
        questions = data["questions"]

        # Chapter を作成/更新
        # 既存は残しつつ、num が一致するものは上書き
        for ch in chapters:
            num = int(ch["num"])
            title = str(ch.get("title", f"Chapter {num}"))
            quota = int(ch.get("official_quota", 0))
            Chapter.objects.update_or_create(
                num=num,
                defaults={"title": title, "official_quota": quota},
            )

        if opts["wipe"]:
            self.stdout.write(self.style.WARNING("WIPING existing questions..."))
            Choice.objects.all().delete()
            Question.objects.all().delete()

        created = 0
        for q in questions:
            ch_num = int(q["chapter"])
            kind = str(q["kind"])
            stem = str(q["stem"])
            note = str(q.get("note", ""))
            is_excluded = bool(q.get("is_excluded", False))
            choices = q.get("choices", [])
            if not choices:
                raise CommandError("choices が空の問題があります。")

            ch = Chapter.objects.filter(num=ch_num).first()
            if not ch:
                raise CommandError(f"章が見つかりません: chapter={ch_num}")

            new_q = Question.objects.create(
                chapter=ch, kind=kind, stem=stem, note=note, is_excluded=is_excluded
            )
            for c in choices:
                Choice.objects.create(
                    question=new_q,
                    text=str(c["text"]),
                    is_correct=bool(c["correct"])
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported bundle: Chapters={len(chapters)} (upsert), Questions={created}"
        ))
