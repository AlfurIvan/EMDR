from django.shortcuts import get_object_or_404
from rest_framework import serializers
from .models import (
    Customer,
    Endpoint,
    UserProfile,
    Source,
    Rule,
    MitigationStrategy,
    Alert
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class EndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = '__all__'

class EndpointCustSerializer(EndpointSerializer):
    class Meta(EndpointSerializer.Meta):
        fields = None
        exclude = ('customer',)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = '__all__'


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = '__all__'


class MitigationStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = MitigationStrategy
        fields = '__all__'


class AlertSerializer(serializers.ModelSerializer):
    rules = RuleSerializer(many=True, read_only=True)
    source = SourceSerializer(read_only=True)
    mitigation_strategy = MitigationStrategySerializer(read_only=True)
    customer = serializers.CharField(source='customer.name', read_only=True)
    endpoint = serializers.CharField(source='endpoint.name', read_only=True)

    class Meta:
        model = Alert
        fields = '__all__'


class AlertCreateSerializer(serializers.ModelSerializer):
    endpoint_id = serializers.IntegerField(write_only=True)
    source_name = serializers.CharField(write_only=True)
    customer_id = serializers.IntegerField(write_only=True)
    rules = serializers.ListField(
        child=serializers.CharField(), write_only=True
    )

    class Meta:
        model = Alert
        fields = ['title', 'description', 'endpoint_id', 'source_name', 'customer_id', 'rules']

    def validate(self, data):
        # Validate endpoint
        endpoint = get_object_or_404(Endpoint, id=data['endpoint_id'])
        if not endpoint.is_active:
            raise serializers.ValidationError({"endpoint_id": "Endpoint is not active."})

        # Validate source
        source = get_object_or_404(Source, name=data['source_name'])

        # Validate customer
        customer = get_object_or_404(Customer, id=data['customer_id'])

        # Validate rules
        rules = Rule.objects.filter(name__in=data['rules'])
        if rules.count() != len(data['rules']):
            raise serializers.ValidationError({"rules": "One or more rules not found."})

        data['endpoint'] = endpoint
        data['source'] = source
        data['customer'] = customer
        data['rules'] = rules
        return data

    def create(self, validated_data):
        rules = validated_data.pop('rules')
        alert = Alert.objects.create(
            title=validated_data['title'],
            description=validated_data['description'],
            endpoint=validated_data['endpoint'],
            source=validated_data['source'],
            customer=validated_data['customer']
        )
        alert.rules.set(rules)
        return alert

class AlertMitigationSelectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "mitigation",