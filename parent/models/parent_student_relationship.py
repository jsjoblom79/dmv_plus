from django.db import models
from parent.models.parent_profile import ParentProfile


class ParentStudentRelationship(models.Model):
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='parent')
    student = models.ForeignKey('student.StudentProfile', on_delete=models.SETNULL, related_name='student')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parent', 'student')