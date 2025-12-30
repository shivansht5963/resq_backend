# Generated migration for GuardAlert improvements
# Adds alert_type, requires_response, and response_deadline fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0005_alter_guardalert_options_and_more'),
    ]

    operations = [
        # Add AlertType choices to GuardAlert
        migrations.AddField(
            model_name='guardalert',
            name='alert_type',
            field=models.CharField(
                choices=[('ASSIGNMENT', 'Assignment Required'), ('BROADCAST', 'Broadcast Only')],
                db_index=True,
                default='ASSIGNMENT',
                help_text='ASSIGNMENT: requires response, BROADCAST: awareness only',
                max_length=20,
            ),
        ),
        
        # Add requires_response field
        migrations.AddField(
            model_name='guardalert',
            name='requires_response',
            field=models.BooleanField(
                default=True,
                help_text='True = guard must accept/reject, False = read-only notification',
            ),
        ),
        
        # Add response_deadline field
        migrations.AddField(
            model_name='guardalert',
            name='response_deadline',
            field=models.DateTimeField(
                blank=True,
                help_text='Deadline for guard response (auto-escalate after this)',
                null=True,
            ),
        ),
        
        # Update AlertStatus choices
        migrations.AlterField(
            model_name='guardalert',
            name='status',
            field=models.CharField(
                choices=[
                    ('SENT', 'Sent'),
                    ('ACCEPTED', 'Accepted (Official Response)'),
                    ('DECLINED', 'Declined'),
                    ('EXPIRED', 'Expired (No Response / Timeout)'),
                ],
                db_index=True,
                default='SENT',
                max_length=20,
            ),
        ),
        
        # Add index for alert_type and status
        migrations.AddIndex(
            model_name='guardalert',
            index=models.Index(fields=['incident', 'alert_type', 'status'], name='security_guardalert_incident_alert_type_status_idx'),
        ),
        
        # Add index for requires_response and status
        migrations.AddIndex(
            model_name='guardalert',
            index=models.Index(fields=['requires_response', 'status'], name='security_guardalert_requires_response_status_idx'),
        ),
    ]
