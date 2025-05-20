from django.core.management.base import BaseCommand
from django.utils import timezone
import logging
import time

from ....drive_service.drive_service import DriveService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Detect physical drives and partitions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-detection even if there are existing drives',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting drive detection...'))
        start_time = timezone.now()
        
        result = DriveService.detect_and_persist_drives()
        
        end_time = timezone.now()
        duration = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS(
            f"Added {result['drives_added']} drives and {result['partitions_added']} partitions in {duration.total_seconds():.2f} seconds"
        ))
