from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
from django.utils import timezone
from django.db import models

class AccountUserManager(BaseUserManager):
    '''
    Custom user manager where email is the unique identifier instead of the username.
    '''

    def create_user(self, email, password=None, **extra_fields):
        '''
        Create and save a regular user with the given email and password.
        :param email:
        :param password:
        :param extra_fields:
        :return: User
        '''
        if not email:
            raise ValueError('A valid email must be set.')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        '''
        Create and save a superuser with the given email and password.
        :param email:
        :param password:
        :param extra_fields:
        :return: superuser
        '''
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class AccountUser(AbstractBaseUser, PermissionsMixin):
    '''
    Custom user model where email is used for authentication instead of username.
    '''
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    # USER_TYPE = [
    #     ('PARENT','Parent'),
    #     ('STUDENT', 'Student'),
    #     ('UNDEFINED', 'Undefined'),
    # ]
    user_type = models.CharField(max_length=50, choices=settings.USER_TYPES, default='Undefined')

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = AccountUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

