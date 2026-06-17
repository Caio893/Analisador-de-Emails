from django.db import models
from django.utils import timezone

from .fields import EncryptedTextField


class GoogleAccount(models.Model):
    email = models.EmailField(unique=True)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True)
    token_uri = models.URLField(default="https://oauth2.googleapis.com/token")
    scopes = models.JSONField(default=list, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    gmail_history_id = models.CharField(max_length=255, blank=True)
    gmail_watch_expiration = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email


class EmailRecord(models.Model):
    class Folder(models.TextChoices):
        INBOX = "inbox", "Inbox"
        SPAM = "spam", "Spam"

    account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE, related_name="emails")
    gmail_id = models.CharField(max_length=255)
    thread_id = models.CharField(max_length=255, blank=True)
    folder = models.CharField(max_length=16, choices=Folder.choices)
    from_name = models.CharField(max_length=255, blank=True)
    from_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=500, blank=True)
    snippet = models.TextField(blank=True)
    body = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    gmail_history_id = models.CharField(max_length=255, blank=True)
    has_attachments = models.BooleanField(default=False)
    attachment_count = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    unread = models.BooleanField(default=False)
    raw_headers = models.JSONField(default=dict, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "gmail_id"],
                name="unique_email_per_google_account",
            )
        ]
        indexes = [
            models.Index(fields=["account", "folder", "-received_at"]),
            models.Index(fields=["account", "hidden_at"], name="api_emailre_account_358774_idx"),
            models.Index(fields=["gmail_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.account.email}: {self.subject or self.gmail_id}"


class TrustedSenderRule(models.Model):
    class RuleType(models.TextChoices):
        EMAIL = "email", "Email"
        DOMAIN = "domain", "Domain"

    account = models.ForeignKey(GoogleAccount, on_delete=models.CASCADE, related_name="trusted_sender_rules")
    rule_type = models.CharField(max_length=16, choices=RuleType.choices)
    value = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rule_type", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "rule_type", "value"],
                name="unique_trusted_sender_rule_per_account",
            )
        ]
        indexes = [
            models.Index(
                fields=["account", "rule_type", "value", "enabled"],
                name="api_trusted_account_bba5f7_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.value = self.value.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.account.email}: {self.rule_type}={self.value}"


class EmailAnalysis(models.Model):
    class Risk(models.TextChoices):
        TRUSTED = "trusted", "Trusted"
        SLIGHTLY_TRUSTED = "slightly_trusted", "Slightly trusted"
        SUSPICIOUS = "suspicious", "Suspicious"
        DANGEROUS = "dangerous", "Dangerous"

    class Status(models.TextChoices):
        LOCAL = "local", "Local heuristic"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    email = models.OneToOneField(EmailRecord, on_delete=models.CASCADE, related_name="analysis")
    risk = models.CharField(max_length=16, choices=Risk.choices)
    risk_score = models.PositiveSmallIntegerField(default=0)
    reason = models.TextField(blank=True)
    signals = models.JSONField(default=list, blank=True)
    model = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETED)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    prompt_version = models.CharField(max_length=64, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-analyzed_at"]
        indexes = [
            models.Index(fields=["risk"]),
            models.Index(fields=["-analyzed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email.gmail_id}: {self.risk} ({self.risk_score})"
