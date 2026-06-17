from rest_framework import serializers
from .models import Brand, Grip, Handedness, PlayerType, Rubber, Blade


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class GripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grip
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class HandednessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Handedness
        fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PlayerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerType
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class RubberSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Brand.objects.filter(is_active=True),
        allow_null=True,
        required=False
    )
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.profile.full_name', read_only=True)
    
    class Meta:
        model = Rubber
        fields = [
            'id', 'name', 'brand', 'category', 'rubber_type',
            'thickness', 'color', 'description', 'is_active', 'brand_name',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_name', 'created_at', 'updated_at']

class BladeSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Brand.objects.filter(is_active=True),
        allow_null=True,
        required=False
    )
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.profile.full_name', read_only=True)
    
    class Meta:
        model = Blade
        fields = [
            'id', 'name', 'brand', 'blade_type', 'speed_class',
            'weight', 'layers', 'handle', 'description', 'is_active', 'brand_name',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_name', 'created_at', 'updated_at']