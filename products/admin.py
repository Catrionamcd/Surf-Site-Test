from django.contrib import admin
from .models import Product, Category, SubCategory, ProductInventory, Brand, Colour

# Register your models here.

class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku',
        'name',
        'category',
        'price',
        'rating',
        'image'
    )

    ordering = ('sku',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'friendly_name',
        'name'
    )

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'category',
        'friendly_name',
        'name'
    )

admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(ProductInventory)
admin.site.register(Brand)
admin.site.register(Colour)
