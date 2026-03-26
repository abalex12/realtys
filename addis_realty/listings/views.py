import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone

from .models import Listing, ListingMedia, ListingReport, ADDIS_AREAS
from .forms import ListingForm
from .media_optimizer import (
    process_image, process_video, is_duplicate_media, detect_media_type,
    get_storage_stats, human_size,
    MAX_IMAGES_PER_LISTING, MAX_VIDEOS_PER_LISTING,
    SUPPORTED_IMAGE_EXTS, SUPPORTED_VIDEO_EXTS,
)
from accounts.models import User, SavedListing

logger = logging.getLogger(__name__)


# ── Decorators ─────────────────────────────────────────────────────────────────

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_admin_role or request.user.is_staff):
            messages.error(request, 'Admin access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def email_verified_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.email_verified:
            messages.warning(request,
                '⚠️ Please verify your email before posting a listing. '
                '<a href="/accounts/resend-verification/">Resend verification email</a>.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ── Media ingestion helper ─────────────────────────────────────────────────────

def _ingest_media_files(listing, image_files, video_files):
    """
    Run the optimizer on uploaded files and persist ListingMedia records.
    Returns (images_saved, videos_saved, errors[]).
    """
    errors = []
    images_saved = 0
    videos_saved = 0

    # Count existing media
    existing_images = listing.media.filter(media_type='image').count()
    existing_videos = listing.media.filter(media_type='video').count()
    orig_total = 0
    opt_total  = 0

    for f in image_files:
        if existing_images + images_saved >= MAX_IMAGES_PER_LISTING:
            errors.append(f"Image limit reached ({MAX_IMAGES_PER_LISTING}). Some images were skipped.")
            break
        try:
            result = process_image(f, f.name)
            # Deduplicate per listing
            if is_duplicate_media(result['sha256'], listing=listing):
                errors.append(f"'{f.name}' is a duplicate and was skipped.")
                continue
            full_cf, full_name = result['full']
            thumb_cf, thumb_name = result['thumbnail']
            m = ListingMedia(
                listing=listing,
                media_type='image',
                order=existing_images + images_saved,
                sha256=result['sha256'],
                original_size=result['original_size'],
                optimized_size=result['optimized_size'],
                savings_pct=result['savings_pct'],
            )
            m.file.save(full_name, full_cf, save=False)
            m.thumbnail.save(thumb_name, thumb_cf, save=False)
            m.save()
            orig_total += result['original_size']
            opt_total  += result['optimized_size']
            images_saved += 1
        except Exception as e:
            logger.error(f"Image ingest error for {f.name}: {e}")
            errors.append(f"Could not process '{f.name}': {str(e)[:120]}")

    for f in video_files:
        if existing_videos + videos_saved >= MAX_VIDEOS_PER_LISTING:
            errors.append(f"Video limit reached ({MAX_VIDEOS_PER_LISTING}). Some videos were skipped.")
            break
        try:
            result = process_video(f, f.name)
            if is_duplicate_media(result['sha256'], listing=listing):
                errors.append(f"'{f.name}' is a duplicate and was skipped.")
                continue
            mp4_cf, mp4_name = result['mp4']
            m = ListingMedia(
                listing=listing,
                media_type='video',
                order=existing_videos + videos_saved,
                sha256=result['sha256'],
                original_size=result['original_size'],
                optimized_size=result['mp4_size'],
                savings_pct=result['savings_pct'],
                duration_secs=result['duration'],
            )
            m.file.save(mp4_name, mp4_cf, save=False)
            if result.get('webm'):
                webm_cf, webm_name = result['webm']
                m.webm_file.save(webm_name, webm_cf, save=False)
            if result.get('poster'):
                poster_cf, poster_name = result['poster']
                m.poster.save(poster_name, poster_cf, save=False)
            m.save()
            orig_total += result['original_size']
            opt_total  += result['mp4_size']
            videos_saved += 1
        except Exception as e:
            logger.error(f"Video ingest error for {f.name}: {e}")
            errors.append(f"Could not process '{f.name}': {str(e)[:120]}")

    # Update listing storage counters
    if orig_total or opt_total:
        listing.original_media_bytes = (listing.original_media_bytes or 0) + orig_total
        listing.total_media_bytes    = (listing.total_media_bytes or 0) + opt_total
        listing.save(update_fields=['original_media_bytes', 'total_media_bytes'])

    return images_saved, videos_saved, errors


# ── Public Views ───────────────────────────────────────────────────────────────

def home(request):
    featured      = Listing.objects.filter(status='approved', is_featured=True)[:6]
    recent_houses = Listing.objects.filter(status='approved', listing_type='house').order_by('-created_at')[:6]
    recent_cars   = Listing.objects.filter(status='approved', listing_type='car').order_by('-created_at')[:6]
    total_listings = Listing.objects.filter(status='approved').count()
    total_houses   = Listing.objects.filter(status='approved', listing_type='house').count()
    total_cars     = Listing.objects.filter(status='approved', listing_type='car').count()
    return render(request, 'listings/home.html', {
        'featured': featured, 'recent_houses': recent_houses, 'recent_cars': recent_cars,
        'areas': ADDIS_AREAS, 'total_listings': total_listings,
        'total_houses': total_houses, 'total_cars': total_cars,
    })


def listing_list(request):
    qs = Listing.objects.filter(status='approved')
    q            = request.GET.get('q', '')
    listing_type = request.GET.get('type', '')
    purpose      = request.GET.get('purpose', '')
    area         = request.GET.get('area', '')
    min_price    = request.GET.get('min_price', '')
    max_price    = request.GET.get('max_price', '')
    sort         = request.GET.get('sort', '-created_at')
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(title_am__icontains=q) |
            Q(description__icontains=q) | Q(description_am__icontains=q) |
            Q(car_make__icontains=q) | Q(car_model__icontains=q) |
            Q(address__icontains=q) | Q(area__icontains=q)
        )
    if listing_type: qs = qs.filter(listing_type=listing_type)
    if purpose:      qs = qs.filter(purpose=purpose)
    if area:         qs = qs.filter(area=area)
    if min_price:
        try: qs = qs.filter(price__gte=float(min_price))
        except ValueError: pass
    if max_price:
        try: qs = qs.filter(price__lte=float(max_price))
        except ValueError: pass
    valid_sorts = ['-created_at', 'created_at', 'price', '-price', '-views_count']
    if sort not in valid_sorts: sort = '-created_at'
    qs = qs.order_by(sort)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'listings/list.html', {
        'page_obj': page_obj, 'areas': ADDIS_AREAS,
        'q': q, 'listing_type': listing_type, 'purpose': purpose,
        'area': area, 'min_price': min_price, 'max_price': max_price,
        'sort': sort, 'total_count': qs.count(),
    })


