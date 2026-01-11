"""
Help content for Section 1983 civil rights complaint sections.
Contains plain-English explanations, tips, and examples for each section.
"""

SECTION_HELP = {
    'plaintiff_info': {
        'title': 'Plaintiff Information',
        'overview': '''
            <strong>What is this?</strong> The plaintiff is YOU - the person whose rights were violated
            and who is filing this complaint. This section identifies you to the court.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> The court needs accurate contact information to send you
            notices about your case. Incorrect information could cause you to miss important deadlines.
        ''',
        'tips': [
            'Use your legal name exactly as it appears on your ID',
            'Provide an address where you can reliably receive mail',
            'Include a phone number where you can be reached during business hours',
        ],
        'fields': {
            'full_name': {
                'tooltip': 'Your complete legal name as shown on government-issued ID',
                'help': 'Enter your full legal name. This should match your driver\'s license or other official ID.',
            },
            'date_of_birth': {
                'tooltip': 'Your birth date - used to verify your identity',
                'help': 'This helps distinguish you from others with similar names.',
            },
            'address': {
                'tooltip': 'Where you currently live or receive mail',
                'help': 'The court will send important documents here. Use an address where you reliably receive mail.',
            },
            'phone': {
                'tooltip': 'Best phone number to reach you',
                'help': 'Include area code. The court or opposing counsel may need to contact you.',
            },
            'email': {
                'tooltip': 'Email address for electronic communications',
                'help': 'Many courts now allow electronic filing and notifications.',
            },
        },
    },

    'incident_overview': {
        'title': 'Incident Overview',
        'overview': '''
            <strong>What is this?</strong> A high-level summary of when, where, and what happened.
            Think of this as the "who, what, when, where" of your case.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> This establishes the basic facts and helps determine which
            court has jurisdiction (authority) to hear your case. The location determines which federal
            district court you'll file in.
        ''',
        'tips': [
            'Be as specific as possible about dates and times',
            'Include the exact address or location if known',
            'The jurisdiction is typically the city/county where the incident occurred',
        ],
        'fields': {
            'incident_date': {
                'tooltip': 'The date the violation occurred',
                'help': 'If the violation occurred over multiple days, enter the first date. You can explain the duration in the narrative.',
            },
            'incident_time': {
                'tooltip': 'Approximate time of day',
                'help': 'Your best estimate is fine. This can help identify witnesses and corroborate your account.',
            },
            'location': {
                'tooltip': 'Physical address or description of where it happened',
                'help': 'Be specific: street address, building name, or detailed description (e.g., "Corner of Main St and 5th Ave, in front of City Hall").',
            },
            'jurisdiction': {
                'tooltip': 'City, county, and state where the incident occurred',
                'help': 'Example: "Los Angeles, Los Angeles County, California". This determines which federal court has jurisdiction.',
            },
            'brief_description': {
                'tooltip': 'One-paragraph summary of what happened',
                'help': 'Summarize the incident in 2-4 sentences. You\'ll provide full details in the Incident Narrative section.',
            },
        },
    },

    'defendants': {
        'title': 'Defendants',
        'overview': '''
            <strong>What is this?</strong> Defendants are the people or agencies you're suing - those
            who violated your constitutional rights. In Section 1983 cases, defendants are typically
            government officials (like police officers) or government agencies.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> You can only recover damages from properly named defendants.
            Section 1983 requires that defendants acted "under color of state law" - meaning they used
            their government authority. Individual officers can be sued personally, and sometimes their
            employing agency can be sued too.
        ''',
        'tips': [
            'Include both individual officers AND their department/agency when possible',
            'Get badge numbers and names from police reports or body camera footage',
            'If you don\'t know an officer\'s name, you can sue "John Doe" officers and identify them later through discovery',
            'Government agencies can only be sued if they have an unconstitutional "policy or custom"',
        ],
        'example': '''
            <strong>Example:</strong><br>
            <em>Individual:</em> Officer John Smith, Badge #1234, Anytown Police Department<br>
            <em>Agency:</em> City of Anytown Police Department
        ''',
        'fields': {
            'name': {
                'tooltip': 'Full name of the officer or agency',
                'help': 'For officers: include rank if known (e.g., "Officer John Smith" or "Sergeant Jane Doe"). For agencies: official name (e.g., "City of Los Angeles Police Department").',
            },
            'defendant_type': {
                'tooltip': 'Is this a person or a government agency?',
                'help': 'Individual: a specific person (officer, official). Agency: a government department or entity.',
            },
            'badge_number': {
                'tooltip': 'Officer\'s badge or ID number',
                'help': 'Found on police reports, citations, or visible on the officer\'s uniform. Helps identify the specific officer.',
            },
            'title_position': {
                'tooltip': 'Their job title or rank',
                'help': 'Examples: "Police Officer", "Sergeant", "Chief of Police", "City Manager".',
            },
            'department_agency': {
                'tooltip': 'Which department or agency they work for',
                'help': 'The government entity that employs them. Example: "Anytown Police Department" or "County Sheriff\'s Office".',
            },
            'actions_taken': {
                'tooltip': 'What this specific defendant did to violate your rights',
                'help': 'Be specific about THIS defendant\'s actions. Example: "Arrested me without probable cause", "Seized my camera and deleted footage", "Used excessive force by...".',
            },
        },
    },

    'incident_narrative': {
        'title': 'Incident Narrative',
        'overview': '''
            <strong>What is this?</strong> Your detailed, chronological account of exactly what happened.
            This is the heart of your complaint - tell your story from beginning to end.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> The narrative must show that government officials violated
            your constitutional rights. A clear, detailed account helps the judge and jury understand
            what happened and why it was wrong.
        ''',
        'tips': [
            'Write in chronological order (first this happened, then that happened)',
            'Include specific quotes if you remember what was said',
            'Describe what you were doing BEFORE the incident - this establishes you were acting lawfully',
            'Note any witnesses who saw what happened',
            'Be factual and avoid emotional language - let the facts speak for themselves',
        ],
        'example': '''
            <strong>Example opening:</strong><br>
            "On March 15, 2024, at approximately 2:30 PM, I was standing on the public sidewalk
            in front of City Hall, recording a video of the building with my smartphone. I was
            approximately 20 feet from the entrance and was not blocking pedestrian traffic..."
        ''',
        'fields': {
            'narrative': {
                'tooltip': 'Complete chronological account of what happened',
                'help': 'Start from before the incident and go through to the end. Include what you saw, heard, and experienced. Be specific about times, locations, and who did what.',
            },
            'what_you_were_doing': {
                'tooltip': 'Your lawful activity before/during the incident',
                'help': 'This establishes you were exercising your rights lawfully. Example: "I was filming from a public sidewalk as part of my First Amendment audit."',
            },
            'officer_statements': {
                'tooltip': 'What the officers said to you',
                'help': 'Include direct quotes if you remember them. Example: \'Officer Smith said, "You can\'t film here" and "Give me your camera or you\'re going to jail."\'',
            },
            'your_statements': {
                'tooltip': 'What you said to the officers',
                'help': 'Include your responses. Example: \'I said, "I\'m on a public sidewalk and have a First Amendment right to film."\'',
            },
        },
    },

    'rights_violated': {
        'title': 'Constitutional Rights Violated',
        'overview': '''
            <strong>What is this?</strong> Section 1983 allows you to sue when government officials
            violate your constitutional rights. This section identifies WHICH rights were violated.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> You must specify which constitutional amendments were
            violated. Each amendment protects different rights, and you need to match the violation
            to the correct amendment.
        ''',
        'tips': [
            'You can claim multiple amendments were violated',
            'The explanation should connect your facts to the legal standard',
            'For First Amendment auditors, the most common claims are First and Fourth Amendment violations',
        ],
        'amendments': {
            'first': {
                'name': 'First Amendment',
                'protects': 'Freedom of speech, press, assembly, and petition',
                'common_violations': [
                    'Stopping you from filming in public',
                    'Arresting you for what you said',
                    'Retaliating against you for exercising free speech',
                    'Preventing peaceful protest or assembly',
                ],
            },
            'fourth': {
                'name': 'Fourth Amendment',
                'protects': 'Freedom from unreasonable searches and seizures',
                'common_violations': [
                    'Arrest without probable cause',
                    'Searching you or your belongings without warrant or consent',
                    'Seizing your camera, phone, or other property',
                    'Excessive force during arrest or detention',
                    'Unlawful detention (being held without legal justification)',
                ],
            },
            'fifth': {
                'name': 'Fifth Amendment',
                'protects': 'Due process and protection against self-incrimination',
                'common_violations': [
                    'Denying you a fair hearing or process',
                    'Forcing you to answer questions without Miranda warnings',
                    'Taking your property without compensation',
                ],
            },
            'fourteenth': {
                'name': 'Fourteenth Amendment',
                'protects': 'Equal protection and due process (applies Bill of Rights to states)',
                'common_violations': [
                    'Treating you differently because of race, religion, or other protected class',
                    'Denying you equal treatment under the law',
                    'State officials violating your fundamental rights',
                ],
            },
        },
        'fields': {
            'first_amendment': {
                'tooltip': 'Check if your free speech, press, or assembly rights were violated',
                'help': 'Select if you were stopped from filming, speaking, protesting, or if you faced retaliation for exercising these rights.',
            },
            'fourth_amendment': {
                'tooltip': 'Check if you were unlawfully searched, seized, arrested, or force was used',
                'help': 'Select if you were arrested without probable cause, searched without a warrant, had property seized, or experienced excessive force.',
            },
            'fifth_amendment': {
                'tooltip': 'Check if your due process rights were violated',
                'help': 'Select if you were denied fair procedures, forced to incriminate yourself, or had property taken without compensation.',
            },
            'fourteenth_amendment': {
                'tooltip': 'Check if you were denied equal protection under the law',
                'help': 'Select if you were treated differently based on race, religion, or other protected characteristics, or if state officials violated your rights.',
            },
            'other_rights': {
                'tooltip': 'Any other constitutional or statutory rights violated',
                'help': 'List any other rights you believe were violated, such as state constitutional rights or other federal laws.',
            },
            'explanation': {
                'tooltip': 'Explain HOW each right was violated',
                'help': 'Connect your facts to the rights. Example: "My First Amendment rights were violated when Officer Smith ordered me to stop filming and seized my camera, despite my being on a public sidewalk engaged in protected activity."',
            },
        },
    },

    'witnesses': {
        'title': 'Witnesses',
        'overview': '''
            <strong>What is this?</strong> People who saw or heard what happened and can support
            your account of events.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> Witness testimony can corroborate your version of events.
            Independent witnesses (people who don't know you) are especially valuable because they're
            seen as unbiased.
        ''',
        'tips': [
            'Include anyone who witnessed any part of the incident',
            'Get contact information at the scene if possible',
            'Note what specifically each witness saw or heard',
            'If you don\'t have witnesses, that\'s okay - many cases proceed without them',
        ],
        'fields': {
            'name': {
                'tooltip': 'Witness\'s full name',
                'help': 'If you don\'t know their full name, provide whatever identifying information you have.',
            },
            'contact_info': {
                'tooltip': 'How to reach this witness',
                'help': 'Phone, email, or address. If you don\'t have contact info, describe how they might be identified (e.g., "employee at the coffee shop on the corner").',
            },
            'relationship': {
                'tooltip': 'How do you know this person?',
                'help': 'Examples: "stranger/bystander", "friend who was with me", "store employee", "fellow auditor". Independent witnesses carry more weight.',
            },
            'what_they_witnessed': {
                'tooltip': 'What did they see or hear?',
                'help': 'Be specific about what part of the incident they witnessed. Example: "Saw the officer grab my camera" or "Heard the officer threaten to arrest me".',
            },
        },
    },

    'evidence': {
        'title': 'Evidence',
        'overview': '''
            <strong>What is this?</strong> Physical proof that supports your claims - videos, photos,
            documents, medical records, etc.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> Evidence can prove your case. Video footage is especially
            powerful in First Amendment audit cases. Keep all evidence safe and make backup copies.
        ''',
        'tips': [
            'VIDEO is your best evidence - your footage, bystander footage, body camera footage',
            'Request body camera and dashcam footage through public records requests',
            'Keep originals safe and work with copies',
            'Document the chain of custody (who has had possession of the evidence)',
            'Medical records if you were injured',
            'Police reports and citations',
        ],
        'fields': {
            'evidence_type': {
                'tooltip': 'What kind of evidence is this?',
                'help': 'Select the type that best describes this piece of evidence.',
            },
            'description': {
                'tooltip': 'Describe what this evidence shows',
                'help': 'Be specific. Example: "Cell phone video showing Officer Smith grabbing my camera while I stood on the public sidewalk" rather than just "video of incident".',
            },
            'location_of_evidence': {
                'tooltip': 'Where is this evidence stored?',
                'help': 'Examples: "On my phone and backed up to cloud storage", "Copy requested from police department", "In my possession at home".',
            },
            'date_obtained': {
                'tooltip': 'When did you get or create this evidence?',
                'help': 'The date you recorded the video, received the document, etc.',
            },
        },
    },

    'damages': {
        'title': 'Damages',
        'overview': '''
            <strong>What is this?</strong> The harms you suffered as a result of the rights violation.
            Damages can be physical, emotional, or financial.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> You can only recover compensation for harms you can prove.
            Documenting your damages thoroughly helps maximize your recovery. Even without physical
            injury, you can recover for emotional distress and the violation of your rights itself.
        ''',
        'tips': [
            'Keep all receipts and documentation of expenses',
            'See a doctor if you were physically injured - medical records are evidence',
            'Document emotional effects: anxiety, fear, sleep problems, etc.',
            'Lost wages if you missed work',
            'Property damage or loss (camera, phone, etc.)',
        ],
        'fields': {
            'physical_injuries': {
                'tooltip': 'Any bodily harm you suffered',
                'help': 'Describe injuries in detail: bruises, cuts, broken bones, pain. Include ongoing effects. Example: "Bruising on both wrists from handcuffs, shoulder pain from being thrown to ground".',
            },
            'emotional_distress': {
                'tooltip': 'Psychological and emotional harm',
                'help': 'Anxiety, fear, humiliation, sleep problems, PTSD symptoms. These are real damages. Example: "Ongoing anxiety about filming in public, difficulty sleeping, fear of police".',
            },
            'medical_treatment': {
                'tooltip': 'Medical care you received or need',
                'help': 'Doctor visits, hospital, therapy, medications. Include dates and costs if known.',
            },
            'financial_losses': {
                'tooltip': 'Money you lost or had to spend',
                'help': 'Lost wages, legal fees, medical bills, travel costs. Be specific with amounts when possible.',
            },
            'property_damage': {
                'tooltip': 'Damage to or loss of your belongings',
                'help': 'Camera, phone, equipment that was damaged, seized, or destroyed. Include value/replacement cost.',
            },
            'other_damages': {
                'tooltip': 'Any other harms not listed above',
                'help': 'Damage to reputation, loss of opportunities, impact on relationships, etc.',
            },
        },
    },

    'prior_complaints': {
        'title': 'Prior Complaints',
        'overview': '''
            <strong>What is this?</strong> Any complaints you've already filed about this incident
            with internal affairs, civilian review boards, or other agencies.
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> Prior complaints can show you tried to resolve the issue
            through official channels. They also create a paper trail. However, you do NOT need to
            exhaust administrative remedies before filing a Section 1983 lawsuit.
        ''',
        'tips': [
            'Filing an internal affairs complaint is optional but can be helpful',
            'Keep copies of all complaints you file',
            'Document any responses or lack of response',
            'The agency\'s failure to act can support claims against them',
        ],
        'fields': {
            'filed_complaint': {
                'tooltip': 'Did you file any official complaints?',
                'help': 'Check if you filed complaints with internal affairs, civilian oversight, city council, or any other official body.',
            },
            'complaint_details': {
                'tooltip': 'Details about complaints you filed',
                'help': 'When filed, with whom, complaint number if assigned. Example: "Filed internal affairs complaint #2024-123 with Anytown PD on March 20, 2024".',
            },
            'agency_response': {
                'tooltip': 'How did the agency respond?',
                'help': 'What happened with your complaint? Still pending, dismissed, sustained? Any findings or actions taken?',
            },
        },
    },

    'relief_sought': {
        'title': 'What Do You Want From This Lawsuit?',
        'overview': '''
            <strong>What is this?</strong> This is where you tell the court what you want if you win.
            Don't worry about the legal terms - we've written everything in plain English!
        ''',
        'why_important': '''
            <strong>Why it matters:</strong> You can only get what you ask for. Ask for everything
            that applies to your situation. You can always settle for less, but you can't get more
            than what you requested.
        ''',
        'recommended_note': '''
            <div class="alert alert-success mb-3">
                <strong><i class="bi bi-lightbulb me-2"></i>Pro Tip:</strong> Click the
                <strong>"Use Recommended"</strong> button above to automatically select the most
                common requests for First Amendment audit cases. You can then customize as needed.
            </div>
        ''',
        'tips': [
            '<strong>ALWAYS</strong> ask for legal fees - if you win, the other side pays your lawyer',
            'You do NOT need to know exact dollar amounts - the court can figure that out',
            'Most 1A auditors ask for: money for losses, extra money as punishment, a court declaration, and legal fees',
            'Juries (regular people) often side with citizens whose rights were violated - request a jury!',
        ],
        'simple_explanations': [
            {
                'question': 'What\'s the difference between the money options?',
                'answer': '<strong>Compensatory</strong> = pays you back for real losses (damaged camera, missed work, stress). <strong>Punitive</strong> = extra money to punish the officers for being bad. You can ask for both!'
            },
            {
                'question': 'What\'s a "declaration" from the court?',
                'answer': 'It\'s an official statement from a judge saying "Yes, this person\'s rights were violated." It creates a legal record that can help other auditors and may prevent future violations.'
            },
            {
                'question': 'Should I ask for policy changes?',
                'answer': 'Only if you want the police department to actually change how they operate (new training, new policies). This is harder to get but can create real change.'
            },
        ],
        'fields': {
            'compensatory_damages': {
                'tooltip': 'Money to cover your actual losses - equipment, wages, emotional harm',
                'help': 'This pays you back for things you lost or suffered: damaged equipment, missed work, anxiety, humiliation, etc.',
            },
            'punitive_damages': {
                'tooltip': 'Extra money to punish the officers - common in 1A audit cases',
                'help': 'When officers clearly knew they were wrong (like telling you filming is illegal when it\'s not), courts often award extra money as punishment.',
            },
            'injunctive_relief': {
                'tooltip': 'Force the department to change their policies or training',
                'help': 'This is optional. Select this if you want the court to ORDER the police department to make changes.',
            },
            'declaratory_relief': {
                'tooltip': 'Get an official court statement that your rights were violated',
                'help': 'Highly recommended! Creates an official record and helps establish legal precedent for future cases.',
            },
            'attorney_fees': {
                'tooltip': 'Make them pay your lawyer if you win - Section 1983 allows this!',
                'help': 'ALWAYS select this! The law specifically allows you to recover legal fees in civil rights cases.',
            },
            'jury_trial_demanded': {
                'tooltip': 'Let regular citizens (not just a judge) decide your case',
                'help': 'Juries are often sympathetic to regular people whose rights were violated by police. Most plaintiffs prefer a jury.',
            },
        },
    },
}


def get_section_help(section_type):
    """Get help content for a specific section."""
    return SECTION_HELP.get(section_type, {})


def get_field_tooltip(section_type, field_name):
    """Get tooltip text for a specific field."""
    section = SECTION_HELP.get(section_type, {})
    fields = section.get('fields', {})
    field = fields.get(field_name, {})
    return field.get('tooltip', '')


def get_field_help(section_type, field_name):
    """Get extended help text for a specific field."""
    section = SECTION_HELP.get(section_type, {})
    fields = section.get('fields', {})
    field = fields.get(field_name, {})
    return field.get('help', '')
