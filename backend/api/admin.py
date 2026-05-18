from django.contrib import admin

from .models import EmailAnalysis, EmailRecord, GoogleAccount, TrustedSenderRule


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "last_synced_at", "updated_at")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailRecord)
class EmailRecordAdmin(admin.ModelAdmin):
    list_display = ("subject", "from_email", "folder", "account", "received_at", "unread")
    list_filter = ("folder", "unread", "account")
    search_fields = ("subject", "from_email", "snippet", "body")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailAnalysis)
class EmailAnalysisAdmin(admin.ModelAdmin):
    list_display = ("email", "risk", "risk_score", "model", "analyzed_at")
    list_filter = ("risk", "model")
    search_fields = ("email__subject", "reason")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TrustedSenderRule)
class TrustedSenderRuleAdmin(admin.ModelAdmin):
    list_display = ("value", "rule_type", "account", "enabled", "updated_at")
    list_filter = ("rule_type", "enabled", "account")
    search_fields = ("value", "account__email")
    readonly_fields = ("created_at", "updated_at")
