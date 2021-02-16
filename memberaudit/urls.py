from django.urls import path
from . import views


app_name = "memberaudit"

urlpatterns = [
    path("", views.index, name="index"),
    path("launcher", views.launcher, name="launcher"),
    path(
        "character_viewer/<int:character_pk>/",
        views.character_viewer,
        name="character_viewer",
    ),
    path("add_character", views.add_character, name="add_character"),
    path(
        "remove_character/<int:character_pk>/",
        views.remove_character,
        name="remove_character",
    ),
    path(
        "share_character/<int:character_pk>/",
        views.share_character,
        name="share_character",
    ),
    path(
        "unshare_character/<int:character_pk>/",
        views.unshare_character,
        name="unshare_character",
    ),
    path(
        "character_assets_data/<int:character_pk>/",
        views.character_assets_data,
        name="character_assets_data",
    ),
    path(
        "character_asset_container/<int:character_pk>/<int:parent_asset_pk>/",
        views.character_asset_container,
        name="character_asset_container",
    ),
    path(
        "character_asset_container_data/<int:character_pk>/<int:parent_asset_pk>/",
        views.character_asset_container_data,
        name="character_asset_container_data",
    ),
    path(
        "character_contacts_data/<int:character_pk>/",
        views.character_contacts_data,
        name="character_contacts_data",
    ),
    path(
        "character_contracts_data/<int:character_pk>/",
        views.character_contracts_data,
        name="character_contracts_data",
    ),
    path(
        "character_contract_details/<int:character_pk>/<int:contract_pk>/",
        views.character_contract_details,
        name="character_contract_details",
    ),
    path(
        "character_contract_items_included_data/<int:character_pk>/<int:contract_pk>/",
        views.character_contract_items_included_data,
        name="character_contract_items_included_data",
    ),
    path(
        "character_contract_items_requested_data/<int:character_pk>/<int:contract_pk>/",
        views.character_contract_items_requested_data,
        name="character_contract_items_requested_data",
    ),
    path(
        "character_corporation_history/<int:character_pk>/",
        views.character_corporation_history,
        name="character_corporation_history",
    ),
    path(
        "character_implants_data/<int:character_pk>/",
        views.character_implants_data,
        name="character_implants_data",
    ),
    path(
        "character_loyalty_data/<int:character_pk>/",
        views.character_loyalty_data,
        name="character_loyalty_data",
    ),
    path(
        "character_jump_clones_data/<int:character_pk>/",
        views.character_jump_clones_data,
        name="character_jump_clones_data",
    ),
    path(
        "character_mail_headers_by_label_data/<int:character_pk>/<int:label_id>/",
        views.character_mail_headers_by_label_data,
        name="character_mail_headers_by_label_data",
    ),
    path(
        "character_mail_headers_by_list_data/<int:character_pk>/<int:list_id>/",
        views.character_mail_headers_by_list_data,
        name="character_mail_headers_by_list_data",
    ),
    path(
        "character_mail_data/<int:character_pk>/<int:mail_pk>/",
        views.character_mail_data,
        name="character_mail_data",
    ),
    path(
        "character_skillqueue_data/<int:character_pk>/",
        views.character_skillqueue_data,
        name="character_skillqueue_data",
    ),
    path(
        "character_skills_data/<int:character_pk>/",
        views.character_skills_data,
        name="character_skills_data",
    ),
    path(
        "character_skill_sets_data/<int:character_pk>/",
        views.character_skill_sets_data,
        name="character_skill_sets_data",
    ),
    path(
        "character_wallet_journal_data/<int:character_pk>/",
        views.character_wallet_journal_data,
        name="character_wallet_journal_data",
    ),
    path(
        "character_wallet_transactions_data/<int:character_pk>/",
        views.character_wallet_transactions_data,
        name="character_wallet_transactions_data",
    ),
    path("reports", views.reports, name="reports"),
    path(
        "compliance_report_data",
        views.compliance_report_data,
        name="compliance_report_data",
    ),
    path("character_finder", views.character_finder, name="character_finder"),
    path(
        "character_finder_data",
        views.character_finder_data,
        name="character_finder_data",
    ),
    path(
        "skill_sets_report_data",
        views.skill_sets_report_data,
        name="skill_sets_report_data",
    ),
    path(
        "character_skill_set_details/<int:character_pk>/<int:skill_set_pk>",
        views.character_skill_set_details,
        name="character_skill_set_details",
    ),
]
