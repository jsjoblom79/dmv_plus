import uuid
from django.db import models

class TripSessionAudit(models.Model):
    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey('Student.Trip', on_delete=models.CASCADE, related_name='audits')
    action = models.CharField(max_length=50)
    performed_by = models.ForeignKey('core.AccountUser', related_name='performed_by', on_delete=models.SET_NULL, null=True)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']