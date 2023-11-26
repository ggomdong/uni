from django.contrib.auth import authenticate
from common.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser  # json 형식으로 오는 request에 대한 parsing을 위한 라이브러리
from wtm.models import Work

from .serializers import UserSerializer, WorkSerializer


@csrf_exempt
def user_list(request):
    if request.method == 'GET':
        query_set = User.objects.all()
        # 다수의 query_set 형태를 serialize 할때는 many=True 사용
        serializer = UserSerializer(query_set, many=True)
        # 데이터 유형과 무관하게 return 하기 위해 safe=False 사용
        return JsonResponse(serializer.data, safe=False)

    # POST의 경우, Postman에서 테스트할때 Param이 아닌 Body-raw-JSON으로 send 해야 함
    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.error, status=400)

@csrf_exempt
def user(request, username):
    # username(사번)을 기준으로 처리
    obj = User.objects.get(username=username)

    if request.method == 'GET':
        serializer = UserSerializer(obj)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = UserSerializer(obj, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.error, status=400)

    elif request.method == 'DELETE':
        obj.delete()
        return HttpResponse(status=204)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        username = data['username']
        password = data['password']

        login_result = authenticate(username=username, password=password)

        # 앱에서 로그인시 사용자 정보를 가져오기 위함
        # TODO: 출결 여부를 return 하는 부분 추가
        obj = User.objects.get(username=username)

        if login_result:
            return JsonResponse({'code': '0000', 'username': obj.username, 'emp_name': obj.emp_name}, status=200)
        else:
            return JsonResponse({'code': '0001', 'msg': '로그인 실패'}, status=401)


@csrf_exempt
def work_record(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)

        # Work.username은 User테이블을 참조하고 있으므로, User테이블에서 먼저 user정보를 가져와서 매핑해줘야 함
        obj = User.objects.get(username=data['username'])
        work = Work()

        # work와 user 매핑
        work.username_id = obj.id
        work.work_code = data['work_code']
        work.record_date = timezone.now()

        work.save()
        return HttpResponse(status=204)