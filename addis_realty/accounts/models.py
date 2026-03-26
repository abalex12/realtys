from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)
    is_admin_role = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(null=True, blank=True, editable=False, unique=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    # Saved listings (many-to-many through separate model for metadata)
    saved_listings = models.ManyToManyField(
        'listings.Listing',
        through='SavedListing',
        related_name='saved_by',
        blank=True,
    )

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def rotate_verification_token(self):
        self.email_verification_token = uuid.uuid4()
        from django.utils import timezone
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token


class SavedListing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_listing_set')
    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE, related_name='saved_listing_set')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} → {self.listing.title}"
