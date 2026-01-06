from django.contrib import admin
from .models import (
    Category, Tag, Template, Purchase, Review,
    CartItem, Wishlist, UserProfile, UserTemplate, TemplateAnalytics
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_free', 'is_featured', 'views', 'downloads', 'created_at']
    list_filter = ['is_published', 'is_featured', 'is_free', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['tags']

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'amount', 'paid', 'purchased_at']
    list_filter = ['paid', 'purchased_at']
    search_fields = ['user__username', 'template__name', 'order_id']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'template__name', 'comment']

admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(UserProfile)
admin.site.register(UserTemplate)
admin.site.register(TemplateAnalytics)
