from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('managed-users/<str:user_type>/new/', views.managed_user_create, name='managed_user_create'),
    path('managed-clubs/new/', views.managed_club_create, name='managed_club_create'),
    
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('pending-clubs/', views.pending_clubs, name='pending_clubs'),
    path('approve-user/<int:profile_id>/', views.approve_user, name='approve_user'),
    path('reject-user/<int:profile_id>/', views.reject_user, name='reject_user'),
    path('approve-club/<int:club_id>/', views.approve_club, name='approve_club'),
    path('reject-club/<int:club_id>/', views.reject_club, name='reject_club'),
    
    path('my-approval-status/', views.my_approval_status, name='my_approval_status'),    
]