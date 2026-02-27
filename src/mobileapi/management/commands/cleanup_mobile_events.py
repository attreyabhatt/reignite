from datetime import timedelta
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from mobileapi.models import MobileCopyEvent, MobileGenerationEvent

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete mobile generation/copy events older than a retention cutoff."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Retention window in days (default: 90).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days <= 0:
            raise CommandError("--days must be greater than zero.")

        cutoff = timezone.now() - timedelta(days=days)

        generation_deleted, _ = MobileGenerationEvent.objects.filter(created_at__lt=cutoff).delete()
        copy_deleted, _ = MobileCopyEvent.objects.filter(created_at__lt=cutoff).delete()
        logger.info(
            "cleanup_mobile_events completed cutoff=%s deleted_generation=%s deleted_copy=%s",
            cutoff.isoformat(),
            generation_deleted,
            copy_deleted,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"cleanup_mobile_events completed cutoff={cutoff.isoformat()} "
                f"deleted_generation={generation_deleted} deleted_copy={copy_deleted}"
            )
        )
