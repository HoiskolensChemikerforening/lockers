from allauth.account.signals import user_signed_up, user_logged_in
from allauth.socialaccount.signals import social_account_added
from dataporten.models import DataportenUser
from django.contrib.auth.models import User

from allauth.socialaccount.models import SocialToken, SocialAccount
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db.models.signals import post_save
from django.dispatch import receiver

from lockers.models import LockerUser


def allauth_token(user: User) -> str:
    return SocialToken.objects.get(
        account__user=user,
        account__provider='dataporten',
    ).token


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).
        We're trying to solve different use cases:
        - social account already exists, just go on
        - social account's username exists, link social account to existing user
        """

        # Ignore existing social accounts, just do this stuff for new ones
        if sociallogin.is_existing:
            return

        # Get existing user by username
        try:
            user = User.objects.get(username=sociallogin.user.username)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)


@receiver(user_logged_in)
def check_active_it_aff1(sender, request=None, user=None, **kwargs):
    if DataportenUser.valid_request(request):
        request.user.__class__ = DataportenUser
    else:
        return

    locker_user, created = LockerUser.objects.get_or_create(user=request.user)
    if created:
        study_programs = request.user.dataporten.study_programs
        study_programs = [f'{i.code}: {i.name}' for i in study_programs.values()]
        study_programs = ', '.join(study_programs)
        locker_user.study_programs = study_programs
        locker_user.save()
