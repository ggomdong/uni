from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from common.models import User
from .models import Work, Module
from .forms import ModuleForm
from django.utils import timezone
import datetime
import calendar

weekday = ['월', '화', '수', '목', '금', '토', '일']
categories = ['정규근무', '탄력근무', '휴일근무']
times = ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00',
         '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
         '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00',
         '21:30', '22:00', '22:30', '23:00', '23:30']
module_colors = {
    1: 'crimson',
    2: 'orange',
    3: 'yellow',
    4: 'limegreen',
    5: 'skyblue',
    6: 'cornflowerblue',
    7: 'slateblue',
    8: 'darkkhaki',
    9: 'violet',
    10: 'teal',
    11: 'white',
}


@login_required(login_url='common:login')
def work_list(request):
    obj = Work.objects.select_related('user').filter().values('user__username', 'user__emp_name', 'work_code', 'record_date')
    year = 2023
    month = 2
    maxday = calendar.monthrange(year, month)[1]
    day = weekday[calendar.monthrange(year, month)[0]]
    print(maxday)
    print(day)
    # for day in datetime.datetime.date(2023, 11):
    #     print(day)
    # for i in obj:
    #     print(i['record_date'].strftime('%H%M'))

    context = {'work_list': obj}
    return render(request, 'wtm/work_list.html', context)


@login_required(login_url='common:login')
def work_module(request):
    obj = Module.objects.all()

    context = {'work_module': obj, 'module_colors': module_colors}
    return render(request, 'wtm/work_module.html', context)


@login_required(login_url='common:login')
def work_module_reg(request):
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.reg_id = request.user
            module.reg_date = timezone.now()
            module.mod_id = request.user
            module.mod_date = timezone.now()
            module.save()
            return redirect('wtm:work_module')
    else:
        form = ModuleForm()
    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form, 'module_colors': module_colors, 'categories': categories,
               'times': times}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_modify(request, module_id):
    module = get_object_or_404(Module, pk=module_id)

    # if request.user != question.author:
    #     messages.error(request, '수정권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question_id)
    # 수정화면에서 등록하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = ModuleForm(request.POST, instance=module)

        if not form.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('wtm:work_module_modify', module_id=module_id)
        if form.is_valid():
            module = form.save(commit=False)
            module.mod_id = request.user
            module.mod_date = timezone.now()
            module.save()
            return redirect('wtm:work_module')
    # GET 방식으로 수정화면 호출
    else:
        # 대상이 유지되어야 하므로, instance=module 과 같이 생성
        form = ModuleForm(instance=module)

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form, 'module_colors': module_colors, 'categories': categories,
               'times': times}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_delete(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    module.delete()
    return redirect('wtm:work_module')


@login_required(login_url='common:login')
def work_status(request):
    pass
    return


@login_required(login_url='common:login')
def work_log(request):
    pass
    return