def listing_detail(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status='approved')
    listing.views_count += 1
    listing.save(update_fields=['views_count'])
    related = Listing.objects.filter(
        status='approved', listing_type=listing.listing_type, area=listing.area
    ).exclude(pk=listing.pk)[:4]
    is_saved = (
        request.user.is_authenticated and
        SavedListing.objects.filter(user=request.user, listing=listing).exists()
    )
    return render(request, 'listings/detail.html', {
        'listing': listing, 'related': related, 'is_saved': is_saved,
    })


def report_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status='approved')
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if reason:
            ListingReport.objects.create(
                listing=listing,
                reporter=request.user if request.user.is_authenticated else None,
                reason=reason,
                details=request.POST.get('details', ''),
                reporter_email='' if request.user.is_authenticated else request.POST.get('reporter_email', ''),
            )
            messages.success(request, 'Thank you. Your report has been submitted.')
        return redirect('listing_detail', slug=slug)
    return render(request, 'listings/report.html', {
        'listing': listing, 'reason_choices': ListingReport.REASON_CHOICES,
    })


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user_listings = Listing.objects.filter(owner=request.user)
    saves = SavedListing.objects.filter(user=request.user).count()
    return render(request, 'listings/dashboard.html', {
        'listings': user_listings.order_by('-created_at'),
        'pending':  user_listings.filter(status='pending').count(),
        'approved': user_listings.filter(status='approved').count(),
        'rejected': user_listings.filter(status='rejected').count(),
        'saves_count': saves,
        'show_verify_banner': not request.user.email_verified,
    })


