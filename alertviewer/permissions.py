from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):

    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and bool(request.user.profile.customer)


class IsAnalyst(BasePermission):

    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and request.user.profile.is_analyst


class IsEndpoint(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated


def is_analyst(request):
    return hasattr(request.user, 'profile') and request.user.profile.is_analyst
