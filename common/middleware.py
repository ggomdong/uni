from django.http import Http404, HttpResponseRedirect
from django.contrib.auth import logout
from django.utils.http import urlencode
from common.models import Branch


RESERVED_SUBDOMAINS = {"dev", "stg", "stage", "www", "admin"}


def _get_host_no_port(request) -> str:
    return request.get_host().split(":")[0].lower()


def _extract_branch_code(request) -> str | None:
    # 1) nginx가 넣는 헤더 우선
    code = request.headers.get("X-Branch-Code")
    if code is not None:
        c = code.strip().lower()
        if c:  # 빈 문자열이면 무시하고 host 파싱으로
            return c

    host = _get_host_no_port(request)

    # 2) 로컬: ydpuni.localhost -> ydpuni
    if host.endswith(".localhost") and host != "localhost":
        sub = host.split(".")[0]
        return None if sub in RESERVED_SUBDOMAINS else sub

    # 3) 운영: ydpuni.medihr.co.kr -> ydpuni
    if host.endswith(".medihr.co.kr") and host != "medihr.co.kr":
        sub = host.split(".")[0]
        return None if sub in RESERVED_SUBDOMAINS else sub

    return None


def _build_branch_host_for_user(request, user_branch_code: str) -> str | None:
    """
    현재 접속 환경(prod/dev/local)을 유지하면서 '올바른 지점 host'를 만든다.
    - ydpuni.dev.medihr.co.kr -> {user}.dev.medihr.co.kr
    - ydpuni.medihr.co.kr     -> {user}.medihr.co.kr
    - ydpuni.localhost        -> {user}.localhost
    """
    host = _get_host_no_port(request)

    if host.endswith(".dev.medihr.co.kr") or host == "dev.medihr.co.kr":
        return f"{user_branch_code}.dev.medihr.co.kr"

    if host.endswith(".medihr.co.kr"):
        return f"{user_branch_code}.medihr.co.kr"

    if host.endswith(".localhost") or host == "localhost":
        return f"{user_branch_code}.localhost"

    # 기타 도메인(예: 레거시 wsnuni.co.kr)은 여기서 None 처리하고 상위에서 fallback
    return None


class BranchGuardMiddleware:
    """
    - 비로그인: 요청 지점코드로 request.branch 세팅
    - 로그인: user.branch와 요청 지점코드 불일치면 로그아웃 + 올바른 지점으로 리다이렉트
    """

    EXEMPT_PREFIXES = (
        "/static/",
        "/favicon.png",
        "/admin/",
        "/api/",
        "/wtm/privacy/",
    )

    # 지점코드가 없더라도 허용할 "포털 host" (dev 포털 등)
    PORTAL_HOSTS = {
        "dev.medihr.co.kr",
        "localhost",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)

        host = _get_host_no_port(request)
        req_code = _extract_branch_code(request)

        # 지점코드가 없는 경우:
        # - dev.medihr.co.kr 같은 포털은 허용(추후 지점선택 페이지 등)
        # - 그 외는 기존대로 차단(404)
        if not req_code:
            if host in self.PORTAL_HOSTS:
                request.branch = None
                return self.get_response(request)
            raise Http404("branch code is required")

        # 로그인 사용자면: 본인 지점과 불일치 시 "로그아웃 + 리다이렉트"
        if request.user.is_authenticated:
            user_branch = getattr(request.user, "branch", None)

            if user_branch and user_branch.code != req_code:
                # 1) 세션 종료 (멈춤 상태 방지)
                logout(request)

                # 2) 올바른 지점으로 이동 (환경 유지)
                target_host = _build_branch_host_for_user(request, user_branch.code)

                # 3) fallback: host를 못 만들면 그냥 /로 (nginx가 처리)
                scheme = "https"  # 운영 기준. 필요하면 request.is_secure()로 분기 가능
                if not target_host:
                    target_url = "/"
                else:
                    qs = urlencode({"err": "branch_mismatch"})
                    target_url = f"{scheme}://{target_host}/?{qs}"

                return HttpResponseRedirect(target_url)

            request.branch = user_branch
            return self.get_response(request)

        # 비로그인은 req_code로 branch 지정
        try:
            request.branch = Branch.objects.get(code=req_code, is_active=True)
        except Branch.DoesNotExist:
            raise Http404("invalid branch")

        return self.get_response(request)
