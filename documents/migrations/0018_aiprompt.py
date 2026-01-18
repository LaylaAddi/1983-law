# Generated manually for AI prompt templates

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0017_defendant_address_verified'),
        ('documents', '0017_merge_20260118_0545'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIPrompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt_type', models.CharField(
                    choices=[
                        ('parse_story', 'Parse Story - Analyzes user story and extracts structured data'),
                        ('analyze_rights', 'Analyze Rights - Identifies constitutional violations'),
                        ('suggest_agency', 'Suggest Agency - Finds defendants based on story'),
                        ('suggest_relief', 'Suggest Relief - Recommends legal relief options'),
                        ('find_law_enforcement', 'Find Law Enforcement - Identifies correct police/sheriff'),
                        ('lookup_address', 'Lookup Address - Finds agency addresses'),
                    ],
                    help_text='Which AI function this prompt is used for',
                    max_length=50,
                    unique=True
                )),
                ('title', models.CharField(help_text='Human-readable title displayed in admin', max_length=255)),
                ('description', models.TextField(help_text='Detailed description of what this prompt does and when it is used')),
                ('system_message', models.TextField(help_text='The system role message that sets AI behavior/persona')),
                ('user_prompt_template', models.TextField(help_text='The main prompt template. Use {variable_name} for placeholders like {city}, {state}, {story_text}')),
                ('available_variables', models.TextField(blank=True, help_text='Comma-separated list of variables available for this prompt (e.g., city, state, story_text)')),
                ('model_name', models.CharField(default='gpt-4o-mini', help_text='OpenAI model to use (e.g., gpt-4o-mini, gpt-4o)', max_length=50)),
                ('temperature', models.FloatField(default=0.1, help_text='AI temperature (0.0-1.0). Lower = more consistent, higher = more creative')),
                ('max_tokens', models.IntegerField(default=2000, help_text='Maximum tokens in the response')),
                ('is_active', models.BooleanField(default=True, help_text='If disabled, falls back to hardcoded prompt')),
                ('version', models.IntegerField(default=1, help_text='Version number for tracking changes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_edited_by', models.ForeignKey(
                    blank=True,
                    help_text='Admin user who last edited this prompt',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'AI Prompt',
                'verbose_name_plural': 'AI Prompts',
                'ordering': ['prompt_type'],
            },
        ),
    ]
