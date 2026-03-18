# Hand-written replacement for the auto-generated 0006 migration.
# The auto-generated version tried to RemoveField before DeleteModel,
# which caused a FieldDoesNotExist crash on SQLite during index rebuild.
# Correct approach: delete FK-holding model first, then the parent model.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_broadcastnotification_broadcastnotificationlog_and_more'),
    ]

    operations = [
        # Delete BroadcastNotificationLog first (it holds the FK to BroadcastNotification)
        migrations.DeleteModel(
            name='BroadcastNotificationLog',
        ),
        # Then delete the parent model
        migrations.DeleteModel(
            name='BroadcastNotification',
        ),
    ]
