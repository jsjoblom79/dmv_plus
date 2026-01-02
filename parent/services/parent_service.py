from django.dispatch import receiver
from django.db.models.signals import post_save
from core.models.custom_user import AccountUser
from parent.models.parent_profile import ParentProfile
# from student.models import StudentProfile


@receiver(post_save, sender=AccountUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type in ['PARENT', 'UNDEFINED']:
            ParentProfile.objects.create(user=instance)
        # if instance.user_type == 'PARENT':
        #     ParentProfile.objects.create(user=instance)
        #
        # elif instance.user_type == 'STUDENT':
        #     StudentProfile.objects.create(user=instance)
        #
        # elif instance.user_type is None:
        #     ParentProfile.objects.create(user=instance)