# Generated by Django 4.2.17 on 2025-01-04 13:29

import django.core.validators
from django.db import migrations, models
import siweauth.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('wallet', models.CharField(max_length=42, null=True, unique=True, validators=[django.core.validators.RegexValidator(regex='^0x[a-fA-F0-9]{40}$'), siweauth.models.validate_ethereum_address], verbose_name='Wallet Address')),
                ('username', models.CharField(blank=True, max_length=150, null=True)),
                ('is_admin', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Nonce',
            fields=[
                ('value', models.CharField(max_length=24, primary_key=True, serialize=False)),
                ('expiration', models.DateTimeField()),
            ],
        ),
    ]
