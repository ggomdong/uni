from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from common.models import Branch, User
from wtm.models import Work


class WorkCreateBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch_a = Branch.objects.create(code="A", name="Branch A")
        self.branch_b = Branch.objects.create(code="B", name="Branch B")
        self.user = User.objects.create_user(
            username="worker",
            password="password",
            emp_name="Worker",
            dept="Dept",
            position="Position",
            join_date=date(2024, 1, 1),
            branch=self.branch_a,
        )

    def test_work_create_forces_user_branch(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/work/",
            data={"branch": self.branch_b.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        work = Work.objects.get(user=self.user)
        self.assertEqual(work.branch_id, self.branch_a.id)
