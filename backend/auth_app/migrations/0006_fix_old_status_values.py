from django.db import migrations


def fix_old_status_values(apps, schema_editor):
    Task = apps.get_model("auth_app", "Task")
    
    # Map old statuses to new ones
    status_map = {
        "todo": "to-do",
        "doing": "in-progress",
    }
    
    for old_status, new_status in status_map.items():
        Task.objects.filter(status=old_status).update(status=new_status)


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0005_task_assignee_task_due_date_task_reviewer_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_old_status_values),
    ]