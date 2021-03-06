from django.urls import path
from . import views
from .webhooks import webhook

urlpatterns = [
    path('', views.checkout, name='checkout'),
    # path('', views.checktest, name='checkout'),
    path('checkout_success/<order_number>', views.checkout_success, name='checkout_success'),
    path('cache_checkout_data/', views.cache_checkout_data, name=''),
    path('wh/', webhook, name='webhook'),
    # path('get_giftcard_status/<giftcard_code>', views.get_giftcard_status, name='get_giftcard_status'),
    path('get_giftcard_status/', views.get_giftcard_status, name='get_giftcard_status'),

]