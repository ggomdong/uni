from django.shortcuts import render

def work_privacy(request):
    branch = getattr(request.user, "branch", None) if request.user.is_authenticated else None
    branch_name = branch.name if branch else None

    context = {
        "branch_name": branch_name,
    }
    return render(request, "wtm/privacy.html", context)
