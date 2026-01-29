"""
Document generation service for creating court-ready Section 1983 complaints.
Uses AI to write professional legal documents with case law properly integrated.
"""
import json
from django.conf import settings
from openai import OpenAI


class DocumentGenerator:
    """
    Generates a professionally written Section 1983 federal complaint
    with case law citations integrated into proper legal arguments.
    """

    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        self.client = OpenAI(api_key=api_key)

    def _get_prompt(self, prompt_type: str) -> dict:
        """
        Fetch a prompt from the database AIPrompt model.

        Args:
            prompt_type: The type of prompt (e.g., 'generate_facts')

        Returns:
            dict with prompt config, or None if not found
        """
        from documents.models import AIPrompt
        prompt = AIPrompt.objects.filter(
            prompt_type=prompt_type,
            is_active=True
        ).first()

        if not prompt:
            return None

        return {
            'system_message': prompt.system_message,
            'user_prompt_template': prompt.user_prompt_template,
            'model_name': prompt.model_name,
            'temperature': prompt.temperature,
            'max_tokens': prompt.max_tokens,
        }

    def generate_complaint(self, document_data: dict) -> dict:
        """
        Generate a complete Section 1983 federal complaint.

        Args:
            document_data: Dict containing all document information:
                - plaintiff: plaintiff info dict
                - defendants: list of defendant dicts
                - incident: incident overview dict
                - narrative: incident narrative dict
                - rights_violated: rights violated dict
                - damages: damages dict
                - relief: relief sought dict
                - case_law: list of accepted case law citations
                - court: federal district court name

        Returns:
            dict with 'success' and 'document' containing generated sections
        """
        # Generate each section of the complaint
        sections = {}

        # 1. Caption
        sections['caption'] = self._generate_caption(document_data)

        # 2. Introduction
        sections['introduction'] = self._generate_introduction(document_data)

        # 3. Jurisdiction and Venue
        sections['jurisdiction'] = self._generate_jurisdiction(document_data)

        # 4. Parties
        sections['parties'] = self._generate_parties(document_data)

        # 5. Statement of Facts
        sections['facts'] = self._generate_facts(document_data)

        # 6. Causes of Action (with case law integrated)
        sections['causes_of_action'] = self._generate_causes_of_action(document_data)

        # 7. Prayer for Relief
        sections['prayer'] = self._generate_prayer(document_data)

        # 8. Jury Demand
        sections['jury_demand'] = self._generate_jury_demand(document_data)

        # 9. Signature Block
        sections['signature'] = self._generate_signature(document_data)

        return {
            'success': True,
            'document': sections,
        }

    def _generate_caption(self, data: dict) -> str:
        """Generate the case caption."""
        plaintiff = data.get('plaintiff', {})
        defendants = data.get('defendants', [])
        court = data.get('court', 'UNITED STATES DISTRICT COURT')

        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip()
        if not plaintiff_name:
            plaintiff_name = "PLAINTIFF"

        # Build defendant lines for caption
        # Separate individuals from agencies, and collect unique agencies
        individual_defendants = []
        agency_defendants = []
        agencies_from_individuals = set()

        for d in defendants:
            d_type = d.get('defendant_type', 'individual')
            name = d.get('name', '')
            title = d.get('title_rank', '')
            agency = d.get('agency_name', '')

            if d_type == 'individual' and name:
                # Format: OFFICER JOHN DOE or SGT. JOHN DOE
                if title:
                    formatted_name = f"{title.upper()} {name.upper()}"
                else:
                    formatted_name = name.upper()
                individual_defendants.append(formatted_name)
                # Track agency for inclusion
                if agency:
                    agencies_from_individuals.add(agency.upper())
            elif d_type == 'agency' and name:
                agency_defendants.append(name.upper())

        # Also add agencies from individuals if not already listed as agency defendants
        for agency in agencies_from_individuals:
            if agency not in agency_defendants:
                agency_defendants.append(agency)

        # Build the defendant block
        all_defendants = individual_defendants + agency_defendants

        if not all_defendants:
            defendant_block = "UNKNOWN DEFENDANTS"
        elif len(all_defendants) == 1:
            defendant_block = f"{all_defendants[0]},\n    individually and in official capacity"
        elif len(all_defendants) == 2:
            defendant_block = f"{all_defendants[0]}, individually and\n    in official capacity, and\n{all_defendants[1]}"
        else:
            # Multiple defendants - list first two + et al.
            defendant_block = f"{all_defendants[0]}, individually and\n    in official capacity,\n{all_defendants[1]}, et al."

        caption = f"""{court.upper()}

{plaintiff_name.upper()},
    Plaintiff,

v.                                          Case No. ________________

{defendant_block},
    Defendants.

________________________________________

COMPLAINT FOR VIOLATION OF CIVIL RIGHTS
PURSUANT TO 42 U.S.C. § 1983

________________________________________"""

        return caption

    def _generate_introduction(self, data: dict) -> str:
        """Generate the introduction paragraph."""
        plaintiff = data.get('plaintiff', {})
        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip()

        intro = f"""COMES NOW Plaintiff {plaintiff_name}, proceeding {"pro se" if plaintiff.get('is_pro_se', True) else "through counsel"}, and for their Complaint against Defendants, states as follows:"""

        return intro

    def _generate_jurisdiction(self, data: dict) -> str:
        """Generate jurisdiction and venue section."""
        incident = data.get('incident', {})
        state = incident.get('state', '[STATE]')

        jurisdiction = """JURISDICTION AND VENUE

1. This Court has subject matter jurisdiction over this action pursuant to 28 U.S.C. § 1331 (federal question jurisdiction) and 28 U.S.C. § 1343 (civil rights jurisdiction).

2. This action arises under the Constitution and laws of the United States, specifically 42 U.S.C. § 1983, which provides a remedy for the deprivation of rights secured by the Constitution.

3. Venue is proper in this district pursuant to 28 U.S.C. § 1391(b) because a substantial part of the events or omissions giving rise to the claims occurred in this judicial district."""

        return jurisdiction

    def _generate_parties(self, data: dict) -> str:
        """Generate the parties section."""
        plaintiff = data.get('plaintiff', {})
        defendants = data.get('defendants', [])
        incident = data.get('incident', {})

        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip()
        address = f"{plaintiff.get('city', '')}, {plaintiff.get('state', '')}".strip(', ')

        parties = f"""PARTIES

4. Plaintiff {plaintiff_name} is an adult individual and citizen of the United States, residing in {address or '[CITY, STATE]'}. At all times relevant to this Complaint, Plaintiff was engaged in constitutionally protected activity.

"""
        para_num = 5
        for i, defendant in enumerate(defendants):
            name = defendant.get('name', f'Defendant {i+1}')
            d_type = defendant.get('defendant_type', 'individual')
            agency = defendant.get('agency_name', '')
            title = defendant.get('title_rank', '')

            if d_type == 'individual':
                title_str = f", {title}," if title else ""
                agency_str = f" employed by {agency}" if agency else ""
                parties += f"""{para_num}. Defendant {name}{title_str} is an individual who, at all times relevant to this Complaint, was acting under color of state law as a law enforcement officer{agency_str}. Defendant {name} is sued in both their individual and official capacity.

"""
            else:
                parties += f"""{para_num}. Defendant {name} is a governmental entity that, at all times relevant to this Complaint, was responsible for the training, supervision, and conduct of its law enforcement officers. Defendant {name} is a "person" within the meaning of 42 U.S.C. § 1983.

"""
            para_num += 1

        return parties.strip()

    def _generate_facts(self, data: dict) -> str:
        """Generate the statement of facts using AI."""
        incident = data.get('incident', {})
        narrative = data.get('narrative', {})
        plaintiff = data.get('plaintiff', {})
        defendants = data.get('defendants', [])
        witnesses = data.get('witnesses', [])
        video_transcripts = data.get('video_transcripts', [])

        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip() or "Plaintiff"

        # Build witness information for context
        witness_info = []
        for w in witnesses:
            witness_entry = {
                'name': w.get('name', 'Unknown witness'),
                'relationship': w.get('relationship', ''),
                'what_they_witnessed': w.get('what_they_witnessed', ''),
                'has_evidence': w.get('has_evidence', False),
                'evidence_description': w.get('evidence_description', ''),
                'prior_interactions': w.get('prior_interactions', ''),
                'willing_to_testify': w.get('willing_to_testify', False),
            }
            witness_info.append(witness_entry)

        # Build context for AI
        context = {
            'plaintiff_name': plaintiff_name,
            'incident_date': incident.get('incident_date', ''),
            'incident_time': incident.get('incident_time', ''),
            'incident_location': incident.get('incident_location', ''),
            'city': incident.get('city', ''),
            'state': incident.get('state', ''),
            'was_recording': incident.get('was_recording', False),
            'summary': narrative.get('summary', ''),
            'detailed_narrative': narrative.get('detailed_narrative', ''),
            'what_were_you_doing': narrative.get('what_were_you_doing', ''),
            'what_was_said': narrative.get('what_was_said', ''),
            'physical_actions': narrative.get('physical_actions', ''),
            'how_it_ended': narrative.get('how_it_ended', ''),
            'defendants': [d.get('name', '') for d in defendants],
            'witnesses': witness_info,
        }

        # Build witness section for prompt
        witness_prompt_section = ""
        if witness_info:
            witness_prompt_section = "\n\nWITNESSES AND THEIR EVIDENCE:\n"
            for w in witness_info:
                witness_prompt_section += f"\n- {w['name']}"
                if w['relationship']:
                    witness_prompt_section += f" ({w['relationship']})"
                witness_prompt_section += ":"
                if w['what_they_witnessed']:
                    witness_prompt_section += f"\n  What they witnessed: {w['what_they_witnessed']}"
                if w['has_evidence'] and w['evidence_description']:
                    witness_prompt_section += f"\n  CAPTURED EVIDENCE: {w['evidence_description']}"
                if w['prior_interactions']:
                    witness_prompt_section += f"\n  Prior interactions with defendants: {w['prior_interactions']}"
                if w['willing_to_testify']:
                    witness_prompt_section += "\n  (Willing to testify)"

        # Build video transcript section for prompt
        video_prompt_section = ""
        if video_transcripts:
            video_prompt_section = "\n\nVIDEO EVIDENCE TRANSCRIPTS:\n"
            video_prompt_section += "(These are transcripts from video recordings of the incident. Quote relevant statements with timestamps.)\n"
            for i, vt in enumerate(video_transcripts, 1):
                video_prompt_section += f"\n[Video {i}: {vt.get('video_title', 'Video Evidence')}]"
                video_prompt_section += f"\nTimestamp: {vt.get('start_time', '')} - {vt.get('end_time', '')}"
                if vt.get('speakers'):
                    speakers_str = ', '.join([f"{k}: {v}" for k, v in vt['speakers'].items()])
                    video_prompt_section += f"\nSpeakers: {speakers_str}"
                video_prompt_section += f"\nTranscript:\n\"{vt.get('transcript', '')}\"\n"

        # Load prompt from database
        prompt_config = self._get_prompt('generate_facts')

        if prompt_config:
            # Use database prompt
            prompt = prompt_config['user_prompt_template'].format(
                plaintiff_name=context['plaintiff_name'],
                incident_date=context['incident_date'],
                incident_time=context['incident_time'],
                incident_location=context['incident_location'],
                city=context['city'],
                state=context['state'],
                was_recording=context['was_recording'],
                what_were_you_doing=context['what_were_you_doing'],
                detailed_narrative=context['detailed_narrative'],
                what_was_said=context['what_was_said'],
                physical_actions=context['physical_actions'],
                how_it_ended=context['how_it_ended'],
                defendants=', '.join(context['defendants']),
                witness_section=witness_prompt_section,
                video_section=video_prompt_section,
            )
            system_message = prompt_config['system_message']
            model_name = prompt_config['model_name']
            temperature = prompt_config['temperature']
            max_tokens = prompt_config['max_tokens']
        else:
            # Fallback to hardcoded prompt if database prompt not found
            prompt = f"""Write the STATEMENT OF FACTS section for a Section 1983 federal complaint based on these details:

PLAINTIFF: {context['plaintiff_name']}
DATE: {context['incident_date']}
TIME: {context['incident_time']}
LOCATION: {context['incident_location']}, {context['city']}, {context['state']}
WAS RECORDING: {context['was_recording']}

NARRATIVE DETAILS:
- What plaintiff was doing: {context['what_were_you_doing']}
- What happened: {context['detailed_narrative']}
- What was said: {context['what_was_said']}
- Physical actions: {context['physical_actions']}
- How it ended: {context['how_it_ended']}

DEFENDANTS: {', '.join(context['defendants'])}{witness_prompt_section}{video_prompt_section}

REQUIREMENTS:
1. Write in formal legal style with numbered paragraphs
2. Use third person ("Plaintiff" not "I")
3. Be chronological and specific about times, locations, actions
4. State facts objectively without legal conclusions
5. Each paragraph should focus on one key fact or event
6. Start paragraph numbers at 10 (previous sections used 1-9)
7. Reference defendants by name where known
8. Include specific details that support the constitutional claims
9. If witnesses captured video/photo evidence, include a paragraph stating that the incident was recorded and describing what the recording captured
10. If witnesses have prior interactions with defendants, this may be relevant to establishing pattern or motive - include if appropriate
11. ONLY if VIDEO EVIDENCE TRANSCRIPTS are provided above, incorporate key quotes from the video with proper attribution. Do NOT invent or reference timestamps unless actual transcript text is provided above
12. If WAS RECORDING is True but no VIDEO EVIDENCE TRANSCRIPTS are provided, you may mention that the incident was recorded, but do NOT reference specific timestamps or quote content that was not provided

Write ONLY the Statement of Facts section, starting with the header "STATEMENT OF FACTS"."""
            system_message = "You are an expert legal writer drafting Section 1983 civil rights complaints for federal court. Write clear, factual, professional legal prose. Use numbered paragraphs and formal legal style."
            model_name = "gpt-4o-mini"
            temperature = 0.3
            max_tokens = 2000

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"""STATEMENT OF FACTS

10. On or about {context['incident_date']}, Plaintiff {context['plaintiff_name']} was present at {context['incident_location']}, {context['city']}, {context['state']}.

11. [Facts to be supplemented based on incident narrative]

(Error generating detailed facts: {str(e)})"""

    def _generate_causes_of_action(self, data: dict) -> dict:
        """Generate causes of action with case law integrated."""
        rights = data.get('rights_violated', {})
        case_law = data.get('case_law', [])
        plaintiff = data.get('plaintiff', {})
        defendants = data.get('defendants', [])
        narrative = data.get('narrative', {})

        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip() or "Plaintiff"
        defendant_names = [d.get('name', 'Defendant') for d in defendants]

        causes = []
        cause_num = 1

        # Group case law by amendment
        case_law_by_amendment = {}
        for cl in case_law:
            amendment = cl.get('amendment', '')
            if amendment not in case_law_by_amendment:
                case_law_by_amendment[amendment] = []
            case_law_by_amendment[amendment].append(cl)

        # First Amendment violations
        if rights.get('first_amendment'):
            first_cases = case_law_by_amendment.get('first', [])
            cause = self._generate_single_cause(
                cause_num=cause_num,
                amendment="First",
                violation_type=self._get_first_amendment_type(rights),
                plaintiff_name=plaintiff_name,
                defendant_names=defendant_names,
                narrative=narrative,
                case_law=first_cases,
                details=rights.get('first_amendment_details', '')
            )
            causes.append(cause)
            cause_num += 1

        # Fourth Amendment violations
        if rights.get('fourth_amendment'):
            fourth_cases = case_law_by_amendment.get('fourth', [])
            cause = self._generate_single_cause(
                cause_num=cause_num,
                amendment="Fourth",
                violation_type=self._get_fourth_amendment_type(rights),
                plaintiff_name=plaintiff_name,
                defendant_names=defendant_names,
                narrative=narrative,
                case_law=fourth_cases,
                details=rights.get('fourth_amendment_details', '')
            )
            causes.append(cause)
            cause_num += 1

        # Fifth Amendment violations
        if rights.get('fifth_amendment'):
            fifth_cases = case_law_by_amendment.get('fifth', [])
            cause = self._generate_single_cause(
                cause_num=cause_num,
                amendment="Fifth",
                violation_type=self._get_fifth_amendment_type(rights),
                plaintiff_name=plaintiff_name,
                defendant_names=defendant_names,
                narrative=narrative,
                case_law=fifth_cases,
                details=rights.get('fifth_amendment_details', '')
            )
            causes.append(cause)
            cause_num += 1

        # Fourteenth Amendment violations
        if rights.get('fourteenth_amendment'):
            fourteenth_cases = case_law_by_amendment.get('fourteenth', [])
            cause = self._generate_single_cause(
                cause_num=cause_num,
                amendment="Fourteenth",
                violation_type=self._get_fourteenth_amendment_type(rights),
                plaintiff_name=plaintiff_name,
                defendant_names=defendant_names,
                narrative=narrative,
                case_law=fourteenth_cases,
                details=rights.get('fourteenth_amendment_details', '')
            )
            causes.append(cause)
            cause_num += 1

        return causes

    def _generate_single_cause(self, cause_num: int, amendment: str, violation_type: str,
                                plaintiff_name: str, defendant_names: list, narrative: dict,
                                case_law: list, details: str) -> dict:
        """Generate a single cause of action with AI."""

        # Format case law for the prompt
        case_citations = []
        for cl in case_law:
            case_citations.append({
                'name': cl.get('case_name', ''),
                'citation': cl.get('citation', ''),
                'key_holding': cl.get('key_holding', ''),
                'explanation': cl.get('explanation', ''),
            })

        facts_summary = narrative.get('detailed_narrative', '') or narrative.get('summary', '')

        prompt = f"""Write a CAUSE OF ACTION for a Section 1983 complaint with the following parameters:

CAUSE OF ACTION NUMBER: {cause_num}
AMENDMENT VIOLATED: {amendment} Amendment
TYPE OF VIOLATION: {violation_type}
PLAINTIFF: {plaintiff_name}
DEFENDANTS: {', '.join(defendant_names)}

FACTS OF THE CASE:
{facts_summary}

ADDITIONAL DETAILS ABOUT VIOLATION:
{details}

CASE LAW TO CITE (integrate these naturally into the legal argument):
{json.dumps(case_citations, indent=2)}

REQUIREMENTS:
1. Start with a header like "FIRST CAUSE OF ACTION" (use ordinal: FIRST, SECOND, THIRD, etc.)
2. Include subheader: "({violation_type} - {amendment} Amendment)"
3. Include "Against Defendant [names]"
4. Write numbered paragraphs (start at a reasonable number like 30+)
5. First paragraph: Incorporate by reference all preceding paragraphs
6. State the legal standard from the Constitution and relevant case law
7. INTEGRATE case law citations naturally - explain the legal standard from each case and apply it to these facts
8. Do NOT just list cases at the end - weave them into the legal argument
9. Connect the defendant's specific conduct to the constitutional violation
10. End with a conclusion that defendants violated plaintiff's rights

EXAMPLE OF PROPER CASE LAW INTEGRATION:
"The Fourth Amendment, made applicable to the states through the Fourteenth Amendment, protects individuals from unreasonable seizures, including the use of excessive force. Graham v. Connor, 490 U.S. 386 (1989). In Graham, the Supreme Court held that claims of excessive force must be analyzed under the 'objective reasonableness' standard. Here, Defendant Officer Smith's conduct was objectively unreasonable because..."

Write the complete cause of action:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert civil rights attorney drafting Section 1983 complaints. You write clear, persuasive legal arguments that properly integrate case law citations. Your writing follows federal court conventions and demonstrates how established legal precedent applies to the specific facts of each case."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            content = response.choices[0].message.content.strip()
        except Exception as e:
            content = f"""CAUSE OF ACTION {cause_num}
