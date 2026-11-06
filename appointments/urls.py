from django.urls import path
from .views import book_appointment_view, update_appointment_status_view

urlpatterns = [
    path('book/', book_appointment_view, name='book-appointment'),
    path('<int:appointment_id>/status/', update_appointment_status_view, name='update-appointment-status'),
]

