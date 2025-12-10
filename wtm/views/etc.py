from django.shortcuts import render

from ..models import Branch

def work_privacy(request):
    branch_code = request.GET.get("branch")
    branch_name = None

    if branch_code:
        branch = Branch.objects.filter(code=branch_code).first()
        if branch:
            branch_name = branch.name

    context = {
        "branch_name": branch_name,
    }
    return render(request, "wtm/privacy.html", context)
