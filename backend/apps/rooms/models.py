from django.db import models

class Room(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    address = models.CharField(max_length=255, blank=True)
    owner = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.code} {self.name}"