({violation_type} - {amendment} Amendment)
Against Defendants {', '.join(defendant_names)}

[Error generating cause of action: {str(e)}]

Plaintiff incorporates by reference all preceding paragraphs.

Defendants violated Plaintiff's {amendment} Amendment rights by {violation_type.lower()}.
"""

        return {
            'number': cause_num,
            'amendment': amendment,
            'violation_type': violation_type,
            'content': content,
            'case_law_used': [cl.get('case_name') for cl in case_law],
        }

    def _get_first_amendment_type(self, rights: dict) -> str:
        """Determine the specific First Amendment violation type."""
        types = []
        if rights.get('first_amendment_speech'):
            types.append("Freedom of Speech")
        if rights.get('first_amendment_press'):
            types.append("Freedom of Press")
        if rights.get('first_amendment_assembly'):
            types.append("Freedom of Assembly")
        if rights.get('first_amendment_petition'):
            types.append("Right to Petition")
        return ", ".join(types) if types else "First Amendment Violation"

    def _get_fourth_amendment_type(self, rights: dict) -> str:
        """Determine the specific Fourth Amendment violation type."""
        types = []
        if rights.get('fourth_amendment_force'):
            types.append("Excessive Force")
        if rights.get('fourth_amendment_arrest'):
            types.append("False Arrest")
        if rights.get('fourth_amendment_search'):
            types.append("Unreasonable Search")
        if rights.get('fourth_amendment_seizure'):
            types.append("Unreasonable Seizure")
        return ", ".join(types) if types else "Fourth Amendment Violation"

    def _get_fifth_amendment_type(self, rights: dict) -> str:
        """Determine the specific Fifth Amendment violation type."""
        types = []
        if rights.get('fifth_amendment_self_incrimination'):
            types.append("Self-Incrimination")
        if rights.get('fifth_amendment_due_process'):
            types.append("Due Process")
        return ", ".join(types) if types else "Fifth Amendment Violation"

    def _get_fourteenth_amendment_type(self, rights: dict) -> str:
        """Determine the specific Fourteenth Amendment violation type."""
        types = []
        if rights.get('fourteenth_amendment_due_process'):
            types.append("Due Process")
        if rights.get('fourteenth_amendment_equal_protection'):
            types.append("Equal Protection")
        return ", ".join(types) if types else "Fourteenth Amendment Violation"

    def _generate_prayer(self, data: dict) -> str:
        """Generate the prayer for relief section."""
        relief = data.get('relief', {})
        plaintiff = data.get('plaintiff', {})
        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip() or "Plaintiff"

        prayer = f"""PRAYER FOR RELIEF

