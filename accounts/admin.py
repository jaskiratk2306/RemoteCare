from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
    ordering = ['username']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('RemoteCare Role & Profile', {
            'fields': ('role', 'phone_number'),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('RemoteCare Role & Profile', {
            'fields': ('role', 'phone_number'),
        }),
    )
