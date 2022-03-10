from django import forms


class ImportFittingForm(forms.Form):
    fitting_text = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Paste fitting in EFT format into this field...",
                "rows": 30,
                "cols": 100,
            }
        ),
    )
    can_overwrite = forms.BooleanField(
        label="Overwrite skill sets with same name", required=False
    )
