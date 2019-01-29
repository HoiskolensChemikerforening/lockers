from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Sets up authentication backend needed for Dataporten"

    def add_arguments(self, parser):
        parser.add_argument("client_id", type=str)
        parser.add_argument("secret_key", type=str)

    def handle(self, *args, **options):
        if not (len(options["client_id"]) and len(options["secret_key"])):
            self.stdout.write(self.style.ERROR("Both options must be provided!"))

        # Load current Site object
        site = Site.objects.get(pk=settings.SITE_ID)

        dataporten_app, _ = SocialApp.objects.get_or_create(name="dataporten-dev", provider="dataporten")
        dataporten_app.client_id = options["client_id"]
        dataporten_app.secret = options["secret_key"]
        dataporten_app.sites.set([site])

        self.stdout.write(self.style.SUCCESS("Successfully set Dataporten settings"))
