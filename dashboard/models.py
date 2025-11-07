from django.conf import settings
from django.db import models
from django.utils import timezone


class SearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='esg_searches')
    company_name = models.CharField(max_length=255)
    searched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['user', '-searched_at']),
            models.Index(fields=['company_name']),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug representation
        return f'{self.user.username}: {self.company_name} at {self.searched_at.isoformat()}'
