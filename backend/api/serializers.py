from rest_framework import serializers

from .models import EmailRecord
from .services.trusted_senders import trusted_sender_rule_for_email


class EmailRecordSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="pk", read_only=True)
    from_ = serializers.SerializerMethodField()
    fromEmail = serializers.EmailField(source="from_email")
    preview = serializers.CharField(source="snippet")
    time = serializers.DateTimeField(source="received_at")
    risk = serializers.SerializerMethodField()
    riskScore = serializers.SerializerMethodField()
    aiReason = serializers.SerializerMethodField()
    analysisStatus = serializers.SerializerMethodField()
    hasAttachments = serializers.BooleanField(source="has_attachments")
    attachmentCount = serializers.IntegerField(source="attachment_count")
    trustedRule = serializers.SerializerMethodField()

    class Meta:
        model = EmailRecord
        fields = [
            "id",
            "from_",
            "fromEmail",
            "subject",
            "preview",
            "body",
            "time",
            "folder",
            "risk",
            "riskScore",
            "aiReason",
            "analysisStatus",
            "hasAttachments",
            "attachmentCount",
            "trustedRule",
            "metadata",
            "unread",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["from"] = data.pop("from_")
        return data

    def get_from_(self, instance: EmailRecord) -> str:
        return instance.from_name or instance.from_email or "Unknown sender"

    def get_risk(self, instance: EmailRecord) -> str:
        if not hasattr(instance, "analysis"):
            return "trusted"
        legacy_map = {"safe": "trusted", "phishing": "dangerous"}
        return legacy_map.get(instance.analysis.risk, instance.analysis.risk)

    def get_riskScore(self, instance: EmailRecord) -> int:
        return instance.analysis.risk_score if hasattr(instance, "analysis") else 0

    def get_aiReason(self, instance: EmailRecord) -> str:
        if not hasattr(instance, "analysis"):
            return "Analise local ainda nao disponivel."
        if instance.analysis.status == "queued":
            return "Analise avancada enfileirada."
        if instance.analysis.status == "running":
            return "Analise avancada em andamento."
        if instance.analysis.status == "failed":
            return "A analise avancada falhou. A classificacao local foi mantida."
        if instance.analysis.model == "local-heuristic" and instance.analysis.reason.startswith(
            "Basic local scan only."
        ):
            return (
                "Analise local basica. A IA ainda nao foi executada. "
                "Clique em Analisar para enviar esta pasta para revisao da IA."
            )
        return instance.analysis.reason

    def get_analysisStatus(self, instance: EmailRecord) -> str:
        if not hasattr(instance, "analysis"):
            return "pending"
        if instance.analysis.status in {"queued", "running"}:
            return "pending"
        if instance.analysis.model in {"local-heuristic", "trusted-sender-rule"}:
            return "local"
        return "analyzed"

    def get_trustedRule(self, instance: EmailRecord) -> dict[str, str] | None:
        rule = trusted_sender_rule_for_email(instance)
        if not rule:
            return None
        return {"ruleType": rule.rule_type, "value": rule.value}


class EmailRecordListSerializer(EmailRecordSerializer):
    class Meta(EmailRecordSerializer.Meta):
        fields = [
            field
            for field in EmailRecordSerializer.Meta.fields
            if field not in {"body", "metadata", "trustedRule"}
        ]
