from django import forms


class ProductSearchForm(forms.Form):
    q = forms.CharField(
        label='Search',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search products...'}),
    )
    min_price = forms.DecimalField(
        required=False, widget=forms.NumberInput(attrs={'placeholder': 'Min'})
    )
    max_price = forms.DecimalField(
        required=False, widget=forms.NumberInput(attrs={'placeholder': 'Max'})
    )
