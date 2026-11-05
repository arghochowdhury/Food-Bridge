from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Restaurant


class Command(BaseCommand):
    help = ("Mark restaurants as license-verified. For LOCAL TESTING only; in real use, "
            "verify each license from the admin panel after checking it on the e-Trade License portal.")

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help="Restaurant names to verify. Leave empty to verify all pending ones.")

    def handle(self, *args, **options):
        qs = Restaurant.objects.exclude(verification_status=Restaurant.VERIFIED)
        if options["names"]:
            names = [n.lower() for n in options["names"]]
            qs = [r for r in qs if r.name.lower() in names]
        count = 0
        for r in qs:
            r.verification_status = Restaurant.VERIFIED
            r.verified_at = timezone.now()
            r.verification_note = ""
            r.save()
            self.stdout.write(f"Verified: {r.name}")
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} restaurant(s) verified."))
