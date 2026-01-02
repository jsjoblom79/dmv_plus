from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models.custom_user import AccountUser


class AccountUserAdmin(BaseUserAdmin):
    '''
    Custom admin interface for the AccountUser model.
    '''
    model = AccountUser

    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'user_type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active')}
        ),
    )

    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    filter_horizontal = ('groups', 'user_permissions',)

admin.site.register(AccountUser, AccountUserAdmin)

