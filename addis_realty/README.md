# Addis Realty — Full-Stack Django Platform

A professional property & vehicle listing platform for Addis Ababa, Ethiopia.

## 🚀 Quick Start

```bash
pip install django pillow
cd addis_realty
python manage.py migrate
python manage.py runserver
```
Visit **http://127.0.0.1:8000**

## 🔐 Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| User 1 | `user1` | `pass123` |
| User 2 | `user2` | `pass123` |

## ✅ Full Feature List

### Email Verification
- Token-based UUID verification link sent on registration
- 24-hour link expiry
- "Resend verification" from dashboard and navbar banner
- Unverified users can browse but cannot post listings
- Verification badge shown in navbar dropdown and dashboard

### Password Management
- Password reset via email link (token + uidb64, 24h expiry)
- Password change for authenticated users
- In development: emails print to terminal/console
- For production: configure SMTP in settings.py

### Public Browsing
- Advanced search (English + Amharic)
- Filter by type, purpose, area, price range
- Sort by date, price, views
- Full detail page with media gallery (swipe/keyboard/thumbnail)
- Save button (heart icon) — requires login
- Share listing via link or WhatsApp
- Report listing (flag for review)

### User Dashboard
- Stats: total, live, in-review, rejected, saved count
- Email verification banner with resend button
- Lock icon on "Post New Listing" if email unverified
- Table of all own listings with status, rejection reason, edit/delete
- Quick links to profile, saved listings, security settings

### Saved Listings
- Toggle save/unsave from listing detail page (AJAX, no page reload)
- Toast notification on save/unsave
- Dedicated "Saved Listings" page with timestamps
- Accessible from navbar dropdown and dashboard

### Listing Reports
- Public "Report Listing" button on every listing detail page
- 6 reason categories (spam, scam, wrong info, duplicate, inappropriate, other)
- Free-text details field
- Reporter email field for non-authenticated users
- Reports tracked in database, resolved by admin

### Admin Panel (`/admin-panel/`)
- Pending review queue (oldest first, pulsing badge)
- Quick approve / quick reject (with reason dropdown)
- "Full Review" page per listing:
  - Complete listing preview with media gallery
  - Owner details (email verification status)
  - Interactive checklist (8 quality checkpoints)
  - Private admin notes field (owner never sees)
  - Approve & Publish or Reject with reason (pre-filled options + custom)
  - Lists all reports against this listing with resolve button
  - Previous rejection reason displayed
- Email notifications to owner on approve/reject
- Reports management section on dashboard
- All Listings view with search + status filter + pagination
- User Management with search, pagination, email-verified indicator
- Grant/revoke admin role per user
- Toggle featured status on any listing

### Email Notifications (console in dev, SMTP-ready for prod)
- Registration: verification link
- Approval: listing is live, direct link
- Rejection: reason + edit link
- Password reset: secure link

## ⚙️ Production Email Setup

In `settings.py`, change:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
SITE_URL = 'https://yourdomain.com'
```
