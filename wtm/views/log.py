from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import datetime

from common.models import User
from common import context_processors
from ..models import Work
from ..forms import WorkForm
from .helpers import fetch_log_users_for_day


@login_required(login_url='common:login')
def work_log(request, stand_day=None):
    branch = request.user.branch
    # 0) 검색어
    kw = request.GET.get("kw", "").strip()

    # 1) 기준일 값이 없으면 현재로 세팅
    if stand_day is None:
        target_date = datetime.today()
        stand_day = target_date.strftime('%Y%m%d')
    else:
        # 'YYYYMMDD' → date 로 변환 및 유효성 검사
        try:
            target_date = datetime.strptime(stand_day, '%Y%m%d').date()
        except ValueError:
            messages.error(request, "잘못된 날짜 형식입니다.")
            return redirect('wtm:work_log')

    days = context_processors.get_days_korean(stand_day)

    # 2) 해당 날짜 근태기록
    log_list = (
        Work.objects
        .filter(record_day=target_date, branch=branch)
        .select_related('user')
        .order_by('-record_date')  # 최신 기록이 위로
    )

    # 직원명 검색 (emp_name 기준)
    if kw:
        log_list = log_list.filter(user__emp_name__icontains=kw)

    # 3) 모달에서 쓸 '대상 직원 목록' (RAW SQL)
    try:
        user_list = fetch_log_users_for_day(stand_day, branch=branch)
    except Exception as e:
        messages.warning(request, f"대상 직원 조회 중 오류가 발생했습니다. ({e})")
        user_list = []

    context = {
        'stand_day': stand_day,
        'days': days,
        'target_date': target_date,
        'log_list': log_list,
        'user_list': user_list,
        'kw': kw,
    }
    return render(request, 'wtm/work_log.html', context)


@login_required(login_url='common:login')
def work_log_save(request):
    if request.method != 'POST':
        messages.error(request, "잘못된 요청입니다.")
        return redirect('wtm:work_log')

    log_id = request.POST.get("log_id")
    stand_day = request.POST.get("stand_day")

    if not stand_day:
        messages.error(request, "일자를 확인해 주세요.")
        return redirect(
            'wtm:work_log',
            stand_day=stand_day or timezone.now().strftime('%Y%m%d'),
        )

    # 기준일 검증
    try:
        datetime.strptime(stand_day, "%Y%m%d")
    except ValueError:
        messages.error(request, "잘못된 날짜 형식입니다.")
        return redirect('wtm:work_log')

    # ─────────────────────────────────────
    # 1) 수정 / 등록 분기
    #    - 수정: user_id는 무시, 기존 obj.user 유지
    #    - 등록: user_id 필수
    # ─────────────────────────────────────

    # 수정모드
    if log_id:
        obj = get_object_or_404(Work, pk=log_id, branch=request.user.branch)
        form = WorkForm(request.POST, instance=obj)
    else:
        user_id = request.POST.get("user_id")
        if not user_id:
            messages.error(request, "직원을 선택해 주세요.")
            return redirect('wtm:work_log', stand_day=stand_day)

        target_user = get_object_or_404(User, pk=user_id, branch=request.user.branch)
        obj = Work(user=target_user)
        form = WorkForm(request.POST, instance=obj)

    if not form.is_valid():
        messages.error(request, "입력값을 확인해 주세요.")
        return redirect('wtm:work_log', stand_day=stand_day)

    obj = form.save(commit=False)

    # record_date = stand_day + record_time
    record_time = form.cleaned_data["record_time"]  # datetime.time
    dt_str = f"{stand_day} {record_time.strftime('%H:%M:%S')}"
    obj.record_date = datetime.strptime(dt_str, "%Y%m%d %H:%M:%S")

    # Work 모델의 pre_save 시그널에서 record_day = record_date.date() 자동 세팅
    if not log_id:
        obj.user = target_user
        obj.branch = request.user.branch
    obj.save()

    messages.success(request, "근태기록이 저장되었습니다.")

    # 어느 화면을 통해서 요청이 왔는지에 따라 리다이렉트 분기
    from_index = request.POST.get("from_index") == "1"

    print(from_index)

    if from_index:
        # Today 화면으로
        return redirect('wtm:index', stand_day)
    else:
        # 근테기록-일별상세 화면으로
        return redirect('wtm:work_log', stand_day)


@login_required(login_url='common:login')
def work_log_delete(request, log_id: int):
    log = get_object_or_404(Work, pk=log_id, branch=request.user.branch)
    stand_day = log.record_day.strftime('%Y%m%d')

    if request.method == "POST":
        log.delete()
        messages.success(request, "근태기록이 삭제되었습니다.")
    else:
        messages.error(request, "잘못된 요청입니다.")

    return redirect('wtm:work_log', stand_day=stand_day)
