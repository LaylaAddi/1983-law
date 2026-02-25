from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # District court lookup (must be before <str:document_slug> catch-all)
    path('lookup-district-court/', views.lookup_district_court, name='lookup_district_court'),

    # Document CRUD
    path('', views.document_list, name='document_list'),
    path('new/', views.document_create, name='document_create'),
    path('<str:document_slug>/', views.document_detail, name='document_detail'),
    path('<str:document_slug>/delete/', views.document_delete, name='document_delete'),
    path('<str:document_slug>/fill-test-data/', views.fill_test_data, name='fill_test_data'),
    path('<str:document_slug>/preview/', views.document_preview, name='document_preview'),
    path('<str:document_slug>/review/', views.document_review, name='document_review'),
    path('<str:document_slug>/download-pdf/', views.download_pdf, name='download_pdf'),

    # Final Document Review - new pathway for editing actual document text
    path('<str:document_slug>/final/', views.final_review, name='final_review'),
    path('<str:document_slug>/final/generate/', views.generate_final_document, name='generate_final_document'),
    path('<str:document_slug>/final/save-section/', views.save_final_section, name='save_final_section'),
    path('<str:document_slug>/final/ai-review/', views.ai_review_final, name='ai_review_final'),
    path('<str:document_slug>/final/regenerate-section/', views.regenerate_final_section, name='regenerate_final_section'),
    path('<str:document_slug>/final/download-pdf/', views.download_final_pdf, name='download_final_pdf'),
    path('<str:document_slug>/generate-pdf/', views.start_pdf_generation, name='start_pdf_generation'),
    path('<str:document_slug>/generate-pdf/status/', views.pdf_generation_status, name='pdf_generation_status'),

    # Guided wizard
    path('<str:document_slug>/wizard/', views.wizard, name='wizard'),

    # Section editing (interview style)
    path('<str:document_slug>/section/<str:section_type>/', views.section_edit, name='section_edit'),
    path('<str:document_slug>/section/<str:section_type>/add/', views.add_multiple_item, name='add_multiple_item'),
    path('<str:document_slug>/section/<str:section_type>/delete/<str:item_slug>/', views.delete_multiple_item, name='delete_multiple_item'),
    path('<str:document_slug>/section/<str:section_type>/status/', views.update_section_status, name='update_section_status'),

    # Edit individual defendant
    path('<str:document_slug>/defendant/<str:defendant_slug>/edit/', views.edit_defendant, name='edit_defendant'),
    path('<str:document_slug>/defendant/<str:defendant_slug>/accept/', views.accept_defendant_agency, name='accept_defendant_agency'),

    # Edit individual witness
    path('<str:document_slug>/witness/<str:witness_slug>/edit/', views.edit_witness, name='edit_witness'),

    # Edit individual evidence
    path('<str:document_slug>/evidence/<str:evidence_slug>/edit/', views.edit_evidence, name='edit_evidence'),

    # AJAX endpoints for preview page
    path('<str:document_slug>/section/<str:section_type>/save/', views.section_save_ajax, name='section_save_ajax'),
    path('<str:document_slug>/section/<str:section_type>/delete-item/<str:item_slug>/', views.delete_item_ajax, name='delete_item_ajax'),

    # AI rights analysis endpoint
    path('<str:document_slug>/analyze-rights/', views.analyze_rights, name='analyze_rights'),

    # AI agency suggestion endpoint
    path('<str:document_slug>/suggest-agency/', views.suggest_agency, name='suggest_agency'),

    # AI section content suggestion endpoint
    path('<str:document_slug>/suggest-section/<str:section_type>/', views.suggest_section_content, name='suggest_section_content'),

    # AI address lookup endpoint (web search)
    path('<str:document_slug>/lookup-address/', views.lookup_address, name='lookup_address'),

    # AI document review endpoint
    path('<str:document_slug>/ai-review/', views.ai_review_document, name='ai_review_document'),
    path('<str:document_slug>/generate-fix/', views.generate_fix, name='generate_fix'),
    path('<str:document_slug>/apply-fix/', views.apply_fix, name='apply_fix'),

    # Tell Your Story (AI-assisted form filling)
    path('<str:document_slug>/tell-your-story/', views.tell_your_story, name='tell_your_story'),
    path('<str:document_slug>/parse-story/', views.parse_story, name='parse_story'),
    path('<str:document_slug>/parse-story/status/', views.parse_story_status, name='parse_story_status'),
    path('<str:document_slug>/apply-story-fields/', views.apply_story_fields, name='apply_story_fields'),

    # Payment
    path('<str:document_slug>/checkout/', views.checkout, name='checkout'),
    path('<str:document_slug>/checkout/success/', views.checkout_success, name='checkout_success'),
    path('<str:document_slug>/checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Finalization
    path('<str:document_slug>/finalize/', views.finalize_document, name='finalize'),

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
    path('<str:document_slug>/video-analysis/', views.video_analysis, name='video_analysis'),
    path('<str:document_slug>/video-analysis/add-video/', views.video_add, name='video_add'),
    path('<str:document_slug>/evidence/<str:evidence_slug>/link-youtube/', views.link_youtube_to_evidence, name='link_youtube_to_evidence'),
    path('<str:document_slug>/evidence/<str:evidence_slug>/unlink-youtube/', views.unlink_youtube_from_evidence, name='unlink_youtube_from_evidence'),
    path('<str:document_slug>/evidence/quick-add-youtube/', views.quick_add_youtube_evidence, name='quick_add_youtube_evidence'),
    path('<str:document_slug>/evidence/analyze-video/', views.analyze_video_evidence, name='analyze_video_evidence'),
    path('<str:document_slug>/evidence/apply-suggestion/', views.apply_video_suggestion, name='apply_video_suggestion'),
    path('<str:document_slug>/video-analysis/<str:video_slug>/delete/', views.video_delete, name='video_delete'),
    path('<str:document_slug>/video-analysis/<str:video_slug>/add-capture/', views.video_add_capture, name='video_add_capture'),
    path('<str:document_slug>/video-analysis/<str:video_slug>/add-speaker/', views.video_add_speaker, name='video_add_speaker'),
    path('<str:document_slug>/video-analysis/<str:video_slug>/update-speaker/<str:speaker_slug>/', views.video_update_speaker, name='video_update_speaker'),
    path('<str:document_slug>/video-analysis/capture/<str:capture_slug>/extract/', views.video_extract_transcript, name='video_extract_transcript'),
    path('<str:document_slug>/video-analysis/capture/<str:capture_slug>/delete/', views.video_delete_capture, name='video_delete_capture'),
    path('<str:document_slug>/video-analysis/capture/<str:capture_slug>/update/', views.video_update_capture, name='video_update_capture'),
]
