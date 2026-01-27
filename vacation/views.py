from datetime import datetime
from django.utils import timezone
from django.shortcuts import render


def ledger(request, stand_ym=None):
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")

    # UI 협의 단계이므로, 지금은 stand_ym만 내려주고 템플릿에서 화면만 잡아도 충분
    context = {
        "stand_ym": stand_ym,
        # "kw": request.GET.get("kw", ""),  # 필요시
        # "ledger": ...                    # 이후 로직 붙일 자리
    }
    return render(request, "vacation/ledger.html", context)

def approvals(request, stand_ym=None):
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    return render(request, "vacation/approvals.html", {"stand_ym": stand_ym})

def resignation(request, stand_ym=None):
    stand_ym = stand_ym or timezone.now().strftime("%Y%m")
    return render(request, "vacation/resignation.html", {"stand_ym": stand_ym})

def settings(request):
    return render(request, "vacation/settings.html")
