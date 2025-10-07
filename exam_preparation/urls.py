# exam_preparation/exam_preparation/urls.py

"""
URL configuration for exam_preparation project.  # exam_preparationプロジェクトのURL設定ファイルの説明コメント

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin  # 管理サイト用モジュールのインポート
from django.urls import path, include  # URLパターン作成のためのpath関数と、他のURL設定を読み込むinclude関数をインポート

urlpatterns = [  # URLパターンのリストを定義開始
    path("admin/", admin.site.urls),  # 管理サイトのURLにアクセスした場合に管理画面のURL設定を読み込む
    path("accounts/", include("django.contrib.auth.urls")),  # Djangoの標準認証機能（ログイン・ログアウト等）のURL設定を読み込む
    path("", include("exam.urls")),  # ルートURL以下のパスはexamアプリのurls.pyで処理させる
]  # urlpatternsリストの終了
