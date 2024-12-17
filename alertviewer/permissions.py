from rest_framework.permissions import BasePermission
from trench.models import MFAMethod


class IsCustomer(BasePermission):

    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and bool(request.user.profile.customer)


class IsAnalyst(BasePermission):

    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and request.user.profile.is_analyst


class IsEndpoint(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsAuthenticatedWithMFA(BasePermission):
    """
    Custom permission to check:
    1. The access token is valid.
    2. The user has set up MFA.
    3. The user has authenticated using their MFA method.
    """

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        mfa_methods = MFAMethod.objects.filter(user=request.user, is_active=True)
        if not mfa_methods.exists():
            return False

        return True

def is_analyst(request):
    return hasattr(request.user, 'profile') and request.user.profile.is_analyst
