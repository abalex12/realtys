from django import forms
from .models import Listing, ListingMedia, ADDIS_AREAS

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ListingForm(forms.ModelForm):
    images = MultipleFileField(required=False, help_text='Upload images (JPG, PNG, WebP)')
    videos = MultipleFileField(required=False, help_text='Upload videos (MP4, WebM) — optional')

    class Meta:
        model = Listing
        fields = [
            'title', 'title_am', 'description', 'description_am',
            'listing_type', 'purpose', 'price', 'price_period',
            'area', 'address', 'phone_number',
            'bedrooms', 'bathrooms', 'floor_area', 'floor_number', 'furnished',
            'car_make', 'car_model', 'car_year', 'car_mileage',
            'car_color', 'car_transmission', 'car_fuel',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'description_am': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('images', 'videos'):
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (existing_class + ' form-control').strip()
        for sel in ('listing_type', 'purpose', 'area', 'car_transmission', 'car_fuel'):
            if sel in self.fields:
                self.fields[sel].widget.attrs['class'] = 'form-select'
        self.fields['furnished'].widget = forms.Select(
            choices=[('', '-- Select --'), (True, 'Furnished'), (False, 'Unfurnished')],
            attrs={'class': 'form-select'}
        )
        self.fields['images'].widget.attrs.update({'class': 'form-control', 'accept': 'image/*'})
        self.fields['videos'].widget.attrs.update({'class': 'form-control', 'accept': 'video/*'})
        optional_fields = ['title_am', 'description_am', 'price_period', 'address',
                          'bedrooms', 'bathrooms', 'floor_area', 'floor_number', 'furnished',
                          'car_make', 'car_model', 'car_year', 'car_mileage',
                          'car_color', 'car_transmission', 'car_fuel']
        for f in optional_fields:
            if f in self.fields:
                self.fields[f].required = False
