"""
Custom permission classes for role-based access control.
"""
from rest_framework.permissions import BasePermission
from accounts.models import User


class IsStudent(BasePermission):
    """Allow access only to users with STUDENT role."""
    
    def has_permission(self, request, view):
        return request.user and request.user.role == User.Role.STUDENT


class IsGuard(BasePermission):
    """Allow access only to users with GUARD role."""
    
    def has_permission(self, request, view):
        return request.user and request.user.role == User.Role.GUARD


class IsAdmin(BasePermission):
    """Allow access only to users with ADMIN role."""
    
    def has_permission(self, request, view):
        return request.user and request.user.role == User.Role.ADMIN


class IsStudentOwner(BasePermission):
    """Allow students to access only their own incidents."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.STUDENT:
            return obj.student == request.user
        return True


class IsGuardOrAdmin(BasePermission):
    """Allow access only to GUARD or ADMIN users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.role in [User.Role.GUARD, User.Role.ADMIN]


class IsAdminOrReadOnly(BasePermission):
    """Allow admin full access, others read-only."""
    
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.role == User.Role.ADMIN
