from django.contrib.auth.models import User

from allauth.socialaccount.models import SocialToken
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


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