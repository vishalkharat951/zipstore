from django.db import models


class PhonePeSettings(models.Model):
    class Environment(models.TextChoices):
        UAT = 'uat', 'UAT (Test)'
        PRODUCTION = 'production', 'Production'

    merchant_id = models.CharField(max_length=255)
    salt_key = models.CharField(max_length=255)
    salt_index = models.CharField(max_length=10)
    environment = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.UAT
    )
    callback_url = models.URLField(
        help_text='PhonePe will redirect here after payment'
    )
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PhonePe Settings'
        verbose_name_plural = 'PhonePe Settings'

    def __str__(self):
        return f'PhonePe ({self.get_environment_display()})'

    def save(self, *args, **kwargs):
        if self.active:
            PhonePeSettings.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(active=True).first()


class PaymentTransaction(models.Model):
    class PaymentMethod(models.TextChoices):
        PHONEPE = 'phonepe', 'PhonePe'
        UPI = 'upi', 'Direct UPI'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, related_name='transactions'
    )
    transaction_id = models.CharField(max_length=255, unique=True, blank=True)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.PHONEPE
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    response_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_id or "N/A"} — {self.get_payment_status_display()}'
