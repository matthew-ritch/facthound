# Generated by Django 5.1.4 on 2025-02-12 02:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0006_alter_question_contractaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='confirmed_onchain',
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name='question',
            name='confirmed_onchain',
            field=models.BooleanField(null=True),
        ),
    ]
