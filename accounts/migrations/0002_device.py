# Generated migration for Device model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, help_text='Expo Push Token', max_length=255, unique=True)),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], default='android', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'accounts_device',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='device',
            index=models.Index(fields=['user', 'is_active'], name='accounts_de_user_id_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='device',
            index=models.Index(fields=['token'], name='accounts_de_token_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='device',
            index=models.Index(fields=['platform'], name='accounts_de_platfor_g7h8i9_idx'),
        ),
    ]
