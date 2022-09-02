from django import forms

from .models import SkillSetGroup
from .models.constants import NAMES_MAX_LENGTH


class ImportFittingForm(forms.Form):
    """Form for importing an EFT fitting."""

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
    skill_set_name = forms.CharField(
        label="New Name",
        max_length=NAMES_MAX_LENGTH,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Instead of name from fitting."}),
    )
    skill_set_group = forms.ModelChoiceField(
        label="Add to skill set group",
        required=False,
        queryset=SkillSetGroup.objects.order_by("name"),
    )


class ImportSkillPlanForm(forms.Form):
    """Form for importing a skill plan."""

    skill_plan_text = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Paste skill plan from Eve Online or Eve Mon into this field...",
                "rows": 30,
                "cols": 100,
            }
        ),
    )
    skill_set_name = forms.CharField(
        label="Name",
        max_length=NAMES_MAX_LENGTH,
        widget=forms.TextInput(attrs={"placeholder": "Name of the new skill set"}),
    )
    can_overwrite = forms.BooleanField(
        label="Overwrite skill sets with same name", required=False
    )
    skill_set_group = forms.ModelChoiceField(
        label="Add to skill set group",
        required=False,
        queryset=SkillSetGroup.objects.order_by("name"),
    )
