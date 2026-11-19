from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "operator", "action", "target")
    list_filter = ("action",)
    search_fields = ("target", "operator__username")
    readonly_fields = ("operator", "action", "target", "before",
                       "after", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