@login_required
@email_verified_required
def listing_create(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            images = request.FILES.getlist('images')
            videos = request.FILES.getlist('videos')
            saved_imgs, saved_vids, errors = _ingest_media_files(listing, images, videos)
            for e in errors:
                messages.warning(request, e)
            if saved_imgs or saved_vids:
                messages.success(request,
                    f'✅ Listing submitted for review! '
                    f'{saved_imgs} image(s) and {saved_vids} video(s) optimized and saved. '
                    f'Storage saved: {listing.savings_pct:.0f}%.')
            else:
                messages.success(request, '✅ Listing submitted for review!')
            return redirect('dashboard')
    else:
        form = ListingForm()
    return render(request, 'listings/listing_form.html', {'form': form, 'action': 'create'})


@login_required
def listing_edit(request, slug):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            listing = form.save()
            listing.status = 'pending'
            listing.save(update_fields=['status'])
            images = request.FILES.getlist('images')
            videos = request.FILES.getlist('videos')
            saved_imgs, saved_vids, errors = _ingest_media_files(listing, images, videos)
            for e in errors:
                messages.warning(request, e)
            messages.success(request, f'Listing updated and resubmitted for review.')
            return redirect('dashboard')
    else:
        form = ListingForm(instance=listing)
    return render(request, 'listings/listing_form.html', {'form': form, 'listing': listing, 'action': 'edit'})


@login_required
def listing_delete(request, slug):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Listing deleted.')
    return redirect('dashboard')


@login_required
def delete_media(request, pk):
    media = get_object_or_404(ListingMedia, pk=pk)
    if media.listing.owner != request.user and not (request.user.is_admin_role or request.user.is_staff):
        return HttpResponseForbidden()
    if request.method == 'POST':
        listing = media.listing
        # Delete all physical files
        for field in (media.file, media.thumbnail, media.webm_file, media.poster):
            if field and field.name:
                try: field.delete(save=False)
                except: pass
        media.delete()
        listing.recalculate_storage()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


# ── Admin Views ────────────────────────────────────────────────────────────────

@login_required
@admin_required
def admin_dashboard(request):
    pending      = Listing.objects.filter(status='pending').order_by('created_at')
    all_listings = Listing.objects.all().order_by('-created_at')
    open_reports = ListingReport.objects.filter(resolved=False).select_related('listing', 'reporter')
    storage      = get_storage_stats()
    stats = {
        'total':   Listing.objects.count(),
        'pending': pending.count(),
        'approved': Listing.objects.filter(status='approved').count(),
        'rejected': Listing.objects.filter(status='rejected').count(),
        'users':   User.objects.count(),
        'reports': open_reports.count(),
        'storage': storage['total_human'],
        'files':   storage['file_count'],
    }
    return render(request, 'listings/admin_dashboard.html', {
        'pending_listings': pending,
        'all_listings': all_listings[:30],
        'open_reports': open_reports[:20],
        'stats': stats,
    })


@login_required
@admin_required
def admin_review(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    if request.method == 'POST':
        action      = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '').strip()
        listing.admin_notes  = admin_notes
        listing.reviewed_by  = request.user
        listing.reviewed_at  = timezone.now()
        if action == 'approve':
            listing.status           = 'approved'
            listing.rejection_reason = ''
            listing.save()
            from accounts.email_utils import send_listing_approved_email
            send_listing_approved_email(listing)
            messages.success(request, f'✅ "{listing.title}" approved and live.')
            return redirect('admin_dashboard')
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, 'Please provide a rejection reason.')
                listing.save(update_fields=['admin_notes', 'reviewed_by', 'reviewed_at'])
            else:
                listing.status           = 'rejected'
                listing.rejection_reason = reason
                listing.save()
                from accounts.email_utils import send_listing_rejected_email
                send_listing_rejected_email(listing)
                messages.warning(request, f'"{listing.title}" rejected. Owner notified.')
                return redirect('admin_dashboard')
        else:
            listing.save(update_fields=['admin_notes', 'reviewed_by', 'reviewed_at'])
            messages.success(request, 'Notes saved.')
    return render(request, 'listings/admin_review.html', {
        'listing': listing,
        'reports': listing.reports.all(),
        'checklist_items': [
            ('has_title',      'Title is clear and descriptive'),
            ('has_description','Description is detailed and accurate'),
            ('has_images',     'Has at least one clear image'),
            ('has_phone',      'Valid phone number provided'),
            ('correct_area',   'Area/location is correct'),
            ('correct_price',  'Price is reasonable for this area'),
            ('no_spam',        'Not spam or duplicate listing'),
            ('safe_content',   'Content is appropriate and safe'),
        ],
    })


