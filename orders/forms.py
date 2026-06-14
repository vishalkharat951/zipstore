from django import forms

from .models import Order


PAYMENT_CHOICES = [
    ('upi', 'UPI (Google Pay, PhonePe, Paytm, BHIM)'),
    ('phonepe', 'PhonePe Gateway'),
]


class CheckoutForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='upi',
    )

    class Meta:
        model = Order
        fields = ['full_name', 'mobile_number', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'John Doe'}),
            'mobile_number': forms.TextInput(attrs={'placeholder': '+1 (555) 123-4567'}),
            'address': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Street, City, State, Postal Code, Country',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-control form-control-lg'
