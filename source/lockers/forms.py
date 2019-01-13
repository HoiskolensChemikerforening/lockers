from django import forms


class ConfirmOwnershipForm(forms.Form):
    agree_to_terms = forms.BooleanField(
        required=True,
        label='Jeg har lest og godtar brukervilkårene for bruk av bokskap'
    )
