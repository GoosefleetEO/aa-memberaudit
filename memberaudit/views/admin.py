from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.html import format_html

from allianceauth import NAME as site_header
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__, tasks
from ..forms import ImportFittingForm, ImportSkillPlanForm
from ..models import SkillSet

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


@login_required
@staff_member_required
def admin_create_skillset_from_fitting(request):
    if request.method == "POST":
        form = ImportFittingForm(request.POST)
        if form.is_valid():
            fitting = form.cleaned_data["_fitting"]
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
                obj, created = SkillSet.objects.update_or_create_from_fitting(**params)
                logger.info(
                    "Skill Set created from fitting with name: %s", fitting.name
                )
                tasks.update_characters_skill_checks.delay(force_update=True)
                if created:
                    msg = f"Skill Set <b>{obj.name}</b> has been created"
                else:
                    msg = f"Skill Set <b>{obj.name}</b> has been updated"
                if form.cleaned_data["_errors"]:
                    errors = form.cleaned_data["_errors"]
                    msg += f" with issues:<br>- {'<br>- '.join(errors)}"
                    messages.warning(request, format_html(msg))
                else:
                    messages.info(request, format_html(f"{msg}."))
            return redirect("admin:memberaudit_skillset_changelist")
    else:
        form = ImportFittingForm()
    return render(
        request,
        "admin/memberaudit/skillset/import_skills.html",
        {
            "title": "Create skill set from fitting",
            "form": form,
            "cl": {"opts": SkillSet._meta},
            "site_header": site_header,
        },
    )


@login_required
@staff_member_required
def admin_create_skillset_from_skill_plan(request):
    if request.method == "POST":
        form = ImportSkillPlanForm(request.POST)
        if form.is_valid():
            skill_plan = form.cleaned_data["_skill_plan"]
            params = {"skill_plan": skill_plan, "user": request.user}
            if form.cleaned_data["skill_set_group"]:
                params["skill_set_group"] = form.cleaned_data["skill_set_group"]
            obj, created = SkillSet.objects.update_or_create_from_skill_plan(**params)
            logger.info("%s: Skill Set created from skill plan", skill_plan.name)
            tasks.update_characters_skill_checks.delay(force_update=True)
            if created:
                msg = f"Skill Set <b>{obj.name}</b> has been created"
            else:
                msg = f"Skill Set <b>{obj.name}</b> has been updated"
            if form.cleaned_data["_errors"]:
                errors = form.cleaned_data["_errors"]
                msg += f" with issues:<br>- {'<br>- '.join(errors)}"
                messages.warning(request, format_html(msg))
            else:
                messages.info(request, format_html(f"{msg}."))
            return redirect("admin:memberaudit_skillset_changelist")
    else:
        form = ImportSkillPlanForm()
    return render(
        request,
        "admin/memberaudit/skillset/import_skills.html",
        {
            "title": "Create skill set from skill plan",
            "form": form,
            "cl": {"opts": SkillSet._meta},
            "site_header": site_header,
        },
    )
