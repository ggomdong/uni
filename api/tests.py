from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from common.models import Branch, User
from wtm.models import Work, MealClaim, MealClaimParticipant


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


class MealClaimAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(code="M", name="Main")
        self.other_branch = Branch.objects.create(code="O", name="Other")
        self.user = User.objects.create_user(
            username="owner",
            password="password",
            emp_name="Owner",
            dept="Dept",
            position="Position",
            join_date=date(2024, 1, 1),
            branch=self.branch,
        )
        self.participant = User.objects.create_user(
            username="participant",
            password="password",
            emp_name="Participant",
            dept="Dept",
            position="Position",
            join_date=date(2024, 1, 1),
            branch=self.branch,
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password",
            emp_name="Other",
            dept="Dept",
            position="Position",
            join_date=date(2024, 1, 1),
            branch=self.other_branch,
        )
        self.used_date = date(2024, 5, 10)

    def _payload(self, **overrides):
        payload = {
            "used_date": self.used_date.strftime("%Y-%m-%d"),
            "merchant_name": "Store",
            "approval_no": "12345678",
            "amount": 50000,
            "participants": [
                {"user_id": self.user.id, "amount": 25000},
                {"user_id": self.participant.id, "amount": 25000},
            ],
        }
        payload.update(overrides)
        return payload

    def test_approval_no_duplicate_returns_400(self):
        MealClaim.objects.create(
            branch=self.branch,
            user=self.user,
            used_date=self.used_date,
            amount=50000,
            approval_no="12345678",
            merchant_name="Store",
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v2/meals/claims/",
            data=self._payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error"), "validation_error")

    def test_participant_sum_mismatch_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v2/meals/claims/",
            data=self._payload(participants=[{"user_id": self.user.id, "amount": 10000}]),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error"), "validation_error")

    def test_participant_outside_branch_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v2/meals/claims/",
            data=self._payload(participants=[{"user_id": self.other_user.id, "amount": 50000}]),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("error"), "validation_error")

    def test_update_delete_permission_requires_owner(self):
        claim = MealClaim.objects.create(
            branch=self.branch,
            user=self.user,
            used_date=self.used_date,
            amount=50000,
            approval_no="87654321",
            merchant_name="Store",
        )
        MealClaimParticipant.objects.create(claim=claim, user=self.user, amount=50000)

        self.client.force_authenticate(self.participant)
        response = self.client.patch(
            f"/api/v2/meals/claims/{claim.id}/",
            data=self._payload(approval_no="11112222"),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data.get("error"), "forbidden")

        response = self.client.delete(f"/api/v2/meals/claims/{claim.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data.get("error"), "forbidden")

    def test_my_items_only_includes_participating_claims(self):
        claim_a = MealClaim.objects.create(
            branch=self.branch,
            user=self.user,
            used_date=self.used_date,
            amount=50000,
            approval_no="22223333",
            merchant_name="Store",
        )
        MealClaimParticipant.objects.create(claim=claim_a, user=self.user, amount=25000)
        MealClaimParticipant.objects.create(claim=claim_a, user=self.participant, amount=25000)

        claim_b = MealClaim.objects.create(
            branch=self.branch,
            user=self.participant,
            used_date=self.used_date,
            amount=30000,
            approval_no="33334444",
            merchant_name="Store2",
        )
        MealClaimParticipant.objects.create(claim=claim_b, user=self.participant, amount=30000)

        self.client.force_authenticate(self.user)
        response = self.client.get(
            "/api/v2/meals/my/items/",
            data={"ym": "202405"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("items", [])), 1)
