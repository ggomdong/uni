from django.http import Http404, HttpResponseForbidden
from common.models import Branch


def _extract_branch_code(request) -> str | None:
    # 1) nginx가 넣는 헤더 우선
    code = request.headers.get("X-Branch-Code")
    if code:
        return code.strip().lower()

    # 2) host 서브도메인: wsnuni.medihr.co.kr -> wsnuni
    host = request.get_host().split(":")[0].lower()
    if host.endswith(".medihr.co.kr") and host != "medihr.co.kr":
        return host.split(".")[0]

    return None


class BranchGuardMiddleware:
    """
    - 비로그인: 요청 지점코드로 request.branch 세팅
    - 로그인: user.branch와 요청 지점코드 불일치면 403 (타 지점 로그인/접근 차단)
    """

    # 지점 강제가 필요 없는 경로만 최소로 예외 처리
    EXEMPT_PREFIXES = (
        "/static/",
        "/favicon.ico",
        "/admin/",   # 원하면 admin도 지점 강제할 수 있지만 보통은 예외로 둠
        "/api/"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)

        req_code = _extract_branch_code(request)

        # 지점코드가 없으면 접근 불가 (루트 도메인은 nginx에서 mogglab으로 빠지므로 정상 플로우)
        if not req_code:
            raise Http404("branch code is required")

        # 로그인 사용자면: 본인 지점과 불일치 시 차단
        if request.user.is_authenticated:
            user_branch = getattr(request.user, "branch", None)
            if user_branch and user_branch.code != req_code:
                return HttpResponseForbidden(
                    "접속한 지점과 계정의 소속 지점이 다릅니다. 올바른 지점 주소로 접속해 주세요."
                )
            request.branch = user_branch
            return self.get_response(request)

        # 비로그인은 req_code로 branch 지정
        try:
            request.branch = Branch.objects.get(code=req_code, is_active=True)
        except Branch.DoesNotExist:
            raise Http404("invalid branch")

        return self.get_response(request)
