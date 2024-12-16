from django.contrib import admin

from .models import (
    Customer,
    Endpoint,
    UserProfile,
    Source,
    Rule,
    MitigationStrategy,
    Alert
)

admin.site.register(Alert)
admin.site.register(Customer)
admin.site.register(Endpoint)
admin.site.register(UserProfile)
admin.site.register(Source)
admin.site.register(Rule)
admin.site.register(MitigationStrategy)
