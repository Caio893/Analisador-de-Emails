import time

from django.core.management.base import BaseCommand

from api.models import EmailRecord
from api.services.analysis_queue import mark_email_analysis_done, pop_email_analysis
from api.services.openai_analysis import analyze_email_locally


class Command(BaseCommand):
    help = "Process queued email AI analyses."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Exit when the queue is empty.")

    def handle(self, *args, **options):
        run_once = options["once"]
        self.stdout.write("MailGuard analysis worker started.")

        while True:
            email_id = pop_email_analysis()
            if email_id is None:
                if run_once:
                    return
                continue

            try:
                email = EmailRecord.objects.select_related("analysis").get(pk=email_id)
                analyze_email_locally(email)
                self.stdout.write(f"Applied local analysis to queued email {email_id}.")
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
