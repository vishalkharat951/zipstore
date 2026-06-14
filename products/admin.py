from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, ProductVideo


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'sort_order']


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1
    fields = ['url', 'title', 'sort_order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('products')

    def product_count(self, obj):
        count = obj.products.count()
        url = f'/admin/products/product/?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        'thumbnail', 'name', 'sku', 'category', 'price_display',
        'stock_status', 'featured', 'active', 'created_at',
    ]
    list_display_links = ['thumbnail', 'name']
    list_filter = [
        'category', 'in_stock', 'active', 'featured', 'created_at',
    ]
    list_editable = ['featured', 'active']
    search_fields = ['name', 'description', 'sku']
    date_hierarchy = 'created_at'
    actions = [
        'mark_featured', 'unmark_featured', 'activate_selected', 'deactivate_selected',
    ]

    inlines = [ProductImageInline, ProductVideoInline]

    fieldsets = [
        ('Basic Info', {
            'fields': ['name', 'slug', 'category', 'description'],
        }),
        ('Pricing & Stock', {
            'fields': [
                ('price', 'discount_price'),
                ('sku', 'stock'),
                'in_stock',
            ],
        }),
        ('Media', {
            'fields': ['image'],
        }),
        ('Status', {
            'fields': ['active', 'featured'],
        }),
    ]

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;" />',
                obj.image.url,
            )
        return format_html(
            '<div style="width: 40px; height: 40px; background: #eee; border-radius: 6px;"></div>'
        )
    thumbnail.short_description = ''

    def price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">₹{}</span> '
                '<span style="color: #c00; font-weight: bold;">₹{}</span>',
                obj.price, obj.discount_price,
            )
        return format_html('<span style="font-weight: bold;">₹{}</span>', obj.price)
    price_display.short_description = 'Price'

    def stock_status(self, obj):
        if not obj.in_stock:
            return format_html('<span style="color: red; font-weight: bold;">Out of Stock</span>')
        if obj.stock is not None and obj.stock <= 5:
            return format_html('<span style="color: orange;">{} left</span>', obj.stock)
        if obj.stock:
            return format_html('<span style="color: green;">{} in stock</span>', obj.stock)
        return format_html('<span style="color: green; font-weight: bold;">Available</span>')
    stock_status.short_description = 'Stock'

    def featured_badge(self, obj):
        if obj.featured:
            return format_html('<span style="color: #e65100;">&#9733; Featured</span>')
        return ''
    featured_badge.short_description = 'Featured'

    def active_badge(self, obj):
        return format_html(
            '<span style="color: {};">&#9679;</span>',
            'green' if obj.active else 'red',
        )
    active_badge.short_description = ''

    def mark_featured(self, request, queryset):
        queryset.update(featured=True)
        self.message_user(request, f'{queryset.count()} product(s) marked as featured.')
    mark_featured.short_description = 'Mark selected as Featured'

    def unmark_featured(self, request, queryset):
        queryset.update(featured=False)
        self.message_user(request, f'{queryset.count()} product(s) unmarked as featured.')
    unmark_featured.short_description = 'Unmark selected as Featured'

    def activate_selected(self, request, queryset):
        queryset.update(active=True)
        self.message_user(request, f'{queryset.count()} product(s) activated.')
    activate_selected.short_description = 'Activate selected'

    def deactivate_selected(self, request, queryset):
        queryset.update(active=False)
        self.message_user(request, f'{queryset.count()} product(s) deactivated.')
    deactivate_selected.short_description = 'Deactivate selected'
