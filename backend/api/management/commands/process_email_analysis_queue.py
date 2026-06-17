import time

from django.core.management.base import BaseCommand

from api.models import EmailRecord
from api.services.analysis_queue import (
    mark_email_analysis_done,
    mark_email_analysis_running,
    pop_email_analysis,
)
from api.services.openai_analysis import analyze_email


class Command(BaseCommand):
    help = "Process queued email AI analyses."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Exit when the queue is empty.")

    def handle(self, *args, **options):
        run_once = options["once"]
        self.stdout.write("MailGuard analysis worker started.")

        while True:
            try:
                email_id = pop_email_analysis()
            except Exception as exc:
                self.stderr.write(f"Failed to read analysis queue: {exc}")
                time.sleep(5)
                continue

            if email_id is None:
                if run_once:
                    return
                continue

            try:
                email = EmailRecord.objects.select_related("analysis").get(pk=email_id)
                if email.hidden_at:
                    self.stdout.write(f"Skipped hidden email {email_id}.")
                    continue
                mark_email_analysis_running(email)
                email = EmailRecord.objects.select_related("analysis").get(pk=email_id)
                analysis = analyze_email(email, force=True, bulk=True)
                self.stdout.write(
                    f"Applied {analysis.model or 'advanced'} analysis to queued email {email_id}."
                )
            except EmailRecord.DoesNotExist:
                self.stdout.write(f"Skipped missing email {email_id}.")
            except Exception as exc:
                self.stderr.write(f"Failed to analyze email {email_id}: {exc}")
                time.sleep(1)
            finally:
                try:
                    mark_email_analysis_done(email_id)
                except Exception as exc:
                    self.stderr.write(f"Failed to clear queue marker for {email_id}: {exc}")
