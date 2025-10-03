# dump_utf8.py
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exam_preparation.settings")

import django

django.setup()

from django.core.management import call_command

with open("dump_20251003.json", "w", encoding="utf-8") as f:
    call_command(
        "dumpdata",
        natural_foreign=True,
        natural_primary=True,
        exclude=[
            "contenttypes",
            "auth.permission",
            "admin.logentry",
            "sessions.session",
        ],
        indent=2,
        stdout=f,  # ← UTF-8 で開いたファイルに直接出力
    )
