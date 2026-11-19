from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"

    def ready(self):
        from . import signals  # noqa
        from apps.rooms.models import Room
        from apps.racks.models import Rack
        from apps.devices.models import Device
        from apps.placements.models import Placement
        for m in (Room, Rack, Device, Placement):
            signals.register_audit(m)
