from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.utils import timezone
from post_office.models import Email

from lockers.management.commands.final_warning import issue_final_warnings
from lockers.models import LOCKER_COUNT
from lockers.models import LockerUser, Locker, LockerToken, Ownership
from lockers.management.commands.resetlockerstatus import reset_locker_ownerships


def create_user_with_locker(count):
    user = User.objects.create(first_name="Glenn", last_name="Gregor", email="glenny@test.no", username="glenny")
    locker_user = LockerUser.objects.create(user=user)
    for i in range(count):
        locker = Locker.objects.create(number=i)
        ownership = Ownership.objects.create(locker=locker, user=locker_user)
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()


class LockerUserLimitTest(TestCase):
    def setUp(self):
        create_user_with_locker(LOCKER_COUNT - 1)

    def test_not_reached_limit(self):
        ownership = Ownership.objects.filter(user__user__email="glenny@test.no")[0]
        self.assertEqual(ownership.reached_limit(), False)

    def test_reached_limit(self):
        ownership = Ownership.objects.filter(user__user__email="glenny@test.no")[0]
        user = ownership.user

        locker = Locker.objects.create(number=LOCKER_COUNT)
        ownership = Ownership.objects.create(locker=locker, user=user)
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()

        self.assertEqual(ownership.reached_limit(), True)


class TokenTest(TestCase):
    # Fetch all templates for sending mail
    fixtures = ["fixtures/email-templates.json", "fixtures/sites.json"]

    def setUp(self):
        user_one = User.objects.create(
            first_name="Glenn", last_name="Gregor", email="glenny@test.no", username="glenny"
        )

        locker_user = LockerUser.objects.create(user=user_one)

        user_two = User.objects.create(first_name="Stale", last_name="Staler", email="stale@test.no", username="stale")

        locker_user2 = LockerUser.objects.create(user=user_two)

        locker = Locker.objects.create(number=1)
        self.ownership = Ownership.objects.create(locker=locker, user=locker_user)
        self.disabled_ownership = Ownership.objects.create(locker=locker, user=locker_user2)

    def test_locker_inactive(self):
        locker = Locker.objects.get(number=1)
        ownership = self.ownership
        self.assertEqual(locker.is_free(), True)
        self.assertEqual(ownership.is_active, False)
        self.assertEqual(ownership.is_confirmed, False)

    def test_locker_taken(self):
        ownership = self.ownership
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()

        ownership.refresh_from_db()
        locker = Locker.objects.get(number=1)

        self.assertEqual(locker.is_free(), False)
        self.assertEqual(ownership.is_active, True)
        self.assertEqual(ownership.is_confirmed, True)
        self.assertEqual(token.pk, None)

    def test_prune_expired(self):
        ownership = self.ownership
        token = LockerToken.objects.create(ownership=ownership)
        # Locker was tried taken without confirming 8 days ago
        token.created = timezone.now() - timedelta(days=8)
        token.save()
        LockerToken.objects.prune_expired()
        # Try to get the recently pruned locker token,
        # but it raises an object does not exist since it was just pruned.
        self.assertRaises(ObjectDoesNotExist, LockerToken.objects.get, ownership=ownership)

    def test_reset_idle(self):
        locker = Locker.objects.get(number=1)
        user = LockerUser.objects.get(user__email="glenny@test.no")
        ownership = Ownership.objects.get(locker=locker, user=user)
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()

        ownership.refresh_from_db()
        ownership.is_active = False
        ownership.save()
        Locker.objects.reset_idle()
        locker.refresh_from_db()
        self.assertEqual(locker.owner, None)
        self.assertEqual(locker.number, 1)
        self.assertEqual(user.user.email, "glenny@test.no")
        self.assertEqual(ownership.locker.number, 1)
        self.assertEqual(ownership.user.user.email, "glenny@test.no")

    def test_active_locker_user_kept_after_reset(self):
        locker = Locker.objects.get(number=1)
        user = LockerUser.objects.get(user__email="glenny@test.no")
        ownership = Ownership.objects.get(locker=locker, user=user)
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()

        Locker.objects.reset_idle()
        locker.refresh_from_db()
        self.assertEqual(locker.owner, ownership)

    def test_reset_locker_ownerships(self):
        # Fetch locker, user, ownership and attach locker <=> ownership
        locker = Locker.objects.get(number=1)
        user = LockerUser.objects.get(user__email="glenny@test.no")
        ownership = Ownership.objects.get(locker=locker, user=user)
        token = LockerToken.objects.create(ownership=ownership)
        token.activate()
        locker.refresh_from_db()
        ownership.refresh_from_db()
        # Check if ownership points to locker and vice versa
        self.assertEqual(locker.owner, ownership)
        self.assertEqual(ownership.locker, locker)
        self.assertEqual(ownership.is_active, True)
        self.assertEqual(ownership.is_confirmed, True)

        # Try to cut the link from ownership to locker
        # (set is_active = False)
        reset_locker_ownerships()
        locker.refresh_from_db()
        user.refresh_from_db()
        ownership.refresh_from_db()
        # Check if the only change made was cutting ownership to locker
        # (is_active = False)
        self.assertEqual(ownership.is_active, False)
        self.assertEqual(ownership.is_confirmed, True)
        self.assertEqual(locker.owner, ownership)
        self.assertEqual(ownership.locker, locker)

        token = LockerToken.objects.get(ownership=ownership)
        token.activate()
        ownership.refresh_from_db()
        self.assertEqual(ownership.is_active, True)
        self.assertEqual(ownership.is_confirmed, True)
        self.assertEqual(locker.owner, ownership)
        self.assertEqual(ownership.locker, locker)


class EmailTest(TestCase):
    # Fetch all templates for sending mail
    fixtures = ["fixtures/email-templates.json", "fixtures/sites.json"]

    def setUp(self):
        user = User.objects.create(first_name="Glenn", last_name="Gregor", email="glenny@test.no", username="glenny")
        locker_user = LockerUser.objects.create(user=user)
        locker = Locker.objects.create(number=1)
        self.ownership = Ownership.objects.create(locker=locker, user=locker_user)
        LockerToken.objects.create(ownership=self.ownership).activate()

    def test_email_activations(self):
        """
        Assert that activation links are present in activation emails.
        Checks that reset_locker_ownerships and issue_final_warnings can send
        valid emails.
        """
        # Reset locker status
        reset_locker_ownerships()
        token = LockerToken.objects.get(ownership=self.ownership)
        activation_link = f"hc.ntnu.no/bokskap/aktiver/{token.key}"

        # Initial reset contains activation link
        initial_email = Email.objects.first()
        self.assertEqual(initial_email.subject, "Vil du beholde bokskap # 1?")
        self.assertIn(activation_link, initial_email.message)
        self.assertIn(activation_link, initial_email.html_message)

        # Issue final warning
        issue_final_warnings()

        # Final warning contains activation link
        final_email = Email.objects.last()
        self.assertEqual(final_email.subject, "Skap #1 klippes og tømmes snart!")
        self.assertIn(activation_link, final_email.message)
        self.assertIn(activation_link, final_email.html_message)
