from django import forms
from captcha.fields import ReCaptchaField


class RegisterExternalLockerUserForm(forms.Form):
    captcha = ReCaptchaField()


class ConfirmOwnershipForm(forms.Form):
    agree_to_terms = forms.BooleanField(
        required=True,
        label='Jeg har lest og godtar brukervilkårene for bruk av bokskap'
    )
