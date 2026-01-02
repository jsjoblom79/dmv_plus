from django.urls import path
from parent import views

urlpatterns = [
    path('dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/<int:student_id>/', views.view_student, name='view_student'),
    path('student/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('student/<int:student_id>/delete/', views.delete_student, name='delete_student'),

    # Trip management
    path('student/<int:student_id>/log-trip/', views.log_trip, name='log_trip'),
    path('trip/<uuid:trip_id>/', views.view_trip, name='view_trip'),
    path('trip/<uuid:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('trip/<uuid:trip_id>/delete/', views.delete_trip, name='delete_trip'),
]