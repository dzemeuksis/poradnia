# Generated by Django 2.2.25 on 2021-12-30 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0012_auto_20180601_1104"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="deadline",
            field=models.BooleanField(
                default=True,
                help_text="A significant event, especially highlighted, for example, in the list of cases.",
                verbose_name="Dead-line",
            ),
        ),
    ]
