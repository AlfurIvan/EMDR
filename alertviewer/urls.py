from django.urls import path

from alertviewer.views import ReceiveAlertView, AlertListView, NonMaliciousListView, AlertDetailView, \
    MitigationStrategyListView, NonMaliciousUpdateResolveView, CompanyEndpointsView, AnalystCompanyEndpointsView, \
    EndpointDetailView, CustomerEndpointDashboardView, CustomerAlertDashboardView, PDFReportView, CustomerAlertListView

receive_urlpatterns = [
    path('', ReceiveAlertView.as_view(), name='receive_alert')
]
metrix_urlpatterns = [
    path('<str:company_name>/endpoints/', CustomerEndpointDashboardView.as_view(),
         name='customer-endpoint-dashboard'),
    path('<str:company_name>/alerts/', CustomerAlertDashboardView.as_view(),
         name='customer-endpoint-dashboard'),
]
alerts_urlpatterns = [
    path('all/', AlertListView.as_view(), name='alert-list'),
    path('', CustomerAlertListView.as_view(), name='customer-alert-list'),
    path('all/<int:pk>/', AlertDetailView.as_view(), name='alert-detail'),
    path('mitigation_strategies/', MitigationStrategyListView.as_view(),
         name='mitigation-strategy-list'),
    path('non-malicious/', NonMaliciousListView.as_view(), name='non-malicious-alert-list'),
    path('non-malicious/<int:pk>/', NonMaliciousUpdateResolveView.as_view(),
         name='non-malicious-alert-list'),
]
endpoints_urlpatterns = [
    path('', CompanyEndpointsView.as_view(), name='company-endpoints'),
    path('<str:company_name>/', AnalystCompanyEndpointsView.as_view(),
         name='analyst-company-endpoints'),
    path('<str:company_name>/<int:pk>/', EndpointDetailView.as_view(),
         name='endpoint-detail'),
]
reporting_urlpatterns = [
    path("", PDFReportView.as_view(), name='pdf_report')
]
