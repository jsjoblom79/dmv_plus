from core.models.custom_user import AccountUser

class AccountService:
    def is_parent(self, user):
        return AccountUser.objects.filter(
            email=user.email,
            user_type='Parent'
        ).exists()

    def is_student(self, user):
        return AccountUser.objects.filter(
            email=user.email,
            user_type='Student'
        ).exists()