from django.urls import path

from alertviewer.views import ReceiveAlertView, AlertListView, NonMaliciousListView, AlertDetailView, \
    MitigationStrategyListView, NonMaliciousUpdateResolveView, CompanyEndpointsView, AnalystCompanyEndpointsView, \
    EndpointDetailView, CustomerEndpointDashboardView, CustomerAlertDashboardView, PDFReportView

urlpatterns = [
    path('receive/', ReceiveAlertView.as_view(), name='receive_alert'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/', AlertDetailView.as_view(), name='alert-detail'),
    path('mitigation_strategies/', MitigationStrategyListView.as_view(), name='mitigation-strategy-list'),
    path('alerts/non-malicious/', NonMaliciousListView.as_view(), name='non-malicious-alert-list'),
    path('alerts/non-malicious/<int:pk>/', NonMaliciousUpdateResolveView.as_view(), name='non-malicious-alert-list'),
    path('company/endpoints/', CompanyEndpointsView.as_view(), name='company-endpoints'),
    path('customers/<str:company_name>/endpoints/', AnalystCompanyEndpointsView.as_view(),
         name='analyst-company-endpoints'),
    path('customers/<str:company_name>/endpoints/<int:pk>/', EndpointDetailView.as_view(), name='endpoint-detail'),
    path('<str:company_name>/dashboard/endpoints/', CustomerEndpointDashboardView.as_view(),
         name='customer-endpoint-dashboard'),
    path('<str:company_name>/dashboard/alerts/', CustomerAlertDashboardView.as_view(),
         name='customer-endpoint-dashboard'),
    path('<str:company_name>/pdf-report/', PDFReportView.as_view(), name='pdf_report'),

]
