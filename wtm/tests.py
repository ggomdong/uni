from datetime import date
from django.utils import timezone

from django.http import QueryDict
from django.test import TestCase

from common.models import Branch, User, Holiday, Business
from wtm.services import meal_claims as svc
from wtm.services.calendar_rules import (
    get_non_business_days,
    get_non_business_weekdays,
    get_non_business_calendar,
)


class MealClaimPayloadFormServiceTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(code="S", name="Svc")
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

    def test_parse_claim_payload_form_matches_json_rules(self):
        form_data = QueryDict("", mutable=True)
        form_data.update(
            {
                "used_date": "2024-05-10",
                "merchant_name": "Store",
                "approval_no": "12345678",
                "amount": "50000",
            }
        )
        form_data.setlist("participant_user", [str(self.user.id), str(self.participant.id)])
        form_data.setlist("participant_amount", ["25000", "25000"])

        form_payload, form_errors = svc.parse_claim_payload_form(form_data, self.branch)
        self.assertEqual(form_errors, [])

        json_payload, json_errors = svc.parse_claim_payload(
            {
                "used_date": "2024-05-10",
                "merchant_name": "Store",
                "approval_no": "12345678",
                "amount": 50000,
                "participants": [
                    {"user_id": self.user.id, "amount": 25000},
                    {"user_id": self.participant.id, "amount": 25000},
                ],
            },
            self.branch,
        )
        self.assertEqual(json_errors, [])
        self.assertEqual(form_payload, json_payload)


class NonBusinessCalendarServiceTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(code="C", name="Calendar")
        self.user = User.objects.create_user(
            username="calendar-admin",
            password="password",
            emp_name="Calendar Admin",
            dept="Admin",
            position="Manager",
            join_date=date(2024, 1, 1),
            branch=self.branch,
        )
        now = timezone.now()
        Business.objects.create(
            branch=self.branch,
            stand_date=date(2024, 1, 1),
            mon="Y",
            tue="Y",
            wed="Y",
            thu="Y",
            fri="Y",
            sat="N",
            sun="N",
            reg_id=self.user,
            reg_date=now,
            mod_id=self.user,
            mod_date=now,
        )
        Holiday.objects.create(
            branch=self.branch,
            holiday=date(2024, 5, 1),  # 수요일
            holiday_name="Labor Day",
            reg_id=self.user,
            reg_date=now,
            mod_id=self.user,
            mod_date=now,
        )

    def test_calendar_result_matches_existing_functions(self):
        year, month = 2024, 5
        expected_days = get_non_business_days(year, month, branch=self.branch)
        expected_weekdays = get_non_business_weekdays(year, month, branch=self.branch)
        days, weekdays = get_non_business_calendar(year, month, branch=self.branch)

        self.assertEqual(days, expected_days)
        self.assertEqual(weekdays, expected_weekdays)
