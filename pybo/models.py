from django.db import models
from common.models import User, Branch


class Question(models.Model):
    # author, voter가 모두 User를 참조하므로, User.question_set 이라고 하면 뭘 기준으로 할지 모호함
    # 따라서, related_name을 정의하여 해결
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='author_question')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    create_date = models.DateTimeField()
    # null : null 허용여부, blank : 데이터 검증 시 값이 없어도 되는지 여부
    modify_date = models.DateTimeField(null=True, blank=True)
    voter = models.ManyToManyField(User, related_name='voter_question')    # 추천인
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="questions",
        db_index=True,
    )

    def __str__(self):
        return self.subject


class Answer(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='author_answer')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.TextField()
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField(null=True, blank=True)
    voter = models.ManyToManyField(User, related_name='voter_answer')
    branch = models.ForeignKey(
        Branch,
        verbose_name="지점",
        on_delete=models.PROTECT,
        related_name="answers",
        db_index=True,
    )
