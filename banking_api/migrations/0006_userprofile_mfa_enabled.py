# Generated by Django 5.1.3 on 2024-11-23 01:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('banking_api', '0005_userprofile_otp_userprofile_otp_expiration'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='mfa_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
