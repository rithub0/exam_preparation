# exam_preparation/exam/urls.py

from django.urls import path  # URLパターンを定義するためのpath関数をインポート
from . import views  # 同じアプリ内のviewsモジュールをインポート

urlpatterns = [  # URLパターンのリストを定義開始
    path("", views.dashboard, name="dashboard"),  # ルートURLにアクセスしたらdashboardビューを呼び出し、名前は'dashboard'
    path("accounts/signup/", views.signup, name="signup"),  # サインアップ用URLとビューの紐付け、名前は'signup'
    # 模擬試験関連URL
    path("mock/start/", views.mock_start, name="mock_start"),  # 模擬試験開始用URL、ビューはmock_start、名前は'mock_start'
    path("mock/session/", views.mock_session, name="mock_session"),  # 模擬試験の問題回答セッション用URL、ビューはmock_session
    path("mock/result/", views.mock_result, name="mock_result"),  # 模擬試験の結果表示用URL、ビューはmock_result
]  # urlpatternsリストの終了
