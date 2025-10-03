# practicum/exam/management/commands/import_questions.py
from __future__ import annotations
import json
import pathlib
from typing import Iterable, List, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exam.models import Chapter, Question, Choice

# 公式クォータ（40問配分）— Chapter 作成時の official_quota に反映
CHAPTER_QUOTA = {
    1:1,  2:2,  3:7,  4:3,  5:2,  6:4,  7:0,  8:2,  9:5,  10:2,
    11:2, 12:0, 13:2, 14:2, 15:0, 16:3, 17:2, 18:1, 19:0
}

def _iter_question_objects_from_file(path: pathlib.Path) -> Iterable[Dict[str, Any]]:
    """
    JSON は単一オブジェクト or 配列のどちらでもOK。
    必須キー：chapter(int), kind(str), stem(str), choices(list[{text,correct}])
    任意キー：note(str), is_excluded(bool)
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for obj in data:
            yield obj
    else:
        yield data

class Command(BaseCommand):
    help = "exam/data/questions/*.json から Chapter/Question/Choice を投入します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default="practicum/exam/data/questions",
            help="問題JSONを格納したディレクトリ（既定: practicum/exam/data/questions）",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="投入前に既存の Question/Choice を全削除します（Chapterは保持）。",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        qdir = pathlib.Path(options["dir"]).resolve()
        if not qdir.exists():
            raise CommandError(f"ディレクトリが見つかりません: {qdir}")

        # Chapter の下地を作成（存在しなければ）
        for num, quota in CHAPTER_QUOTA.items():
            Chapter.objects.get_or_create(
                num=num,
                defaults={"title": f"Chapter {num}", "official_quota": quota},
            )
        # 既存 Chapter の official_quota を最新に揃える
        for num, quota in CHAPTER_QUOTA.items():
            Chapter.objects.filter(num=num).update(official_quota=quota)

        if options["wipe"]:
            self.stdout.write(self.style.WARNING("WIPING existing questions..."))
            Choice.objects.all().delete()
            Question.objects.all().delete()

        files = sorted(qdir.glob("*.json"))
        if not files:
            raise CommandError(f"JSONファイルがありません: {qdir}/*.json")

        created_q = 0
        for f in files:
            for obj in _iter_question_objects_from_file(f):
                try:
                    ch_num = int(obj["chapter"])
                    kind = str(obj["kind"])
                    stem = str(obj["stem"])
                    choices = obj["choices"]
                except KeyError as e:
                    raise CommandError(f"{f.name}: 必須キーが不足しています: {e}")

                note = str(obj.get("note", ""))
                is_excluded = bool(obj.get("is_excluded", False))

                # Chapter を取得（無ければ作成）
                ch, _ = Chapter.objects.get_or_create(
                    num=ch_num,
                    defaults={"title": f"Chapter {ch_num}", "official_quota": CHAPTER_QUOTA.get(ch_num, 0)},
                )

                # 同一 stem の重複を避けたい場合は get_or_create に切替可能
                q = Question.objects.create(
                    chapter=ch,
                    kind=kind,
                    stem=stem,
                    note=note,
                    is_excluded=is_excluded,
                )
                # choices
                if not isinstance(choices, list) or not choices:
                    raise CommandError(f"{f.name}: choices は非空リストである必要があります。")
                for c in choices:
                    Choice.objects.create(
                        question=q,
                        text=str(c["text"]),
                        is_correct=bool(c["correct"]),
                    )

                created_q += 1

        self.stdout.write(self.style.SUCCESS(f"Imported: Question {created_q}件"))
