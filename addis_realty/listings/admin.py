from django.contrib import admin
from .models import Listing, ListingMedia

class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'listing_type', 'purpose', 'area', 'status', 'owner', 'created_at']
    list_filter = ['status', 'listing_type', 'purpose', 'area']
    search_fields = ['title', 'description']
    inlines = [ListingMediaInline]
    readonly_fields = ['views_count', 'created_at', 'updated_at']

@admin.register(ListingMedia)
class ListingMediaAdmin(admin.ModelAdmin):
    list_display = ['listing', 'media_type', 'order']
