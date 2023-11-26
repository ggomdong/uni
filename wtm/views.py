from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Work


def work_list(request):
    work = get_object_or_404(Work, pk=work_id)
    context = {'work': work}
    return render(request, 'wtm/work_manager.html', context)
