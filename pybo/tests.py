from datetime import date

from django.utils import timezone

from django.test import TestCase
from django.urls import reverse

from common.models import Branch, User
from pybo.models import Question


class QuestionBranchIsolationTests(TestCase):
    def setUp(self):
        self.branch_a = Branch.objects.create(code="A", name="Branch A")
        self.branch_b = Branch.objects.create(code="B", name="Branch B")
        self.user_a = User.objects.create_user(
            username="user_a",
            password="password",
            emp_name="User A",
            dept="Dept A",
            position="Position A",
            join_date=date(2024, 1, 1),
            branch=self.branch_a,
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            password="password",
            emp_name="User B",
            dept="Dept B",
            position="Position B",
            join_date=date(2024, 1, 1),
            branch=self.branch_b,
        )

    def test_question_detail_denied_for_other_branch(self):
        question = Question.objects.create(
            author=self.user_b,
            subject="Secret",
            content="Branch B only",
            create_date=timezone.now(),
            branch=self.branch_b,
        )

        self.client.force_login(self.user_a)
        response = self.client.get(reverse("pybo:detail", args=[question.id]))

        self.assertEqual(response.status_code, 404)
