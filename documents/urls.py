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
    path('<int:document_id>/review/', views.document_review, name='document_review'),
    path('<int:document_id>/download-pdf/', views.download_pdf, name='download_pdf'),
    path('<int:document_id>/generate-pdf/', views.start_pdf_generation, name='start_pdf_generation'),
    path('<int:document_id>/generate-pdf/status/', views.pdf_generation_status, name='pdf_generation_status'),

    # Section editing (interview style)
    path('<int:document_id>/section/<str:section_type>/', views.section_edit, name='section_edit'),
    path('<int:document_id>/section/<str:section_type>/add/', views.add_multiple_item, name='add_multiple_item'),
    path('<int:document_id>/section/<str:section_type>/delete/<int:item_id>/', views.delete_multiple_item, name='delete_multiple_item'),
    path('<int:document_id>/section/<str:section_type>/status/', views.update_section_status, name='update_section_status'),

    # Edit individual defendant
    path('<int:document_id>/defendant/<int:defendant_id>/edit/', views.edit_defendant, name='edit_defendant'),
    path('<int:document_id>/defendant/<int:defendant_id>/accept/', views.accept_defendant_agency, name='accept_defendant_agency'),

    # Edit individual witness
    path('<int:document_id>/witness/<int:witness_id>/edit/', views.edit_witness, name='edit_witness'),

    # Edit individual evidence
    path('<int:document_id>/evidence/<int:evidence_id>/edit/', views.edit_evidence, name='edit_evidence'),

    # AJAX endpoints for preview page
    path('<int:document_id>/section/<str:section_type>/save/', views.section_save_ajax, name='section_save_ajax'),
    path('<int:document_id>/section/<str:section_type>/delete-item/<int:item_id>/', views.delete_item_ajax, name='delete_item_ajax'),

    # District court lookup
    path('lookup-district-court/', views.lookup_district_court, name='lookup_district_court'),

    # AI rights analysis endpoint
    path('<int:document_id>/analyze-rights/', views.analyze_rights, name='analyze_rights'),

    # AI agency suggestion endpoint
    path('<int:document_id>/suggest-agency/', views.suggest_agency, name='suggest_agency'),

    # AI section content suggestion endpoint
    path('<int:document_id>/suggest-section/<str:section_type>/', views.suggest_section_content, name='suggest_section_content'),

    # AI address lookup endpoint (web search)
    path('<int:document_id>/lookup-address/', views.lookup_address, name='lookup_address'),

    # AI document review endpoint
    path('<int:document_id>/ai-review/', views.ai_review_document, name='ai_review_document'),
    path('<int:document_id>/generate-fix/', views.generate_fix, name='generate_fix'),
    path('<int:document_id>/apply-fix/', views.apply_fix, name='apply_fix'),

    # Tell Your Story (AI-assisted form filling)
    path('<int:document_id>/tell-your-story/', views.tell_your_story, name='tell_your_story'),
    path('<int:document_id>/parse-story/', views.parse_story, name='parse_story'),
    path('<int:document_id>/parse-story/status/', views.parse_story_status, name='parse_story_status'),
    path('<int:document_id>/apply-story-fields/', views.apply_story_fields, name='apply_story_fields'),

    # Payment
    path('<int:document_id>/checkout/', views.checkout, name='checkout'),
    path('<int:document_id>/checkout/success/', views.checkout_success, name='checkout_success'),
    path('<int:document_id>/checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Finalization
    path('<int:document_id>/finalize/', views.finalize_document, name='finalize'),

    # Promo codes / Referrals
    path('my-referral-code/', views.my_referral_code, name='my_referral_code'),
    path('validate-promo-code/', views.validate_promo_code, name='validate_promo_code'),
    path('promo-code/<int:code_id>/toggle/', views.toggle_promo_code, name='toggle_promo_code'),
    path('request-payout/', views.request_payout, name='request_payout'),

    # Admin referral management
    path('admin/referrals/', views.admin_referrals, name='admin_referrals'),
    path('admin/referrals/payout/<int:request_id>/process/', views.admin_process_payout, name='admin_process_payout'),
    path('admin/referrals/usage/<int:usage_id>/mark-paid/', views.admin_mark_usage_paid, name='admin_mark_usage_paid'),
    path('admin/referrals/code/<int:code_id>/edit/', views.admin_edit_promo_code, name='admin_edit_promo_code'),

    # Video Analysis (YouTube transcript extraction - subscribers only)
    path('<int:document_id>/video-analysis/', views.video_analysis, name='video_analysis'),
    path('<int:document_id>/video-analysis/add-video/', views.video_add, name='video_add'),
    path('<int:document_id>/evidence/<int:evidence_id>/link-youtube/', views.link_youtube_to_evidence, name='link_youtube_to_evidence'),
    path('<int:document_id>/evidence/<int:evidence_id>/unlink-youtube/', views.unlink_youtube_from_evidence, name='unlink_youtube_from_evidence'),
    path('<int:document_id>/evidence/quick-add-youtube/', views.quick_add_youtube_evidence, name='quick_add_youtube_evidence'),
    path('<int:document_id>/evidence/analyze-video/', views.analyze_video_evidence, name='analyze_video_evidence'),
    path('<int:document_id>/evidence/apply-suggestion/', views.apply_video_suggestion, name='apply_video_suggestion'),
    path('<int:document_id>/video-analysis/<int:video_id>/delete/', views.video_delete, name='video_delete'),
    path('<int:document_id>/video-analysis/<int:video_id>/add-capture/', views.video_add_capture, name='video_add_capture'),
    path('<int:document_id>/video-analysis/<int:video_id>/add-speaker/', views.video_add_speaker, name='video_add_speaker'),
    path('<int:document_id>/video-analysis/<int:video_id>/update-speaker/<int:speaker_id>/', views.video_update_speaker, name='video_update_speaker'),
    path('<int:document_id>/video-analysis/capture/<int:capture_id>/extract/', views.video_extract_transcript, name='video_extract_transcript'),
    path('<int:document_id>/video-analysis/capture/<int:capture_id>/delete/', views.video_delete_capture, name='video_delete_capture'),
    path('<int:document_id>/video-analysis/capture/<int:capture_id>/update/', views.video_update_capture, name='video_update_capture'),
]
