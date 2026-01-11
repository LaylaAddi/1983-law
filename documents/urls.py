from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Document CRUD
    path('', views.document_list, name='document_list'),
    path('new/', views.document_create, name='document_create'),
    path('<int:document_id>/', views.document_detail, name='document_detail'),
    path('<int:document_id>/delete/', views.document_delete, name='document_delete'),
    path('<int:document_id>/fill-test-data/', views.fill_test_data, name='fill_test_data'),
    path('<int:document_id>/preview/', views.document_preview, name='document_preview'),

    # Section editing (interview style)
    path('<int:document_id>/section/<str:section_type>/', views.section_edit, name='section_edit'),
    path('<int:document_id>/section/<str:section_type>/add/', views.add_multiple_item, name='add_multiple_item'),
    path('<int:document_id>/section/<str:section_type>/delete/<int:item_id>/', views.delete_multiple_item, name='delete_multiple_item'),
    path('<int:document_id>/section/<str:section_type>/status/', views.update_section_status, name='update_section_status'),

    # AJAX endpoints for preview page
    path('<int:document_id>/section/<str:section_type>/save/', views.section_save_ajax, name='section_save_ajax'),
    path('<int:document_id>/section/<str:section_type>/delete-item/<int:item_id>/', views.delete_item_ajax, name='delete_item_ajax'),
]
