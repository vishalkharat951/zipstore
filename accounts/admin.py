from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Address, Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ['phone', 'avatar_preview', 'date_of_birth']
    readonly_fields = ['avatar_preview']

    def avatar_preview(self, obj):
        if obj and obj.avatar:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url,
            )
        return '-'
    avatar_preview.short_description = 'Avatar'


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ['address_type', 'full_name', 'city', 'is_default']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline, AddressInline]
    list_display = [
        'email', 'username', 'is_active', 'is_staff',
        'order_count', 'date_joined',
    ]
    list_filter = ['is_active', 'is_staff', 'date_joined', 'is_superuser']
    search_fields = ['email', 'username', 'profile__phone']
    date_hierarchy = 'date_joined'

    fieldsets = [
        (None, {'fields': ['username', 'email', 'password']}),
        ('Personal Info', {'fields': ['first_name', 'last_name']}),
        ('Permissions', {
            'fields': [
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            ],
            'classes': ['collapse'],
        }),
        ('Important Dates', {
            'fields': ['last_login', 'date_joined'],
            'classes': ['collapse'],
        }),
    ]

    def order_count(self, obj):
        count = obj.orders.count()
        url = f'/admin/orders/order/?user__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    order_count.short_description = 'Orders'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'avatar_thumb', 'date_of_birth']
    search_fields = ['user__email', 'user__username', 'phone']
    list_select_related = ['user']

    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 30px; height: 30px; object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url,
            )
        return '-'
    avatar_thumb.short_description = 'Avatar'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'full_name', 'address_type', 'city',
        'state', 'is_default',
    ]
    list_filter = ['address_type', 'is_default', 'country', 'state']
    search_fields = ['user__email', 'full_name', 'city', 'phone']
    list_select_related = ['user']
