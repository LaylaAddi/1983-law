# Generated manually for video evidence feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('youtube_url', models.CharField(help_text='Full YouTube URL', max_length=500)),
                ('video_id', models.CharField(help_text='YouTube video ID (extracted from URL)', max_length=20)),
                ('video_title', models.CharField(blank=True, help_text='Video title fetched from YouTube', max_length=255)),
                ('video_duration_seconds', models.IntegerField(blank=True, help_text='Total video length in seconds', null=True)),
                ('has_youtube_captions', models.BooleanField(default=False, help_text='Whether YouTube captions are available')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('evidence', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='video_evidence', to='documents.evidence')),
            ],
            options={
                'verbose_name': 'Video Evidence',
                'verbose_name_plural': 'Video Evidence',
            },
        ),
        migrations.CreateModel(
            name='VideoSpeaker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(help_text='Speaker label (e.g., "Speaker 1", "Male Officer")', max_length=100)),
                ('is_plaintiff', models.BooleanField(default=False, help_text='Is this speaker the plaintiff (user)?')),
                ('notes', models.CharField(blank=True, help_text='Description (e.g., "Officer with mustache")', max_length=255)),
                ('defendant', models.ForeignKey(blank=True, help_text='Link to defendant if this speaker is a defendant', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='video_speaker_attributions', to='documents.defendant')),
                ('video_evidence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='speakers', to='documents.videoevidence')),
            ],
            options={
                'verbose_name': 'Video Speaker',
                'verbose_name_plural': 'Video Speakers',
                'unique_together': {('video_evidence', 'label')},
            },
        ),
        migrations.CreateModel(
            name='VideoCapture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time_seconds', models.IntegerField(help_text='Clip start time in seconds (e.g., 302 for 5:02)')),
                ('end_time_seconds', models.IntegerField(help_text='Clip end time in seconds (e.g., 333 for 5:33)')),
                ('raw_transcript', models.TextField(blank=True, help_text='Extracted transcript text (unedited)')),
                ('attributed_transcript', models.TextField(blank=True, help_text='User-edited transcript with speaker attributions')),
                ('extraction_method', models.CharField(blank=True, choices=[('youtube', 'YouTube Captions'), ('whisper', 'Whisper Transcription')], help_text='How the transcript was extracted', max_length=20)),
                ('extraction_status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', help_text='Current status of transcript extraction', max_length=20)),
                ('extraction_error', models.TextField(blank=True, help_text='Error message if extraction failed')),
                ('ai_use_recorded', models.BooleanField(default=False, help_text='Whether this extraction was counted toward AI usage limit')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('video_evidence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='captures', to='documents.videoevidence')),
            ],
            options={
                'verbose_name': 'Video Capture',
                'verbose_name_plural': 'Video Captures',
                'ordering': ['start_time_seconds'],
            },
        ),
    ]
