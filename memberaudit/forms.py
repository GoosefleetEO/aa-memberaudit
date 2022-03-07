from django import forms


class ImportFittingForm(forms.Form):
    fitting_text = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Paste fitting into this field",
                "rows": 30,
                "cols": 100,
            }
        ),
        help_text="Create a new skill set from a fitting in EFT format.",
    )
