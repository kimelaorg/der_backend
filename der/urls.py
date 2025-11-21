"""
URL configuration for der project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Including urls of the apps
    path('api/auth/', include('accounts.urls')),
    path('api/expenses/', include('expenses.urls')),
    path('api/setups/', include('setups.urls')),
    path('api/mega/', include('mega.urls')),
    path('api/products/', include('products.urls')),
    # path('api/reviews/', include('reviews.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/sales/', include('sales.urls')),
    # path('api/payments/', include('payments.urls')),
    # path('api/license/', include('licence.urls')),
    path('api/purchasing/', include('purchasing.urls')),
    # path('api/shipping/', include('shipping.urls')),
    # path('api/analytics/', include('analytics.urls')),

    # url for documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
