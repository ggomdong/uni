from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from common.models import User
from .models import Work, Module, Contract
from .forms import ModuleForm, ContractForm
from django.utils import timezone
import common.context_processors
import datetime
import calendar


@login_required(login_url='common:login')
def index(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/index.html', context)


@login_required(login_url='common:login')
def work_module(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
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
    context = {'form': form}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_modify(request, module_id):
    module = get_object_or_404(Module, pk=module_id)

    # if request.user != question.author:
    #     messages.error(request, '수정권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question_id)
    # 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
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
    context = {'form': form}
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
def work_contract_reg(request, user_id):
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.user_id = user_id
            contract.reg_id = request.user
            contract.reg_date = timezone.now()
            contract.mod_id = request.user
            contract.mod_date = timezone.now()
            contract.save()
            return redirect('common:user_modify', user_id=user_id)
    else:
        form = ContractForm()

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    target_user = get_object_or_404(User, pk=user_id)      # 근로계약 대상 표시를 위함
    module_list = Module.objects.all()              # 근로모듈을 요일별로 입력하기 위함
    context = {'form': form, 'target_user': target_user, 'module_list': module_list}
    return render(request, 'wtm/work_contract_reg.html', context)


@login_required(login_url='common:login')
def work_contract_modify(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    # 수정시 포맷이 달라서 기준일자가 유지되지 않는 문제 해결을 위해 포맷을 미리 지정
    contract.stand_date = contract.stand_date.strftime("%Y-%m-%d")
    user_id = contract.user_id

    # if request.user != question.author:
    #     messages.error(request, '수정권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question_id)
    # 수정화면에서 저장하기 버튼 클릭시 POST 방식으로 데이터 수정
    if request.method == 'POST':
        # 수정된 내용을 반영하기 위해, request에서 넘어온 값으로 덮어쓰라는 의미
        form = ContractForm(request.POST, instance=contract)

        if not form.has_changed():
            messages.error(request, '수정된 사항이 없습니다.')
            return redirect('wtm:work_contract_modify', module_id=contract_id)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.mod_id = request.user
            contract.mod_date = timezone.now()
            contract.save()
            return redirect('common:user_modify', user_id=user_id)
    # GET 방식으로 수정화면 호출
    else:
        # 대상이 유지되어야 하므로, instance=contract 와 같이 생성
        form = ContractForm(instance=contract)

    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    target_user = get_object_or_404(User, pk=user_id)  # 근로계약 대상 표시를 위함
    module_list = Module.objects.all()  # 근로모듈을 요일별로 입력하기 위함

    context = {'form': form, 'target_user': target_user, 'module_list': module_list}
    return render(request, 'wtm/work_contract_reg.html', context)


@login_required(login_url='common:login')
def work_contract_delete(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    user_id = contract.user_id
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    contract.delete()
    return redirect('common:user_modify', user_id=user_id)


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
def work_status(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/work_status.html', context)


@login_required(login_url='common:login')
def work_log(request):
    obj = Module.objects.all()

    context = {'work_module': obj}
    return render(request, 'wtm/work_log.html', context)

