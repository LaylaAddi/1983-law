"""
Test data for populating document sections with realistic sample data.
Based on a typical First Amendment auditor case scenario.
"""
from datetime import date, time
from decimal import Decimal


def populate_test_data(document):
    """Populate all sections of a document with realistic test data."""
    from .models import (
        PlaintiffInfo, IncidentOverview, Defendant, IncidentNarrative,
        RightsViolated, Witness, Evidence, Damages, PriorComplaints, ReliefSought
    )

    sections = {s.section_type: s for s in document.sections.all()}

    # 1. Plaintiff Information
    if 'plaintiff_info' in sections:
        section = sections['plaintiff_info']
        PlaintiffInfo.objects.update_or_create(
            section=section,
            defaults={
                'full_name': 'John Michael Smith',
                'street_address': '1234 Liberty Lane',
                'city': 'Springfield',
                'state': 'Illinois',
                'zip_code': '62701',
                'phone': '(217) 555-0142',
                'email': 'jsmith.auditor@email.com',
                'is_pro_se': True,
            }
        )
        section.status = 'completed'
        section.save()

    # 2. Incident Overview
    if 'incident_overview' in sections:
        section = sections['incident_overview']
        IncidentOverview.objects.update_or_create(
            section=section,
            defaults={
                'incident_date': date(2024, 8, 15),
                'incident_time': time(14, 30),
                'incident_location': '100 North Main Street, City Hall Front Entrance',
                'city': 'Springfield',
                'state': 'Illinois',
                'location_type': 'Public sidewalk in front of government building',
                'was_recording': True,
                'recording_device': 'iPhone 15 Pro Max',
            }
        )
        section.status = 'completed'
        section.save()

    # 3. Defendants
    if 'defendants' in sections:
        section = sections['defendants']
        # Clear existing defendants
        Defendant.objects.filter(section=section).delete()

        # Add agency
        Defendant.objects.create(
            section=section,
            defendant_type='agency',
            name='Springfield Police Department',
            address='300 South 7th Street, Springfield, IL 62701',
            description='Municipal law enforcement agency responsible for training and supervision of officers',
        )

        # Add individual officers
        Defendant.objects.create(
            section=section,
            defendant_type='individual',
            name='Officer James Wilson',
            badge_number='4521',
            title_rank='Patrol Officer',
            agency_name='Springfield Police Department',
            address='300 South 7th Street, Springfield, IL 62701',
            description='White male, approximately 6\'1", 200 lbs, dark hair. Was the primary officer who made contact.',
        )

        Defendant.objects.create(
            section=section,
            defendant_type='individual',
            name='Sergeant Robert Thompson',
            badge_number='2187',
            title_rank='Sergeant',
            agency_name='Springfield Police Department',
            address='300 South 7th Street, Springfield, IL 62701',
            description='White male, approximately 5\'10", 180 lbs. Arrived as backup and approved the detention.',
        )

        section.status = 'completed'
        section.save()

    # 4. Incident Narrative
    if 'incident_narrative' in sections:
        section = sections['incident_narrative']
        IncidentNarrative.objects.update_or_create(
            section=section,
            defaults={
                'summary': 'While lawfully recording the exterior of City Hall from a public sidewalk, I was approached by police officers who demanded I stop recording, detained me for approximately 45 minutes, and threatened arrest for "suspicious activity" despite my compliance with all laws.',

                'detailed_narrative': '''On August 15, 2024, at approximately 2:30 PM, I was standing on the public sidewalk in front of Springfield City Hall, lawfully recording the building's exterior with my iPhone. I was conducting a First Amendment audit to document public spaces and test government officials' understanding of citizens' rights to record in public.

I was not blocking pedestrian traffic, was not on government property, and was not interfering with any government operations. I was simply standing on the public sidewalk recording the building facade and people entering/exiting through the main entrance.

After approximately 10 minutes of recording, Officer James Wilson approached me and immediately demanded to know what I was doing and why I was recording. I politely explained that I was exercising my First Amendment right to record in public. Officer Wilson stated that I was "acting suspicious" and demanded my identification.

I respectfully declined to provide ID, as I was not engaged in any criminal activity and Illinois does not have a stop-and-identify statute. Officer Wilson then called for backup. Sergeant Robert Thompson arrived approximately 5 minutes later.

Sergeant Thompson told me I was being detained for "suspicious activity" and that I was required to identify myself. When I again declined, stating I was exercising my constitutional rights, Sergeant Thompson stated I would be arrested for "obstruction" if I did not comply.

I was detained on the sidewalk for approximately 45 minutes while officers ran my description through their system and consulted with dispatch. During this time, I was not free to leave. Eventually, after finding no warrants or criminal history, I was released with a verbal warning to "stay away from government buildings."''',

                'what_were_you_doing': 'I was standing on a public sidewalk recording the exterior of City Hall with my smartphone. I was conducting a First Amendment audit, which is a constitutionally protected activity.',

                'initial_contact': 'Officer Wilson approached me from the City Hall entrance and immediately demanded to know what I was doing and why I was recording the building.',

                'what_was_said': '''Officer Wilson: "Hey, what are you doing? Why are you recording?"
Me: "I\'m exercising my First Amendment right to record in public."
Wilson: "You\'re acting suspicious. Let me see some ID."
Me: "I respectfully decline. I\'m not required to identify myself as I\'m not suspected of any crime."
Wilson: "Stay right here." [calls for backup]

Sergeant Thompson arrived and said: "What\'s going on here?"
Wilson: "This guy is recording the building and won\'t ID himself."
Thompson to me: "You\'re being detained for suspicious activity. I need to see your ID now."
Me: "On what grounds? Recording in public is not a crime."
Thompson: "If you don\'t show ID, I\'m going to arrest you for obstruction."''',

                'physical_actions': 'Officer Wilson positioned himself between me and my path of egress. When Sergeant Thompson arrived, they both stood in front of me in an intimidating manner. At one point, Sergeant Thompson placed his hand on his taser and stated "Don\'t make this difficult." I was not handcuffed but was clearly not free to leave.',

                'how_it_ended': 'After approximately 45 minutes of detention, during which officers consulted with dispatch and ran my description, I was told I was "free to go" but was warned to "stay away from government buildings" or I would be arrested. I immediately left the area and drove home.',
            }
        )
        section.status = 'completed'
        section.save()

    # 5. Rights Violated
    if 'rights_violated' in sections:
        section = sections['rights_violated']
        RightsViolated.objects.update_or_create(
            section=section,
            defaults={
                'first_amendment': True,
                'first_amendment_speech': True,
                'first_amendment_press': True,
                'first_amendment_assembly': False,
                'first_amendment_petition': False,
                'first_amendment_details': 'Officers violated my First Amendment rights by demanding I stop recording in a public place, retaliating against me for exercising my right to record public officials and public buildings, and attempting to chill my protected speech through threats of arrest. The right to record police and government officials in public spaces is clearly established under the First Amendment.',

                'fourth_amendment': True,
                'fourth_amendment_search': False,
                'fourth_amendment_seizure': True,
                'fourth_amendment_arrest': True,
                'fourth_amendment_force': False,
                'fourth_amendment_details': 'I was unlawfully seized when officers detained me for 45 minutes without reasonable suspicion of criminal activity. Recording in public is not a crime and does not constitute "suspicious activity." The detention amounted to a de facto arrest without probable cause.',

                'fifth_amendment': False,
                'fifth_amendment_self_incrimination': False,
                'fifth_amendment_due_process': False,
                'fifth_amendment_details': '',

                'fourteenth_amendment': True,
                'fourteenth_amendment_due_process': True,
                'fourteenth_amendment_equal_protection': False,
                'fourteenth_amendment_details': 'The officers\' actions deprived me of my liberty without due process of law. I was detained and threatened with arrest for engaging in constitutionally protected activity.',

                'other_rights': 'Illinois Constitution Article I, Section 4 (Freedom of Speech) was also violated.',
            }
        )
        section.status = 'completed'
        section.save()

    # 6. Witnesses
    if 'witnesses' in sections:
        section = sections['witnesses']
        # Clear existing witnesses
        Witness.objects.filter(section=section).delete()

        Witness.objects.create(
            section=section,
            name='Sarah Johnson',
            contact_info='(217) 555-0198, sjohnson@email.com',
            relationship='Bystander - was exiting City Hall during the incident',
            what_they_witnessed='Witnessed the entire interaction from when officers first approached me. Saw officers detain me on the sidewalk and heard Sergeant Thompson threaten to arrest me.',
            willing_to_testify=True,
        )

        Witness.objects.create(
            section=section,
            name='Michael Chen',
            contact_info='YouTube: @MikeChenAudits',
            relationship='Fellow First Amendment auditor - was recording from across the street',
            what_they_witnessed='Recorded the entire incident from approximately 50 feet away. Has video footage of the detention.',
            willing_to_testify=True,
        )

        section.status = 'completed'
        section.save()

    # 7. Evidence
    if 'evidence' in sections:
        section = sections['evidence']
        # Clear existing evidence
        Evidence.objects.filter(section=section).delete()

        Evidence.objects.create(
            section=section,
            evidence_type='video',
            title='My recording of the incident',
            description='Continuous recording from my iPhone showing the entire interaction with officers, including their demands to stop recording and threats of arrest.',
            date_created=date(2024, 8, 15),
            location_obtained='Recorded by me at the scene',
            is_in_possession=True,
            needs_subpoena=False,
            notes='Approximately 52 minutes of footage. Audio clearly captures all statements made by officers.',
        )

        Evidence.objects.create(
            section=section,
            evidence_type='video',
            title='Michael Chen\'s recording',
            description='Recording from fellow auditor showing the interaction from across the street.',
            date_created=date(2024, 8, 15),
            location_obtained='Obtained from Michael Chen',
            is_in_possession=True,
            needs_subpoena=False,
            notes='Shows officers surrounding me and the length of detention.',
        )

        Evidence.objects.create(
            section=section,
            evidence_type='body_cam',
            title='Officer Wilson body camera footage',
            description='Body camera footage from Officer Wilson should show the entire interaction.',
            date_created=date(2024, 8, 15),
            location_obtained='Springfield Police Department',
            is_in_possession=False,
            needs_subpoena=True,
            notes='FOIA request submitted 8/20/2024, pending response.',
        )

        Evidence.objects.create(
            section=section,
            evidence_type='document',
            title='CAD/Dispatch records',
            description='Computer-aided dispatch records showing the call for backup and duration of the stop.',
            date_created=date(2024, 8, 15),
            location_obtained='Springfield Police Department',
            is_in_possession=False,
            needs_subpoena=True,
            notes='Will show timeline and what was communicated to dispatch.',
        )

        section.status = 'completed'
        section.save()

    # 8. Damages
    if 'damages' in sections:
        section = sections['damages']
        Damages.objects.update_or_create(
            section=section,
            defaults={
                'physical_injury': False,
                'physical_injury_description': '',
                'medical_treatment': False,
                'medical_treatment_description': '',
                'ongoing_medical_issues': False,
                'ongoing_medical_description': '',

                'emotional_distress': True,
                'emotional_distress_description': 'The incident caused significant anxiety and stress. I experienced difficulty sleeping for several weeks afterward and felt anxious about exercising my First Amendment rights in public. I have been hesitant to conduct further audits due to fear of similar retaliation.',

                'property_damage': False,
                'property_damage_description': '',
                'lost_wages': True,
                'lost_wages_amount': Decimal('450.00'),
                'legal_fees': Decimal('500.00'),
                'medical_expenses': Decimal('0.00'),
                'other_expenses': Decimal('75.00'),
                'other_expenses_description': 'FOIA request fees and certified mail costs for complaints.',

                'reputation_harm': True,
                'reputation_harm_description': 'The incident was witnessed by multiple members of the public, including people entering and exiting City Hall. Being detained by police in public was humiliating and damaged my reputation in the community.',

                'other_damages': 'Chilling effect on my First Amendment activities. I have been reluctant to exercise my constitutional rights since this incident.',
            }
        )
        section.status = 'completed'
        section.save()

    # 9. Prior Complaints
    if 'prior_complaints' in sections:
        section = sections['prior_complaints']
        PriorComplaints.objects.update_or_create(
            section=section,
            defaults={
                'filed_internal_complaint': True,
                'internal_complaint_date': date(2024, 8, 22),
                'internal_complaint_description': 'Filed formal complaint with Springfield Police Department Internal Affairs division regarding the unlawful detention and First Amendment violations.',
                'internal_complaint_outcome': 'Received letter dated September 15, 2024 stating the complaint was "not sustained" and that officers acted within policy.',

                'filed_civilian_complaint': True,
                'civilian_complaint_date': date(2024, 8, 25),
                'civilian_complaint_description': 'Filed complaint with Springfield Civilian Police Review Board.',
                'civilian_complaint_outcome': 'Pending review. Hearing scheduled for November 2024.',

                'contacted_media': True,
                'media_contact_description': 'Uploaded my recording to YouTube on August 16, 2024. Video has received over 50,000 views. Was interviewed by local news station WICS on August 20, 2024.',

                'other_actions': 'Sent formal demand letter to Springfield City Attorney on September 1, 2024, requesting settlement. Received response on September 20, 2024 denying any wrongdoing.',
            }
        )
        section.status = 'completed'
        section.save()

    # 10. Relief Sought
    if 'relief_sought' in sections:
        section = sections['relief_sought']
        ReliefSought.objects.update_or_create(
            section=section,
            defaults={
                'compensatory_damages': True,
                'compensatory_amount': Decimal('50000.00'),
                'punitive_damages': True,
                'punitive_amount': Decimal('100000.00'),
                'attorney_fees': True,

                'injunctive_relief': True,
                'injunctive_description': 'Requesting the Court order Springfield Police Department to: (1) Implement training on First Amendment rights, specifically the right to record in public; (2) Issue a department-wide memorandum clarifying that recording in public is not "suspicious activity"; (3) Discipline the officers involved.',

                'declaratory_relief': True,
                'declaratory_description': 'Requesting the Court declare that: (1) Plaintiff had a clearly established First Amendment right to record in public; (2) Officers violated Plaintiff\'s First and Fourth Amendment rights; (3) The detention was unlawful.',

                'other_relief': 'Nominal damages of $1.00 for the constitutional violations, in addition to compensatory damages.',

                'jury_trial_demanded': True,
            }
        )
        section.status = 'completed'
        section.save()

    # Update document status
    document.status = 'review'
    document.save()

    return True
