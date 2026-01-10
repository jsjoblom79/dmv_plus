from core.models.custom_user import AccountUser
from django.db import models



class ParentProfile(models.Model):
    user = models.OneToOneField(AccountUser, on_delete=models.CASCADE)
    address1 = models.CharField(max_length=100, blank=True, null=True)
    address2 = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=2, blank=True, null=True)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='profile_photos/parents/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def get_photo_url(self):
        ''' Return photo url or default image '''
        if self.photo:
            return self.photo.url
        return '/static/images/default_user.png'


