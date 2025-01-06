# Generated by Django 4.2.17 on 2025-01-06 03:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_alter_answer_answerhash_alter_question_bounty_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='answer',
            name='status',
            field=models.CharField(choices=[('UN', 'Unselected'), ('SE', 'Selected'), ('CE', 'Certified'), ('PO', 'Paid Out')], max_length=100),
        ),
    ]
