# Generated by Django 4.2.17 on 2025-01-04 13:29

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import siweauth.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('dt', models.DateTimeField()),
                ('poster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=1000)),
                ('dt', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('thread', models.ManyToManyField(to='questions.thread')),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('questionHash', models.BinaryField()),
                ('questionAddress', models.CharField(max_length=42, unique=True, validators=[django.core.validators.RegexValidator(regex='^0x[a-fA-F0-9]{40}$'), siweauth.models.validate_ethereum_address], verbose_name='FactHound Question Address')),
                ('bounty', models.IntegerField()),
                ('status', models.CharField(choices=[('OP', 'Open'), ('AS', 'Answer Selected'), ('RS', 'Resolved'), ('CA', 'Canceled')], max_length=100)),
                ('asker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='questions.post')),
            ],
        ),
        migrations.AddField(
            model_name='post',
            name='thread',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='questions.thread'),
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answerHash', models.BinaryField(unique=True)),
                ('status', models.CharField(choices=[('OP', 'Open'), ('SE', 'Selected'), ('CE', 'Certified'), ('PO', 'Paid Out')], max_length=100)),
                ('answerer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='questions.post')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='questions.question')),
            ],
        ),
    ]
