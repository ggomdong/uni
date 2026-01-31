import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from ..models import Module
from ..forms import ModuleForm


@login_required(login_url='common:login')
def work_module(request):
    obj = Module.objects.filter(branch=request.user.branch).order_by('order', 'id')

    context = {'work_module': obj}
    return render(request, 'wtm/work_module.html', context)


@login_required(login_url='common:login')
def work_module_reorder(request):
    payload = json.loads(request.body.decode('utf-8'))
    ids = payload.get('ids', [])

    if not isinstance(ids, list) or not ids:
        return JsonResponse({'ok': False, 'msg': 'invalid ids'}, status=400)

    with transaction.atomic():
        qs = Module.objects.select_for_update().filter(id__in=ids, branch=request.user.branch)

        # 멀티테넌시/사업장 범위가 있으면 반드시 제한
        # qs = qs.filter(branch=request.user.branch)

        found = set(qs.values_list('id', flat=True))
        if len(found) != len(ids):
            return JsonResponse({'ok': False, 'msg': 'some ids not found'}, status=400)

        for idx, mid in enumerate(ids, start=1):
            Module.objects.filter(id=mid, branch=request.user.branch).update(order=idx)

    return JsonResponse({'ok': True})


@login_required(login_url='common:login')
def work_module_reg(request):
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.branch = request.user.branch
            module.reg_id = request.user
            module.reg_date = timezone.now()
            module.mod_id = request.user
            module.mod_date = timezone.now()
            module.save()
            messages.success(request, "근로모듈을 등록했습니다.")
            return redirect('wtm:work_module')
    else:
        form = ModuleForm()
    # POST방식이지만 form에 오류가 있거나, GET방식일때 아래로 진행
    context = {'form': form}
    return render(request, 'wtm/work_module_reg.html', context)


@login_required(login_url='common:login')
def work_module_modify(request, module_id):
    module = get_object_or_404(Module, pk=module_id, branch=request.user.branch)

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
            messages.success(request, "근로모듈을 수정했습니다.")
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
    module = get_object_or_404(Module, pk=module_id, branch=request.user.branch)
    # if request.user != question.author:
    #     messages.error(request, '삭제 권한이 없습니다.')
    #     return redirect('pybo:detail', question_id=question.id)
    module.delete()
    messages.success(request, "근로모듈을 삭제했습니다.")
    return redirect('wtm:work_module')