WHEREFORE, Plaintiff {plaintiff_name} respectfully requests that this Court:

"""
        items = []
        letter = ord('A')

        items.append(f"{chr(letter)}. Enter judgment in favor of Plaintiff and against Defendants;")
        letter += 1

        if relief.get('compensatory_damages', True):
            amount = relief.get('compensatory_amount')
            if amount:
                items.append(f"{chr(letter)}. Award Plaintiff compensatory damages in the amount of ${amount:,.2f}, or such greater amount as proven at trial;")
            else:
                items.append(f"{chr(letter)}. Award Plaintiff compensatory damages in an amount to be determined at trial;")
            letter += 1

        if relief.get('punitive_damages'):
            items.append(f"{chr(letter)}. Award Plaintiff punitive damages against Defendants in their individual capacities in an amount sufficient to punish and deter such conduct;")
            letter += 1

        if relief.get('declaratory_relief'):
            items.append(f"{chr(letter)}. Issue a declaratory judgment that Defendants' actions violated Plaintiff's constitutional rights;")
            letter += 1

        if relief.get('injunctive_relief'):
            desc = relief.get('injunctive_description', '')
            if desc:
                items.append(f"{chr(letter)}. Issue injunctive relief ordering Defendants to {desc};")
            else:
                items.append(f"{chr(letter)}. Issue appropriate injunctive relief;")
            letter += 1

        if relief.get('attorney_fees', True):
            items.append(f"{chr(letter)}. Award Plaintiff reasonable attorney's fees and costs pursuant to 42 U.S.C. § 1988;")
            letter += 1

        items.append(f"{chr(letter)}. Award Plaintiff pre-judgment and post-judgment interest as allowed by law;")
        letter += 1

        items.append(f"{chr(letter)}. Grant such other and further relief as this Court deems just and proper.")

        prayer += "\n\n".join(items)

        return prayer

    def _generate_jury_demand(self, data: dict) -> str:
        """Generate jury demand section."""
        relief = data.get('relief', {})

        if relief.get('jury_trial_demanded', True):
            return """JURY DEMAND

