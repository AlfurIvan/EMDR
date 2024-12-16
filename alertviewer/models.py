from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    contact_email = models.EmailField()

    def __str__(self):
        return self.company_name


class Endpoint(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    host = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.ip})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    is_analyst = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Source(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Rule(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class MitigationStrategy(models.Model):
    description = models.TextField()

    def __str__(self):
        return self.description[:50]


class Alert(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('validated', 'Validated'),
        ('resolved', 'Resolved'),
    ]
    CLOSURE_CODE_CHOICES = [
        ('NA', 'N/A'),
        ('TP', 'True Positive'),
        ('FP', 'False Positive'),
        ('TPNM', 'True Positive Not Malicious'),
    ]
    MITIGATION_CHOICES = [
        ('NA', 'N/A'),
        ("soc", 'By SOC Team'),
        ("customer", 'By Customer'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    validator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='validated_alerts')
    validated_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    closure_code = models.CharField(max_length=50, choices=CLOSURE_CODE_CHOICES, default='NA')
    mitigation_strategy = models.ForeignKey(MitigationStrategy, on_delete=models.SET_NULL, null=True, blank=True)
    mitigation = models.CharField(max_length=50, choices=MITIGATION_CHOICES, default='NA')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    rules = models.ManyToManyField(Rule, related_name='alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='low')

    def __str__(self):
        return self.title
