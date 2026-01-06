from django.urls import path
from parent import views

urlpatterns = [
    path('dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/<int:student_id>/', views.view_student, name='view_student'),
    path('student/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('student/<int:student_id>/delete/', views.delete_student, name='delete_student'),

    # Manual Trip management
    path('student/<int:student_id>/log-trip/', views.log_trip, name='log_trip'),
    # Timer Trip management
    path('student/<int:student_id>/start-trip/', views.start_trip, name='start_trip'),
    path('trip/<uuid:trip_id>/active/', views.active_trip, name='active_trip'),
    path('trip/<uuid:trip_id>/stop/', views.stop_trip, name='stop_trip'),

    # viewing and Editing Trips
    path('trip/<uuid:trip_id>/', views.view_trip, name='view_trip'),
    path('trip<uuid:trip_id>/approve/', views.approve_trip, name='approve_trip'),
    path('trip/<uuid:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('trip/<uuid:trip_id>/delete/', views.delete_trip, name='delete_trip'),

]