from __future__ import unicode_literals

from django.db import migrations


def create_site_model_objects(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')

    prod, _ = Site.objects.get_or_create(pk=1)
    dev, _ = Site.objects.get_or_create(pk=2)

    dev.name = 'development'

    prod.domain = 'skap.hc.ntnu.no'
    dev.domain = '127.0.0.1'

    prod.save()
    dev.save()


def delete_site_model_objects(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.filter(pk__in=(1, 2,)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sites', '0001_initial',),
    ]

    operations = [
        migrations.RunPython(
            create_site_model_objects,
            delete_site_model_objects,
        ),
    ]