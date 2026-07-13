"""Declared handler contracts for UI-v2 enabled actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandlerContract:
    action_label: str
    page: str
    handler_purpose: str
    canonical_operation: str
    requires_confirmation: bool = False
    placeholder: bool = False
    test_id: str = ""


HANDLER_CONTRACTS: tuple[HandlerContract, ...] = (
    HandlerContract("Neues Profil", "Profile", "open_create_mode", "profile.create", test_id="profile_create_open"),
    HandlerContract("Speichern", "Profile", "persist_profile_draft", "profile.save", test_id="profile_save"),
    HandlerContract("Abbrechen", "Profile", "discard_profile_draft", "profile.cancel", test_id="profile_cancel"),
    HandlerContract("Bearbeiten", "Profile", "open_edit_mode", "profile.edit", test_id="profile_edit_open"),
    HandlerContract("Profil duplizieren", "Profile", "duplicate_profile", "profile.duplicate", test_id="profile_duplicate"),
    HandlerContract("Aktivieren", "Profile", "activate_profile", "profile.activate", test_id="profile_activate"),
    HandlerContract("Profil löschen", "Profile", "delete_profile_confirmed", "profile.delete", requires_confirmation=True, test_id="profile_delete"),
    HandlerContract("Neue Konfiguration", "Konfigurationen", "open_create_mode", "configuration.create", test_id="config_create_open"),
    HandlerContract("Speichern", "Konfigurationen", "persist_configuration_draft", "configuration.save", test_id="config_save"),
    HandlerContract("Abbrechen", "Konfigurationen", "discard_configuration_draft", "configuration.cancel", test_id="config_cancel"),
    HandlerContract("Bearbeiten", "Konfigurationen", "open_edit_mode", "configuration.edit", test_id="config_edit_open"),
    HandlerContract("Aktivieren", "Konfigurationen", "set_configuration_active_true", "configuration.activate", test_id="config_activate"),
    HandlerContract("Deaktivieren", "Konfigurationen", "set_configuration_active_false", "configuration.deactivate", test_id="config_deactivate"),
    HandlerContract("Zielordner auswählen", "Konfigurationen", "pick_folder_to_draft", "configuration.folder_picker_draft", test_id="config_folder_picker"),
    HandlerContract("Nach oben", "Konfigurationen", "reorder_configuration_up", "configuration.reorder", test_id="config_reorder_up"),
    HandlerContract("Nach unten", "Konfigurationen", "reorder_configuration_down", "configuration.reorder", test_id="config_reorder_down"),
    HandlerContract("Löschen", "Konfigurationen", "delete_configuration_confirmed", "configuration.delete", requires_confirmation=True, test_id="config_delete"),
)

PLACEHOLDER_PATTERNS = (
    "placeholder",
    "not implemented",
    "coming soon",
    "todo",
    "generic toast",
)

WRITER_CALLS = {
    "profile.save": ("create_profile", "save_profile_changes"),
    "profile.duplicate": ("duplicate_profile",),
    "profile.activate": ("activate_profile",),
    "profile.delete": ("delete_profile",),
    "configuration.save": ("update_configuration", "update_unmatched_configuration", "create_configuration"),
    "configuration.activate": ("set_configuration_active",),
    "configuration.deactivate": ("set_configuration_active",),
    "configuration.reorder": ("reorder_configurations",),
    "configuration.delete": ("delete_configuration",),
}

CONTRACT_TEST_IDS = {contract.test_id for contract in HANDLER_CONTRACTS if contract.test_id}
