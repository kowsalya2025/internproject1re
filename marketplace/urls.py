from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Home & Listing
    path('', views.home, name='home'),
    path('templates/', views.template_list, name='template_list'),
    path('template/<slug:slug>/', views.template_detail, name='template_detail'),
    path('themes/', views.themes_page, name='themes'),
    
    # Search & Category
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category_templates, name='category_templates'),
    
    # Preview
    path('preview/<slug:slug>/', views.preview_template, name='preview_template'),
    path('preview-fullscreen/<slug:slug>/', views.preview_template_fullscreen, name='preview_fullscreen'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Cart & Checkout
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:template_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:template_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('purchase-success/', views.purchase_success, name='purchase_success'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<int:template_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:template_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Profile & Purchases
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('my-purchases/', views.my_purchases, name='my_purchases'),
    path('download/<int:template_id>/', views.download_template, name='download_template'),
    
    # Reviews
    path('review/add/<int:template_id>/', views.add_review, name='add_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
]