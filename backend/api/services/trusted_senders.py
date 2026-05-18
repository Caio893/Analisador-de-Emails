from api.models import EmailRecord, TrustedSenderRule


def normalize_rule_value(value: str) -> str:
    value = (value or "").strip().lower()
    if value.startswith("@"):
        value = value[1:]
    return value


def sender_domain(email: EmailRecord) -> str:
    metadata = email.metadata or {}
    domain = normalize_rule_value(str(metadata.get("sender_domain") or ""))
    if domain:
        return domain
    if "@" in email.from_email:
        return normalize_rule_value(email.from_email.rsplit("@", 1)[-1])
    return ""


def sender_email(email: EmailRecord) -> str:
    return normalize_rule_value(email.from_email)


def has_high_risk_trusted_sender_bypass(email: EmailRecord) -> bool:
    metadata = email.metadata or {}
    return email.folder == EmailRecord.Folder.SPAM or bool(metadata.get("dangerous_attachment_extensions"))


def domain_matches(rule_value: str, domain: str) -> bool:
    return domain == rule_value or domain.endswith(f".{rule_value}")


def trusted_sender_rule_for_email(email: EmailRecord) -> TrustedSenderRule | None:
    if has_high_risk_trusted_sender_bypass(email):
        return None

    email_value = sender_email(email)
    domain_value = sender_domain(email)
    rules = TrustedSenderRule.objects.filter(account=email.account, enabled=True)

    if email_value:
        exact_rule = rules.filter(rule_type=TrustedSenderRule.RuleType.EMAIL, value=email_value).first()
        if exact_rule:
            return exact_rule

    if domain_value:
        for rule in rules.filter(rule_type=TrustedSenderRule.RuleType.DOMAIN):
            if domain_matches(rule.value, domain_value):
                return rule

    return None


def create_trusted_sender_rule(email: EmailRecord, rule_type: str) -> tuple[TrustedSenderRule, bool]:
    if rule_type == TrustedSenderRule.RuleType.EMAIL:
        value = sender_email(email)
    elif rule_type == TrustedSenderRule.RuleType.DOMAIN:
        value = sender_domain(email)
    else:
        raise ValueError("rule_type must be email or domain.")

    if not value:
        raise ValueError("Could not determine sender value for trusted rule.")

    return TrustedSenderRule.objects.update_or_create(
        account=email.account,
        rule_type=rule_type,
        value=value,
        defaults={"enabled": True},
    )
