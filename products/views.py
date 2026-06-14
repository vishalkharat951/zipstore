from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from .forms import ProductSearchForm
from .models import Category, Product


class HomeView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(
            active=True, featured=True
        ).select_related('category')[:8]
        context['latest_products'] = Product.objects.filter(
            active=True
        ).select_related('category')[:8]
        context['categories'] = Category.objects.filter(
            products__active=True
        ).distinct()[:6]
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(active=True)
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            self.category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=self.category)
        else:
            self.category = None
        return queryset.select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['all_categories'] = Category.objects.annotate(
            product_count=Count('products', filter=Q(products__active=True))
        ).filter(product_count__gt=0)
        context['total_count'] = Product.objects.filter(active=True).count()
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(active=True).select_related('category')

    def get_object(self):
        category_slug = self.kwargs.get('category_slug')
        slug = self.kwargs.get('slug')
        return get_object_or_404(
            self.get_queryset(),
            slug=slug,
            category__slug=category_slug,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            active=True, category=self.object.category
        ).exclude(id=self.object.id)[:4]
        return context


class ProductSearchView(ListView):
    model = Product
    template_name = 'products/product_search.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(active=True)
        self.form = ProductSearchForm(self.request.GET)
        if self.form.is_valid():
            q = self.form.cleaned_data.get('q')
            min_price = self.form.cleaned_data.get('min_price')
            max_price = self.form.cleaned_data.get('max_price')
            if q:
                queryset = queryset.filter(
                    Q(name__icontains=q) | Q(description__icontains=q)
                )
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
        return queryset.select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form
        return context


class CategoryListView(ListView):
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(
            products__active=True
        ).annotate(
            Count('products')
        ).distinct()
