import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


class ParentInvitation(models.Model):
    """
    Model for tracking parent invitations to share student access
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    invitation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Who sent the invitation
    inviter = models.ForeignKey(
        'parent.ParentProfile',
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )

    # Which student is being shared
    student = models.ForeignKey(
        'student.StudentProfile',
        on_delete=models.CASCADE,
        related_name='parent_invitations'
    )

    # Invitation details
    invited_email = models.EmailField()
    invited_first_name = models.CharField(max_length=255, blank=True)
    invited_last_name = models.CharField(max_length=255, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Who accepted (if accepted)
    accepted_by = models.ForeignKey(
        'parent.ParentProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Optional personal message
    message = models.TextField(blank=True, help_text="Personal message to include in invitation")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['invited_email', 'status']),
        ]

    def __str__(self):
        return f"Invitation to {self.invited_email} for {self.student.first_name} {self.student.last_name}"

    def save(self, *args, **kwargs):
        # Set expiration date if not set (7 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if invitation has expired"""
        if self.status != 'PENDING':
            return False
        return timezone.now() > self.expires_at

    def mark_expired(self):
        """Mark invitation as expired"""
        if self.status == 'PENDING' and self.is_expired():
            self.status = 'EXPIRED'
            self.save()
            return True
        return False

    def accept(self, parent_profile):
        """Accept the invitation"""
        if self.status != 'PENDING':
            raise ValueError("Invitation is not pending")

        if self.is_expired():
            self.mark_expired()
            raise ValueError("Invitation has expired")

        self.status = 'ACCEPTED'
        self.accepted_by = parent_profile
        self.accepted_at = timezone.now()
        self.save()

    def cancel(self):
        """Cancel the invitation"""
        if self.status == 'PENDING':
            self.status = 'CANCELLED'
            self.save()
            return True
        return False