@login_required
@admin_required
def admin_approve(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    listing.status = 'approved'; listing.rejection_reason = ''
    listing.reviewed_by = request.user; listing.reviewed_at = timezone.now()
    listing.save()
    from accounts.email_utils import send_listing_approved_email
    send_listing_approved_email(listing)
    messages.success(request, f'✅ "{listing.title}" approved.')
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))


@login_required
@admin_required
def admin_reject(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    reason = request.POST.get('reason', '').strip() or 'Does not meet listing guidelines.'
    listing.status = 'rejected'; listing.rejection_reason = reason
    listing.reviewed_by = request.user; listing.reviewed_at = timezone.now()
    listing.save()
    from accounts.email_utils import send_listing_rejected_email
    send_listing_rejected_email(listing)
    messages.warning(request, f'"{listing.title}" rejected.')
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))


@login_required
@admin_required
def admin_delete_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    title = listing.title; listing.delete()
    messages.success(request, f'"{title}" deleted.')
    return redirect('admin_dashboard')


@login_required
@admin_required
def admin_toggle_featured(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    listing.is_featured = not listing.is_featured
    listing.save(update_fields=['is_featured'])
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))


@login_required
@admin_required
def admin_manage_users(request):
    q = request.GET.get('q', '')
    users = User.objects.all().order_by('-date_joined')
    if q:
        users = users.filter(Q(username__icontains=q)|Q(email__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q))
    page_obj = Paginator(users, 25).get_page(request.GET.get('page'))
    return render(request, 'listings/admin_users.html', {'page_obj': page_obj, 'q': q})


@login_required
@admin_required
def admin_toggle_admin(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user != request.user and not user.is_superuser:
        user.is_admin_role = not user.is_admin_role
        user.save(update_fields=['is_admin_role'])
    return redirect('admin_manage_users')


@login_required
@admin_required
def admin_resolve_report(request, report_id):
    report = get_object_or_404(ListingReport, pk=report_id)
    report.resolved = True; report.resolved_by = request.user; report.save()
    messages.success(request, 'Report resolved.')
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))


@login_required
@admin_required
def admin_all_listings(request):
    qs = Listing.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    if status_filter: qs = qs.filter(status=status_filter)
    if q: qs = qs.filter(Q(title__icontains=q)|Q(owner__username__icontains=q))
    page_obj = Paginator(qs, 20).get_page(request.GET.get('page'))
    return render(request, 'listings/admin_all_listings.html', {
        'page_obj': page_obj, 'status_filter': status_filter, 'q': q
    })


@login_required
@admin_required
def admin_storage_stats(request):
    """Admin page showing per-listing storage analytics."""
    from django.db.models import Sum
    top_savers = (
        Listing.objects.filter(original_media_bytes__gt=0)
        .order_by('-original_media_bytes')[:20]
    )
    global_stats = Listing.objects.aggregate(
        total_orig=Sum('original_media_bytes'),
        total_opt=Sum('total_media_bytes'),
    )
    disk_stats = get_storage_stats()
    return render(request, 'listings/admin_storage.html', {
        'top_savers': top_savers,
        'global_stats': global_stats,
        'disk_stats': disk_stats,
        'human_size': human_size,
    })
