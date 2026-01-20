from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('followups/export/', views.followups_export_csv, name='followups_export_csv'),
    path('followups/new/', views.followup_create, name='followup_create'),
    path('followups/<int:pk>/edit/', views.followup_edit, name='followup_edit'),
    path('followups/<int:pk>/done/', views.followup_mark_done, name='followup_mark_done'),
]
