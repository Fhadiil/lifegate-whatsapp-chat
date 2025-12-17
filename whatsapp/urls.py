from django.urls import path
from .views import whatsapp_webhook
from . import views

urlpatterns = [
    path('webhook/', whatsapp_webhook, name='whatsapp-webhook'),
    
    # Clinician Portal API
    path('api/clinician/queue/', views.clinician_queue, name='clinician_queue'),
    path('api/clinician/case/<int:case_id>/', views.case_detail, name='case_detail'),
    path('api/clinician/case/<int:case_id>/message/', views.send_clinician_message, name='send_message'),
    path('api/clinician/case/<int:case_id>/accept/', views.accept_case, name='accept_case'),
    path('api/clinician/case/<int:case_id>/resolve/', views.resolve_case, name='resolve_case'),
    path('api/session/<str:phone_number>/history/', views.session_history, name='session_history'),
    
    # Admin API
    path('api/admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
