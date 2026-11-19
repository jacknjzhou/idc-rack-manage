from django.db.models.signals import post_save, post_delete, pre_save

from .middleware import get_current_user
from .models import AuditLog

_MODELS = []


def _snapshot(instance):
    return {f.name: str(getattr(instance, f.name)) for f in instance._meta.concrete_fields
            if not f.primary_key}


def register_audit(model):
    _MODELS.append(model)


def _pre_save(sender, instance, **kwargs):
    if sender in _MODELS and instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._audit_before = _snapshot(old)
        except sender.DoesNotExist:
            instance._audit_before = {}


def _handler(sender, instance, **kwargs):
    if sender not in _MODELS:
        return
    target = f"{sender.__name__}:{getattr(instance, 'pk', '?')}"
    operator = get_current_user()
    if kwargs.get("created"):
        AuditLog.objects.create(action="create", target=target, operator=operator,
                                before={}, after=_snapshot(instance))
    elif kwargs.get("signal") is post_delete:
        AuditLog.objects.create(action="delete", target=target, operator=operator,
                                before=_snapshot(instance), after={})
    else:
        AuditLog.objects.create(action="update", target=target, operator=operator,
                                before=getattr(instance, "_audit_before", {}),
                                after=_snapshot(instance))


post_save.connect(_handler)
post_delete.connect(_handler)
pre_save.connect(_pre_save)
