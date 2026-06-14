import os
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from products.models import Category, Product, ProductImage


class Command(BaseCommand):
    help = 'Populate products from existing media files'

    def handle(self, *args, **options):
        media_products = os.path.join(settings.MEDIA_ROOT, 'products')
        media_categories = os.path.join(settings.MEDIA_ROOT, 'categories')

        products_data = [
            {
                'name': 'Anti-Snoring Lips Strip',
                'category_name': 'Health & Beauty',
                'category_slug': 'health-beauty',
                'price': 9.99,
                'discount_price': 6.99,
                'description': 'Premium anti-snoring lip strips designed to promote nasal breathing and reduce snoring. Comfortable and easy to use.',
                'sku': 'ASLS-001',
                'stock': 150,
                'featured': True,
                'main_image_prefix': 'anti-snoring-lips-strip',
                'main_image_file': 'anti-snoring-lips-strip-1719059151.jpg',
                'extra_images': [
                    'anti-snoring-lips-strip1-1719059151.jpg',
                    'anti-snoring-lips-strip2-1719059151.jpg',
                    'anti-snoring-lips-strip3-1719059151.jpg',
                    'anti-snoring-lips-strip4-1719059151.jpg',
                    'anti-snoring-lips-strip5-1719059152.jpg',
                    'anti-snoring-lips-strip6-1719059152.jpg',
                    'anti-snoring-lips-strip7-1719059152.jpg',
                    'anti-snoring-lips-strip8-1719059152.jpg',
                ],
            },
            {
                'name': 'Earpick Flashlight Ear Cleaner',
                'category_name': 'Health & Beauty',
                'category_slug': 'health-beauty',
                'price': 12.99,
                'discount_price': 8.99,
                'description': 'Safe and gentle ear cleaning tool with built-in LED flashlight for visibility. Ergonomically designed for comfortable use.',
                'sku': 'EPEC-001',
                'stock': 200,
                'featured': True,
                'main_image_prefix': 'Earpick-Flashlight-Ear-Cleaner',
                'main_image_file': 'Earpick-Flashlight-Ear-Cleaner-1653046204.jpg',
                'extra_images': [
                    'Earpick-Flashlight-Ear-Cleaner1-1653046204.jpg',
                    'Earpick-Flashlight-Ear-Cleaner2-1653046204.jpg',
                    'Earpick-Flashlight-Ear-Cleaner3-1653046205.jpg',
                    'Earpick-Flashlight-Ear-Cleaner5-1653046205.jpg',
                    'Earpick-Flashlight-Ear-Cleaner6-1653046206.jpg',
                ],
            },
            {
                'name': 'Smile Baby Knee Pad',
                'category_name': 'Baby Products',
                'category_slug': 'baby-products',
                'price': 14.99,
                'discount_price': 10.99,
                'description': 'Soft and comfortable knee pads for babies learning to crawl. Provides protection and cushioning for little knees.',
                'sku': 'SBKP-001',
                'stock': 120,
                'featured': True,
                'main_image_prefix': 'Smile-Baby-Knee-Pad-Knee-Cushi',
                'main_image_file': 'Smile-Baby-Knee-Pad-Knee-Cushi-1678874850.jpg',
                'extra_images': [
                    'Smile-Baby-Knee-Pad-Knee-Cushi1-1678874850.jpg',
                    'Smile-Baby-Knee-Pad-Knee-Cushi2-1678874850.jpg',
                    'Smile-Baby-Knee-Pad-Knee-Cushi3-1678874851.jpg',
                    'Smile-Baby-Knee-Pad-Knee-Cushi4-1678874851.jpg',
                ],
            },
            {
                'name': 'V-Shape Baby Safety Protection',
                'category_name': 'Baby Products',
                'category_slug': 'baby-products',
                'price': 11.99,
                'discount_price': 7.99,
                'description': 'V-shaped safety protection pad for babies. Helps prevent head injuries and provides comfortable support.',
                'sku': 'VBSP-001',
                'stock': 100,
                'featured': True,
                'main_image_prefix': 'V-Shape-Baby-Safety-Protection',
                'main_image_file': 'V-Shape-Baby-Safety-Protection3-1683199752.jpg',
                'extra_images': [
                    'V-Shape-Baby-Safety-Protection1-1683199751.jpg',
                    'V-Shape-Baby-Safety-Protection2-1683199752.jpg',
                    'V-Shape-Baby-Safety-Protection4-1683199753.jpg',
                    'V-Shape-Baby-Safety-Protection5-1683199753.jpg',
                    'V-Shape-Baby-Safety-Protection6-1683199754.jpg',
                ],
            },
        ]

        for pd in products_data:
            cat, _ = Category.objects.get_or_create(
                slug=pd['category_slug'],
                defaults={'name': pd['category_name']},
            )

            if cat.name == 'Baby Products' and not cat.image:
                cat_img = os.path.join(media_categories, 'V-Shape-Baby-Safety-Protection3-1683199752.jpg')
                if os.path.exists(cat_img):
                    with open(cat_img, 'rb') as f:
                        cat.image.save('category_baby.jpg', File(f), save=True)

            main_img_path = os.path.join(media_products, pd['main_image_file'])
            product = Product.objects.create(
                name=pd['name'],
                category=cat,
                price=pd['price'],
                discount_price=pd['discount_price'],
                description=pd['description'],
                sku=pd['sku'],
                stock=pd['stock'],
                featured=pd['featured'],
                active=True,
            )

            if os.path.exists(main_img_path):
                with open(main_img_path, 'rb') as f:
                    product.image.save(pd['main_image_file'], File(f), save=True)

            for i, img_file in enumerate(pd['extra_images']):
                img_path = os.path.join(media_products, img_file)
                if os.path.exists(img_path):
                    pi = ProductImage(product=product, sort_order=i + 1)
                    with open(img_path, 'rb') as f:
                        pi.image.save(img_file, File(f), save=True)

            self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))

        self.stdout.write(self.style.SUCCESS('Done populating products!'))