Plaintiff hereby demands a trial by jury on all issues so triable."""
        else:
            return ""

    def _generate_signature(self, data: dict) -> str:
        """Generate signature block."""
        plaintiff = data.get('plaintiff', {})
        is_pro_se = plaintiff.get('is_pro_se', True)

        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip()
        address = plaintiff.get('street_address', '')
        city_state = f"{plaintiff.get('city', '')}, {plaintiff.get('state', '')} {plaintiff.get('zip_code', '')}".strip()
        phone = plaintiff.get('phone', '')
        email = plaintiff.get('email', '')

        date_line = "Dated: _______________________"

        if is_pro_se:
            signature = f"""{date_line}

Respectfully submitted,


_________________________________
{plaintiff_name}
Plaintiff, Pro Se
{address}
{city_state}
Phone: {phone}
Email: {email}"""
        else:
            attorney_name = plaintiff.get('attorney_name', '')
            attorney_bar = plaintiff.get('attorney_bar_number', '')
            attorney_firm = plaintiff.get('attorney_firm_name', '')
            attorney_address = plaintiff.get('attorney_street_address', '')
            attorney_city_state = f"{plaintiff.get('attorney_city', '')}, {plaintiff.get('attorney_state', '')} {plaintiff.get('attorney_zip_code', '')}".strip()
            attorney_phone = plaintiff.get('attorney_phone', '')
            attorney_email = plaintiff.get('attorney_email', '')

            signature = f"""{date_line}

Respectfully submitted,


_________________________________
{attorney_name}
Bar No. {attorney_bar}
{attorney_firm}
{attorney_address}
{attorney_city_state}
Phone: {attorney_phone}
Email: {attorney_email}

Attorney for Plaintiff"""

        return signature
