from django.http import Http404


def get_branch_or_404(request):
    branch = getattr(request, "branch", None)
    if branch is None:
        raise Http404("branch code is required")
    return branch
