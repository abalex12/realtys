from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid

ADDIS_AREAS = [
    ('bole', 'Bole / ቦሌ'),
    ('kirkos', 'Kirkos / ቂርቆስ'),
    ('kolfe', 'Kolfe Keranio / ቆልፌ ቀራኒዮ'),
    ('gulele', 'Gulele / ጉለሌ'),
    ('lideta', 'Lideta / ልደታ'),
    ('nifas_silk', 'Nifas Silk-Lafto / ንፋስ ስልክ-ላፍቶ'),
    ('akaky', 'Akaky Kaliti / አቃቂ ቃሊቲ'),
    ('yeka', 'Yeka / የካ'),
    ('addis_ketema', 'Addis Ketema / አዲስ ከተማ'),
    ('arada', 'Arada / አራዳ'),
    ('lemlem', 'Lemi-Kura / ለሚ-ኩራ'),
    ('cherkos', 'Cherkos / ጨርቆስ'),
]


class Listing(models.Model):
    TYPE_HOUSE = 'house'
    TYPE_CAR = 'car'
    TYPE_CHOICES = [(TYPE_HOUSE, 'House'), (TYPE_CAR, 'Car')]

    PURPOSE_RENT = 'rent'
    PURPOSE_SALE = 'sale'
    PURPOSE_CHOICES = [(PURPOSE_RENT, 'For Rent'), (PURPOSE_SALE, 'For Sale')]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    title_am = models.CharField(max_length=200, blank=True, verbose_name='Title (Amharic)')
    description = models.TextField()
    description_am = models.TextField(blank=True, verbose_name='Description (Amharic)')
    listing_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    price_period = models.CharField(max_length=20, default='month', blank=True)
    area = models.CharField(max_length=50, choices=ADDIS_AREAS)
    city = models.CharField(max_length=50, default='Addis Ababa', editable=False)
    address = models.CharField(max_length=300, blank=True)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)

    # Admin review fields
    admin_notes = models.TextField(blank=True, verbose_name='Admin Notes (private)')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_listings'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    slug = models.SlugField(max_length=250, unique=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # House-specific
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    floor_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    floor_number = models.PositiveIntegerField(null=True, blank=True)
    furnished = models.BooleanField(null=True, blank=True)

    # Car-specific
    car_make = models.CharField(max_length=50, blank=True)
    car_model = models.CharField(max_length=50, blank=True)
    car_year = models.PositiveIntegerField(null=True, blank=True)
    car_mileage = models.PositiveIntegerField(null=True, blank=True)
    car_color = models.CharField(max_length=30, blank=True)
    car_transmission = models.CharField(max_length=20, blank=True,
        choices=[('automatic', 'Automatic'), ('manual', 'Manual')])
    car_fuel = models.CharField(max_length=20, blank=True,
        choices=[('petrol', 'Petrol'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')])

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or f"listing-{uuid.uuid4().hex[:8]}"
            slug = base_slug
            n = 1
            while Listing.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_main_image(self):
        return self.media.filter(media_type='image').first()

    def get_images(self):
        return self.media.filter(media_type='image')

    def get_videos(self):
        return self.media.filter(media_type='video')

    @property
    def area_display(self):
        for val, label in ADDIS_AREAS:
            if val == self.area:
                return label
        return self.area

    def get_report_count(self):
        return self.reports.filter(resolved=False).count()


class ListingMedia(models.Model):
    IMAGE = 'image'
    VIDEO = 'video'
    MEDIA_TYPES = [(IMAGE, 'Image'), (VIDEO, 'Video')]

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='listings/%Y/%m/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default=IMAGE)
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.listing.title} - {self.media_type} {self.id}"

    def is_image(self):
        return self.media_type == self.IMAGE

    def is_video(self):
        return self.media_type == self.VIDEO


class ListingReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam or misleading'),
        ('scam', 'Possible scam or fraud'),
        ('wrong_info', 'Wrong information'),
        ('duplicate', 'Duplicate listing'),
        ('inappropriate', 'Inappropriate content'),
        ('other', 'Other'),
    ]
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='submitted_reports'
    )
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    reporter_email = models.EmailField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='resolved_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report: {self.listing.title} - {self.reason}"
