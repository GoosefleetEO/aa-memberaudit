from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.html import format_html

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__, tasks
from ..core.eft_parser import EftParserError
from ..core.fittings import Fitting
from ..forms import ImportFittingForm
from ..models import SkillSet

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


@login_required
@staff_member_required
def admin_create_skillset_from_fitting(request):
    if request.method == "POST":
        form = ImportFittingForm(request.POST)
        if form.is_valid():
            try:
                fitting, errors = Fitting.create_from_eft(
                    form.cleaned_data["fitting_text"]
                )
            except EftParserError:
                messages.warning(
                    request, "The fitting does not appear to be a valid EFT format."
                )
            else:
                skill_set_name = (
                    form.cleaned_data["skill_set_name"]
                    if form.cleaned_data["skill_set_name"]
                    else fitting.name
                )
                if (
                    not form.cleaned_data["can_overwrite"]
                    and SkillSet.objects.filter(name=skill_set_name).exists()
                ):
                    messages.warning(
                        request,
                        format_html(
                            "A skill set with the name "
                            f"<b>{fitting.name}</b> already exists."
                        ),
                    )
                else:
                    params = {"fitting": fitting, "user": request.user}
                    if form.cleaned_data["skill_set_group"]:
                        params["skill_set_group"] = form.cleaned_data["skill_set_group"]
                    if form.cleaned_data["skill_set_name"]:
                        params["skill_set_name"] = form.cleaned_data["skill_set_name"]
                    obj, created = SkillSet.objects.update_or_create_from_fitting(
                        **params
                    )
                    logger.info(
                        "Skill Set created from fitting with name: %s", fitting.name
                    )
                    tasks.update_characters_skill_checks.delay(force_update=True)
                    if created:
                        msg = f"Skill Set <b>{obj.name}</b> has been created"
                    else:
                        msg = f"Skill Set <b>{obj.name}</b> has been updated"
                    if errors:
                        msg += f" with issues:<br>- {'<br>- '.join(errors)}"
                        messages.warning(request, format_html(msg))
                    else:
                        messages.info(request, format_html(f"{msg}."))
            return redirect("admin:memberaudit_skillset_changelist")
    else:
        form = ImportFittingForm()
    return render(
        request,
        "admin/memberaudit/skillset/import_fitting.html",
        {
            "title": "Member Audit",
            "subtitle": "Create skill set from fitting",
            "form": form,
        },
    )
