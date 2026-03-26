from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('listings/', views.listing_list, name='listing_list'),
    path('listings/<slug:slug>/', views.listing_detail, name='listing_detail'),
    path('listings/<slug:slug>/report/', views.report_listing, name='report_listing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/create/', views.listing_create, name='listing_create'),
    path('dashboard/edit/<slug:slug>/', views.listing_edit, name='listing_edit'),
    path('dashboard/delete/<slug:slug>/', views.listing_delete, name='listing_delete'),
    path('media/delete/<int:pk>/', views.delete_media, name='delete_media'),
    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/review/<slug:slug>/', views.admin_review, name='admin_review'),
    path('admin-panel/approve/<slug:slug>/', views.admin_approve, name='admin_approve'),
    path('admin-panel/reject/<slug:slug>/', views.admin_reject, name='admin_reject'),
    path('admin-panel/delete/<slug:slug>/', views.admin_delete_listing, name='admin_delete_listing'),
    path('admin-panel/feature/<slug:slug>/', views.admin_toggle_featured, name='admin_toggle_featured'),
    path('admin-panel/users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin-panel/users/<int:user_id>/toggle-admin/', views.admin_toggle_admin, name='admin_toggle_admin'),
    path('admin-panel/reports/<int:report_id>/resolve/', views.admin_resolve_report, name='admin_resolve_report'),
    path('admin-panel/listings/', views.admin_all_listings, name='admin_all_listings'),
]
