from django.db import models
from common.models import User


class Work(models.Model):
    username = models.ForeignKey(User, on_delete=models.PROTECT)
    work_code = models.CharField(max_length=1)
    record_date = models.DateTimeField()