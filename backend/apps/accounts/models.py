from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE = [("admin", "管理员"), ("operator", "运维"), ("viewer", "只读")]
    role = models.CharField(max_length=16, choices=ROLE, default="viewer")
