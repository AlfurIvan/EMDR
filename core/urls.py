"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from alertviewer.urls import (
    receive_urlpatterns,
    metrix_urlpatterns,
    alerts_urlpatterns,
    endpoints_urlpatterns,
    reporting_urlpatterns
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('trench.urls')),
    path('auth/', include('trench.urls.jwt')),
    path('doc/', SpectacularAPIView.as_view(), name='schema'),
    path('doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('doc/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('receive/', include(receive_urlpatterns), name='receive'),
    path('dashboard/', include(metrix_urlpatterns), name='dashboard'),
    path('alerts/', include(alerts_urlpatterns), name='alerts'),
    path('endpoints/', include(endpoints_urlpatterns), name='endpoints'),
    path('pdf-report/', include(reporting_urlpatterns), name='reporting'),
]

