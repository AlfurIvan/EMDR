import django_filters

from .models import Alert, Source


class AlertFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Alert.STATUS_CHOICES)
    closure_code = django_filters.ChoiceFilter(choices=Alert.CLOSURE_CODE_CHOICES)
    source = django_filters.ModelChoiceFilter(queryset=Source.objects.all())
    timestamp_before = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr='lte')
    timestamp_after = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr='gte')

    class Meta:
        model = Alert
        fields = ['status', 'closure_code', 'source', 'timestamp_before', 'timestamp_after']
