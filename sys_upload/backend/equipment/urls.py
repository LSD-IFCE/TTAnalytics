from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'api/brands', views.BrandViewSet)
router.register(r'api/grips', views.GripViewSet)
router.register(r'api/handedness', views.HandednessViewSet)
router.register(r'api/player-types', views.PlayerTypeViewSet)
router.register(r'api/rubbers', views.RubberViewSet)
router.register(r'api/blades', views.BladeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Views para templates
    path('equipamentos/', views.equipment_list, name='equipment_list'),
    path('equipamentos/novo/', views.equipment_add, name='equipment_add'),
    path('equipamentos/marcas/nova/', views.brand_add, name='brand_add'),
    path('equipamentos/marcas/<int:pk>/editar/', views.brand_edit, name='brand_edit'),
    path('equipamentos/<str:equipment_type>/<int:pk>/editar/', views.equipment_edit, name='equipment_edit'),
    path('empunhaduras/', views.grip_list, name='grip_list'),
    path('tipos-atleta/', views.player_type_list, name='player_type_list'),
]