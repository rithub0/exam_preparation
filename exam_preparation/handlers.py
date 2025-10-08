from django.shortcuts import render

def handler404(request, exception):
    """
    404エラー（ページが見つからない）のハンドラー
    """
    return render(request, 'error/404.html', status=404)

def handler500(request):
    """
    500エラー（サーバーエラー）のハンドラー
    """
    return render(request, 'error/500.html', status=500)