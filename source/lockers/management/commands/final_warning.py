from django.core.management.base import BaseCommand, CommandError
from lockers.models import Locker
from lockers.email import send_final_warning


class Command(BaseCommand):
    help = "Command for issuing final warning to lockers that haven't been re-activated."

    def add_arguments(self, parser):
        parser.add_argument(
            "--silent", action="store_true", dest="silent", default=False, help="Silently issue command"
        )

    def handle(self, *args, **options):
        if not options.get("silent"):
            self.stdout.write(self.style.NOTICE(self.help))
            self.stdout.write(self.style.NOTICE("Are you sure you wish to proceed? y/N"))
            confirm = input("").lower()
            if confirm == "y":
                self.stdout.write(self.style.NOTICE("Issuing final warnings..."))
            else:
                raise CommandError("Aborted.")
        else:
            self.stdout.write(self.style.NOTICE("Silent treatment received."))

        endangered = issue_final_warnings()
        self.stdout.write(self.style.SUCCESS("{} warnings issued".format(endangered)))


def issue_final_warnings():
    endangered = (
        Locker.objects.filter(owner__isnull=False)
        .filter(owner__is_active__exact=False)
        .prefetch_related("owner__user")
    )

    for locker in endangered:
        token = locker.owner.token
        send_final_warning(locker.owner.user, token)

    return len(endangered)
