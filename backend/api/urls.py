from django.urls import path

from .views import (
    EmailAnalyzeView,
    EmailDetailView,
    EmailListView,
    EmailRemoveView,
    EmailSyncView,
    GoogleAuthCallbackView,
    GoogleAuthStartView,
    GoogleAccountRevokeView,
    GoogleAccountView,
    HealthView,
    SummaryView,
    TrustedSenderRuleView,
)

urlpatterns = [
    path("healthz/", HealthView.as_view(), name="healthz"),
    path("auth/google/start/", GoogleAuthStartView.as_view(), name="google-auth-start"),
    path("auth/google/callback/", GoogleAuthCallbackView.as_view(), name="google-auth-callback"),
    path("account/", GoogleAccountView.as_view(), name="google-account"),
    path("account/revoke/", GoogleAccountRevokeView.as_view(), name="google-account-revoke"),
    path("emails/sync/", EmailSyncView.as_view(), name="email-sync"),
    path("emails/analyze/", EmailAnalyzeView.as_view(), name="email-analyze"),
    path("emails/", EmailListView.as_view(), name="email-list"),
    path("emails/<int:pk>/", EmailDetailView.as_view(), name="email-detail"),
    path("emails/<int:pk>/remove/", EmailRemoveView.as_view(), name="email-remove"),
    path("trusted-senders/", TrustedSenderRuleView.as_view(), name="trusted-senders"),
    path("summary/", SummaryView.as_view(), name="summary"),
]
