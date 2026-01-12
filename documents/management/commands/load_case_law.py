"""
Management command to load verified Section 1983 case law into the database.
These are real, accurate citations that have been verified.
"""
from django.core.management.base import BaseCommand
from documents.models import CaseLaw


LANDMARK_CASES = [
    # ============================================================
    # SECTION 1983 FOUNDATIONAL CASES
    # ============================================================
    {
        'case_name': 'Monroe v. Pape',
        'citation': '365 U.S. 167 (1961)',
        'year': 1961,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'section_1983_general',
        'key_holding': 'Section 1983 provides a federal remedy for constitutional violations by state actors, even when state remedies exist. Officers acting "under color of law" can be sued even if their actions violate state law.',
        'facts_summary': 'Chicago police officers broke into the Monroe family home without a warrant, ransacked the house, and detained Mr. Monroe without arraignment.',
        'relevance_keywords': 'under color of law, state actor, federal remedy, police misconduct, section 1983 liability',
        'citation_text': 'Section 1983 creates a federal cause of action against anyone who, "under color of" state law, deprives another of constitutional rights. Monroe v. Pape, 365 U.S. 167 (1961).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTH AMENDMENT - EXCESSIVE FORCE
    # ============================================================
    {
        'case_name': 'Graham v. Connor',
        'citation': '490 U.S. 386 (1989)',
        'year': 1989,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'excessive_force',
        'key_holding': 'Claims of excessive force in the context of an arrest or investigatory stop must be analyzed under the Fourth Amendment\'s "objective reasonableness" standard, not substantive due process.',
        'facts_summary': 'Diabetic man experiencing insulin reaction was stopped by police, thrown against car, handcuffed, and injured despite friends explaining his medical condition.',
        'relevance_keywords': 'excessive force, objective reasonableness, arrest, seizure, police force, physical force, injury',
        'citation_text': 'The Fourth Amendment\'s "objective reasonableness" standard governs claims of excessive force during arrest. Graham v. Connor, 490 U.S. 386 (1989). Courts must consider the severity of the crime, whether the suspect posed an immediate threat, and whether the suspect was actively resisting.',
        'is_landmark': True,
    },
    {
        'case_name': 'Tennessee v. Garner',
        'citation': '471 U.S. 1 (1985)',
        'year': 1985,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'excessive_force',
        'key_holding': 'Deadly force may not be used to prevent escape of a fleeing felon unless the officer has probable cause to believe the suspect poses a significant threat of death or serious physical injury.',
        'facts_summary': 'Police officer shot and killed an unarmed teenager who was fleeing after a burglary.',
        'relevance_keywords': 'deadly force, fleeing suspect, shooting, lethal force, escape, unarmed',
        'citation_text': 'Use of deadly force to prevent escape is unreasonable unless the officer has probable cause to believe the suspect poses a threat of serious physical harm. Tennessee v. Garner, 471 U.S. 1 (1985).',
        'is_landmark': True,
    },
    {
        'case_name': 'Scott v. Harris',
        'citation': '550 U.S. 372 (2007)',
        'year': 2007,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'excessive_force',
        'key_holding': 'An officer\'s attempt to terminate a dangerous high-speed car chase that threatens the lives of innocent bystanders does not violate the Fourth Amendment, even if it places the fleeing motorist at risk of serious injury or death.',
        'facts_summary': 'Police ended high-speed chase by ramming suspect\'s car, rendering him a quadriplegic.',
        'relevance_keywords': 'vehicle pursuit, car chase, ramming, high speed, public safety, deadly force',
        'citation_text': 'Officers may use force to terminate a high-speed pursuit that poses danger to the public, balancing the nature and quality of the intrusion against the governmental interests at stake. Scott v. Harris, 550 U.S. 372 (2007).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTH AMENDMENT - FALSE ARREST / UNLAWFUL DETENTION
    # ============================================================
    {
        'case_name': 'Dunaway v. New York',
        'citation': '442 U.S. 200 (1979)',
        'year': 1979,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'false_arrest',
        'key_holding': 'Police must have probable cause to seize a person and transport them to the police station for interrogation. Detention for custodial questioning, even without formal arrest, requires probable cause.',
        'facts_summary': 'Police took suspect to station for questioning about a murder without probable cause, obtaining incriminating statements.',
        'relevance_keywords': 'probable cause, detention, custodial interrogation, seizure, police station, questioning',
        'citation_text': 'Detention for custodial questioning, regardless of its label, constitutes a seizure requiring probable cause. Dunaway v. New York, 442 U.S. 200 (1979).',
        'is_landmark': True,
    },
    {
        'case_name': 'Terry v. Ohio',
        'citation': '392 U.S. 1 (1968)',
        'year': 1968,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unlawful_detention',
        'key_holding': 'Police may briefly detain a person for investigation if they have reasonable suspicion of criminal activity. A limited pat-down search for weapons is permitted if the officer reasonably believes the person is armed and dangerous.',
        'facts_summary': 'Officer observed men who appeared to be casing a store for robbery, stopped and frisked them, finding weapons.',
        'relevance_keywords': 'reasonable suspicion, stop and frisk, terry stop, investigative detention, pat down, brief detention',
        'citation_text': 'An investigative stop requires reasonable suspicion that criminal activity is afoot. Terry v. Ohio, 392 U.S. 1 (1968). The detention must be temporary and limited in scope.',
        'is_landmark': True,
    },
    {
        'case_name': 'Florida v. Bostick',
        'citation': '501 U.S. 429 (1991)',
        'year': 1991,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unlawful_detention',
        'key_holding': 'A seizure occurs when a reasonable person would not feel free to decline the officer\'s requests or otherwise terminate the encounter.',
        'facts_summary': 'Police boarded a bus and asked to search passenger\'s luggage without informing him he could refuse.',
        'relevance_keywords': 'free to leave, consensual encounter, bus, seizure, reasonable person, terminate encounter',
        'citation_text': 'A person is seized within the meaning of the Fourth Amendment only when, by means of physical force or show of authority, their freedom of movement is restrained. Florida v. Bostick, 501 U.S. 429 (1991).',
        'is_landmark': True,
    },
    {
        'case_name': 'Rodriguez v. United States',
        'citation': '575 U.S. 348 (2015)',
        'year': 2015,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unlawful_detention',
        'key_holding': 'A traffic stop becomes unlawful if it is prolonged beyond the time reasonably required to complete the mission of issuing a ticket.',
        'facts_summary': 'After completing a traffic stop, officer detained driver for additional 7-8 minutes waiting for a drug-sniffing dog.',
        'relevance_keywords': 'traffic stop, prolonged detention, extended stop, dog sniff, delay, mission of stop',
        'citation_text': 'Authority for a traffic stop ends when tasks tied to the traffic infraction are completed. Extending the stop beyond that point without reasonable suspicion violates the Fourth Amendment. Rodriguez v. United States, 575 U.S. 348 (2015).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTH AMENDMENT - UNREASONABLE SEARCH
    # ============================================================
    {
        'case_name': 'Mapp v. Ohio',
        'citation': '367 U.S. 643 (1961)',
        'year': 1961,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unreasonable_search',
        'key_holding': 'Evidence obtained through searches that violate the Fourth Amendment is inadmissible in state court (exclusionary rule applies to states).',
        'facts_summary': 'Police forcibly entered home without a warrant, searched extensively, and found obscene materials.',
        'relevance_keywords': 'warrantless search, exclusionary rule, home search, without warrant, evidence',
        'citation_text': 'The Fourth Amendment\'s protection against unreasonable searches applies to the states, and evidence obtained in violation must be excluded. Mapp v. Ohio, 367 U.S. 643 (1961).',
        'is_landmark': True,
    },
    {
        'case_name': 'Payton v. New York',
        'citation': '445 U.S. 573 (1980)',
        'year': 1980,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unreasonable_search',
        'key_holding': 'Absent exigent circumstances, police may not enter a home to make a warrantless arrest.',
        'facts_summary': 'Police entered suspect\'s home without a warrant to make a routine felony arrest.',
        'relevance_keywords': 'home entry, warrantless arrest, exigent circumstances, doorway, residence, warrant requirement',
        'citation_text': 'The Fourth Amendment prohibits warrantless entry into a person\'s home to make an arrest, absent exigent circumstances. Payton v. New York, 445 U.S. 573 (1980).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTH AMENDMENT - UNREASONABLE SEIZURE (PROPERTY)
    # ============================================================
    {
        'case_name': 'Soldal v. Cook County',
        'citation': '506 U.S. 56 (1992)',
        'year': 1992,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourth',
        'right_category': 'unreasonable_seizure',
        'key_holding': 'The Fourth Amendment protects against unreasonable seizures of property, not just persons. Seizure of property occurs when there is meaningful interference with an individual\'s possessory interests.',
        'facts_summary': 'Deputies assisted in removing plaintiff\'s mobile home from lot without proper eviction proceedings.',
        'relevance_keywords': 'property seizure, possessory interest, personal property, confiscation, taking property',
        'citation_text': 'A seizure of property occurs when there is meaningful interference with an individual\'s possessory interests in that property. Soldal v. Cook County, 506 U.S. 56 (1992).',
        'is_landmark': True,
    },

    # ============================================================
    # FIRST AMENDMENT - FREEDOM OF SPEECH / RECORDING POLICE
    # ============================================================
    {
        'case_name': 'Glik v. Cunniffe',
        'citation': '655 F.3d 78 (1st Cir. 2011)',
        'year': 2011,
        'court_level': 'circuit',
        'circuit': '1st Circuit',
        'amendment': 'first',
        'right_category': 'recording',
        'key_holding': 'The First Amendment protects the right to film police officers performing their duties in public. This right is clearly established.',
        'facts_summary': 'Man arrested for recording police arresting another person in public park using his cell phone.',
        'relevance_keywords': 'recording police, filming officers, cell phone, video, public place, photography, first amendment audit',
        'citation_text': 'The First Amendment protects the right of individuals to record police officers in the discharge of their duties in a public space. Glik v. Cunniffe, 655 F.3d 78 (1st Cir. 2011). This right is clearly established.',
        'is_landmark': True,
    },
    {
        'case_name': 'Turner v. Driver',
        'citation': '848 F.3d 678 (5th Cir. 2017)',
        'year': 2017,
        'court_level': 'circuit',
        'circuit': '5th Circuit',
        'amendment': 'first',
        'right_category': 'recording',
        'key_holding': 'The First Amendment protects the right to record police activity, including from public sidewalks near police stations.',
        'facts_summary': 'Man detained and questioned for filming police station from public sidewalk.',
        'relevance_keywords': 'recording police, filming police station, sidewalk, public forum, photography, first amendment audit',
        'citation_text': 'The First Amendment right to record police extends to filming police stations and officers from public spaces. Turner v. Driver, 848 F.3d 678 (5th Cir. 2017).',
        'is_landmark': True,
    },
    {
        'case_name': 'ACLU v. Alvarez',
        'citation': '679 F.3d 583 (7th Cir. 2012)',
        'year': 2012,
        'court_level': 'circuit',
        'circuit': '7th Circuit',
        'amendment': 'first',
        'right_category': 'recording',
        'key_holding': 'Audio recording of police performing public duties is protected by the First Amendment. Eavesdropping statutes cannot be applied to criminalize recording of police in public.',
        'facts_summary': 'Challenge to Illinois eavesdropping law that criminalized audio recording of police without consent.',
        'relevance_keywords': 'audio recording, eavesdropping, wiretapping law, recording police, public duties',
        'citation_text': 'The First Amendment protects audio as well as video recording of police officers performing their duties in public. ACLU v. Alvarez, 679 F.3d 583 (7th Cir. 2012).',
        'is_landmark': True,
    },
    {
        'case_name': 'Fields v. City of Philadelphia',
        'citation': '862 F.3d 353 (3rd Cir. 2017)',
        'year': 2017,
        'court_level': 'circuit',
        'circuit': '3rd Circuit',
        'amendment': 'first',
        'right_category': 'recording',
        'key_holding': 'The First Amendment protects the act of photographing, filming, or otherwise recording police officers conducting their official duties in public.',
        'facts_summary': 'Two individuals were retaliated against for recording police - one at a house party, one at a protest.',
        'relevance_keywords': 'recording police, photography, filming, bystander recording, retaliation',
        'citation_text': 'Recording police activity in public is protected by the First Amendment as a means of gathering information about government officials performing their duties. Fields v. City of Philadelphia, 862 F.3d 353 (3rd Cir. 2017).',
        'is_landmark': True,
    },

    # ============================================================
    # FIRST AMENDMENT - FREEDOM OF SPEECH (GENERAL)
    # ============================================================
    {
        'case_name': 'City of Houston v. Hill',
        'citation': '482 U.S. 451 (1987)',
        'year': 1987,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'first',
        'right_category': 'speech',
        'key_holding': 'The First Amendment protects a significant amount of verbal criticism and challenge directed at police officers. Ordinances criminalizing speech that "interrupts" police are unconstitutionally overbroad.',
        'facts_summary': 'Man arrested for shouting at police officer to divert attention from friend being arrested.',
        'relevance_keywords': 'verbal criticism, speech to police, challenging officer, interrupting, talking back, criticism',
        'citation_text': 'The First Amendment protects verbal criticism of police officers, even when expressed in a challenging or hostile manner. City of Houston v. Hill, 482 U.S. 451 (1987).',
        'is_landmark': True,
    },
    {
        'case_name': 'Cohen v. California',
        'citation': '403 U.S. 15 (1971)',
        'year': 1971,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'first',
        'right_category': 'speech',
        'key_holding': 'Offensive or profane speech is protected by the First Amendment. The government cannot prohibit expression simply because it is offensive to some.',
        'facts_summary': 'Man convicted for wearing jacket with profane anti-draft message in courthouse.',
        'relevance_keywords': 'profanity, offensive speech, vulgar language, cursing, swearing, expletive',
        'citation_text': 'The First Amendment protects offensive and profane expression. The government may not punish speech simply because others find it offensive. Cohen v. California, 403 U.S. 15 (1971).',
        'is_landmark': True,
    },

    # ============================================================
    # FIRST AMENDMENT - RETALIATION
    # ============================================================
    {
        'case_name': 'Crawford-El v. Britton',
        'citation': '523 U.S. 574 (1998)',
        'year': 1998,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'first',
        'right_category': 'speech',
        'key_holding': 'Government officials may be held liable under Section 1983 for retaliating against individuals who exercise their First Amendment rights.',
        'facts_summary': 'Prison inmate alleged officials retaliated against him for filing grievances and lawsuits.',
        'relevance_keywords': 'retaliation, first amendment retaliation, retaliatory arrest, retaliatory prosecution, punishment for speech',
        'citation_text': 'Officials who retaliate against individuals for exercising First Amendment rights violate Section 1983. Crawford-El v. Britton, 523 U.S. 574 (1998).',
        'is_landmark': True,
    },
    {
        'case_name': 'Nieves v. Bartlett',
        'citation': '587 U.S. ___, 139 S. Ct. 1715 (2019)',
        'year': 2019,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'first',
        'right_category': 'speech',
        'key_holding': 'Probable cause generally defeats a First Amendment retaliatory arrest claim, but an exception exists where officers have probable cause for minor offenses but typically exercise discretion not to arrest.',
        'facts_summary': 'Man arrested at festival after verbally confronting officers, claimed arrest was retaliation for protected speech.',
        'relevance_keywords': 'retaliatory arrest, retaliation, probable cause, discretionary arrest, minor offense',
        'citation_text': 'A plaintiff may maintain a First Amendment retaliatory arrest claim when officers had probable cause only for a minor offense, and similarly situated individuals were not arrested. Nieves v. Bartlett, 139 S. Ct. 1715 (2019).',
        'is_landmark': True,
    },

    # ============================================================
    # FIRST AMENDMENT - ASSEMBLY
    # ============================================================
    {
        'case_name': 'Edwards v. South Carolina',
        'citation': '372 U.S. 229 (1963)',
        'year': 1963,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'first',
        'right_category': 'assembly',
        'key_holding': 'The First Amendment protects peaceful assembly and demonstration on public property. Arrests for breach of peace during peaceful protests violate constitutional rights.',
        'facts_summary': 'Civil rights demonstrators peacefully protesting at state capitol were arrested for breach of peace.',
        'relevance_keywords': 'protest, demonstration, peaceful assembly, public property, march, gathering',
        'citation_text': 'The First Amendment protects the right to peacefully assemble and petition for redress of grievances on public property. Edwards v. South Carolina, 372 U.S. 229 (1963).',
        'is_landmark': True,
    },

    # ============================================================
    # FIFTH AMENDMENT - SELF-INCRIMINATION
    # ============================================================
    {
        'case_name': 'Miranda v. Arizona',
        'citation': '384 U.S. 436 (1966)',
        'year': 1966,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fifth',
        'right_category': 'self_incrimination',
        'key_holding': 'Prior to custodial interrogation, police must warn suspects of their right to remain silent and right to counsel. Statements obtained without these warnings are inadmissible.',
        'facts_summary': 'Defendant confessed during police interrogation without being informed of his rights.',
        'relevance_keywords': 'miranda rights, right to remain silent, custodial interrogation, right to counsel, warning',
        'citation_text': 'Individuals in custodial interrogation must be informed of their right to remain silent and right to counsel before questioning. Miranda v. Arizona, 384 U.S. 436 (1966).',
        'is_landmark': True,
    },
    {
        'case_name': 'Chavez v. Martinez',
        'citation': '538 U.S. 760 (2003)',
        'year': 2003,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fifth',
        'right_category': 'self_incrimination',
        'key_holding': 'The Fifth Amendment\'s Self-Incrimination Clause is not violated until compelled statements are used against a defendant in a criminal proceeding. However, coercive interrogation may still violate substantive due process.',
        'facts_summary': 'Officer continued interrogating shooting victim while he was in severe pain in hospital, but statements were never used in criminal case.',
        'relevance_keywords': 'coercive interrogation, compelled statement, hospital interrogation, substantive due process',
        'citation_text': 'While the Self-Incrimination Clause requires use in a criminal case, coercive interrogation tactics may independently violate due process. Chavez v. Martinez, 538 U.S. 760 (2003).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTEENTH AMENDMENT - DUE PROCESS
    # ============================================================
    {
        'case_name': 'County of Sacramento v. Lewis',
        'citation': '523 U.S. 833 (1998)',
        'year': 1998,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'due_process',
        'key_holding': 'To establish a substantive due process violation, plaintiff must show the officer\'s conduct "shocks the conscience." In rapidly evolving situations, this requires intent to harm unrelated to legitimate law enforcement.',
        'facts_summary': 'Police pursuit resulted in death of motorcycle passenger when officer\'s car struck the bike.',
        'relevance_keywords': 'shocks the conscience, substantive due process, intent to harm, reckless, deliberate indifference',
        'citation_text': 'Executive action violates substantive due process only when it "shocks the conscience." In rapidly evolving situations, liability requires a purpose to cause harm. County of Sacramento v. Lewis, 523 U.S. 833 (1998).',
        'is_landmark': True,
    },
    {
        'case_name': 'Rochin v. California',
        'citation': '342 U.S. 165 (1952)',
        'year': 1952,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'due_process',
        'key_holding': 'Police conduct that "shocks the conscience" violates due process. Forcibly extracting evidence from a suspect\'s body offends fundamental principles of justice.',
        'facts_summary': 'Officers forcibly took suspect to hospital and had his stomach pumped to retrieve swallowed drugs.',
        'relevance_keywords': 'shocks the conscience, bodily integrity, forced medical procedure, stomach pumping',
        'citation_text': 'Conduct that shocks the conscience violates due process, regardless of the method used to obtain evidence. Rochin v. California, 342 U.S. 165 (1952).',
        'is_landmark': True,
    },

    # ============================================================
    # FOURTEENTH AMENDMENT - EQUAL PROTECTION
    # ============================================================
    {
        'case_name': 'Village of Willowbrook v. Olech',
        'citation': '528 U.S. 562 (2000)',
        'year': 2000,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'equal_protection',
        'key_holding': 'A "class of one" equal protection claim is viable where plaintiff alleges intentional different treatment from similarly situated individuals without rational basis.',
        'facts_summary': 'Village required plaintiff to grant larger easement than required of other property owners.',
        'relevance_keywords': 'class of one, similarly situated, unequal treatment, discrimination, selective enforcement',
        'citation_text': 'Equal protection is violated when an individual is intentionally treated differently from similarly situated persons without rational basis. Village of Willowbrook v. Olech, 528 U.S. 562 (2000).',
        'is_landmark': True,
    },
    {
        'case_name': 'Whren v. United States',
        'citation': '517 U.S. 806 (1996)',
        'year': 1996,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'equal_protection',
        'key_holding': 'The subjective intentions of police officers do not make an otherwise lawful traffic stop unconstitutional under the Fourth Amendment, but selective enforcement based on race may violate Equal Protection.',
        'facts_summary': 'Officers made traffic stop for minor violation, suspecting drug activity; defendants claimed racial profiling.',
        'relevance_keywords': 'racial profiling, pretextual stop, selective enforcement, traffic stop, discrimination',
        'citation_text': 'While pretextual stops do not violate the Fourth Amendment, selective enforcement based on race violates Equal Protection. Whren v. United States, 517 U.S. 806 (1996).',
        'is_landmark': True,
    },

    # ============================================================
    # QUALIFIED IMMUNITY
    # ============================================================
    {
        'case_name': 'Harlow v. Fitzgerald',
        'citation': '457 U.S. 800 (1982)',
        'year': 1982,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'qualified_immunity',
        'key_holding': 'Government officials performing discretionary functions are entitled to qualified immunity unless their conduct violates clearly established statutory or constitutional rights of which a reasonable person would have known.',
        'facts_summary': 'Former Air Force analyst sued White House aides for retaliatory firing.',
        'relevance_keywords': 'qualified immunity, clearly established, reasonable officer, discretionary function',
        'citation_text': 'Qualified immunity protects officials unless their conduct violated clearly established rights that a reasonable person would have known. Harlow v. Fitzgerald, 457 U.S. 800 (1982).',
        'is_landmark': True,
    },
    {
        'case_name': 'Saucier v. Katz',
        'citation': '533 U.S. 194 (2001)',
        'year': 2001,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'qualified_immunity',
        'key_holding': 'Qualified immunity analysis involves two questions: (1) whether the facts alleged show a constitutional violation, and (2) whether the right was clearly established at the time.',
        'facts_summary': 'Military police officer used force to remove protester from VP Gore event.',
        'relevance_keywords': 'qualified immunity analysis, two-prong test, clearly established right',
        'citation_text': 'Courts analyzing qualified immunity must determine (1) if a constitutional violation occurred and (2) if the right was clearly established. Saucier v. Katz, 533 U.S. 194 (2001).',
        'is_landmark': True,
    },
    {
        'case_name': 'Pearson v. Callahan',
        'citation': '555 U.S. 223 (2009)',
        'year': 2009,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'qualified_immunity',
        'key_holding': 'Courts have discretion to decide which prong of the qualified immunity analysis to address first. They need not always determine if a constitutional violation occurred before deciding if the right was clearly established.',
        'facts_summary': 'Officers entered home based on consent given by informant already inside.',
        'relevance_keywords': 'qualified immunity, clearly established, constitutional violation, discretion',
        'citation_text': 'Courts may grant qualified immunity based on the "clearly established" prong alone without deciding if a constitutional violation occurred. Pearson v. Callahan, 555 U.S. 223 (2009).',
        'is_landmark': True,
    },
    {
        'case_name': 'Hope v. Pelzer',
        'citation': '536 U.S. 730 (2002)',
        'year': 2002,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'qualified_immunity',
        'key_holding': 'A right can be "clearly established" by prior decisions even without a case directly on point, if the unlawfulness of the conduct was apparent in light of pre-existing law.',
        'facts_summary': 'Prison guards handcuffed inmate to hitching post in the sun for seven hours without water or bathroom.',
        'relevance_keywords': 'clearly established, obvious clarity, general principle, prior precedent',
        'citation_text': 'Officials can be on notice that their conduct violates established law even without a case directly on point. Hope v. Pelzer, 536 U.S. 730 (2002).',
        'is_landmark': True,
    },

    # ============================================================
    # MUNICIPAL LIABILITY (MONELL)
    # ============================================================
    {
        'case_name': 'Monell v. Department of Social Services',
        'citation': '436 U.S. 658 (1978)',
        'year': 1978,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'municipal_liability',
        'key_holding': 'Municipalities can be sued under Section 1983 when an official policy or custom causes a constitutional violation. However, municipalities cannot be held liable solely on a respondeat superior theory.',
        'facts_summary': 'Female employees challenged city policy requiring pregnant employees to take unpaid leave.',
        'relevance_keywords': 'municipal liability, official policy, custom, city, county, government entity, monell',
        'citation_text': 'Municipalities may be liable under Section 1983 when an official policy or custom causes a constitutional deprivation. Monell v. Dep\'t of Social Services, 436 U.S. 658 (1978).',
        'is_landmark': True,
    },
    {
        'case_name': 'City of Canton v. Harris',
        'citation': '489 U.S. 378 (1989)',
        'year': 1989,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'municipal_liability',
        'key_holding': 'A municipality may be liable for inadequate training of employees if the failure amounts to deliberate indifference to constitutional rights.',
        'facts_summary': 'Woman suffered injury after police failed to provide medical attention following arrest.',
        'relevance_keywords': 'failure to train, deliberate indifference, municipal policy, training, supervision',
        'citation_text': 'Inadequate police training may form the basis for municipal liability when it amounts to deliberate indifference to constitutional rights. City of Canton v. Harris, 489 U.S. 378 (1989).',
        'is_landmark': True,
    },
    {
        'case_name': 'Connick v. Thompson',
        'citation': '563 U.S. 51 (2011)',
        'year': 2011,
        'court_level': 'supreme',
        'circuit': '',
        'amendment': 'fourteenth',
        'right_category': 'municipal_liability',
        'key_holding': 'A single Brady violation by prosecutors is generally insufficient to establish municipal liability for failure to train, absent a pattern of similar violations.',
        'facts_summary': 'Prosecutor\'s office failed to disclose exculpatory evidence, leading to wrongful conviction.',
        'relevance_keywords': 'failure to train, pattern of violations, deliberate indifference, single incident',
        'citation_text': 'Municipal liability for failure to train typically requires proof of a pattern of similar violations, not just a single incident. Connick v. Thompson, 563 U.S. 51 (2011).',
        'is_landmark': True,
    },
]


class Command(BaseCommand):
    help = 'Load verified Section 1983 case law into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing case law before loading',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count = CaseLaw.objects.all().delete()[0]
            self.stdout.write(f'Deleted {deleted_count} existing case law entries')

        created_count = 0
        updated_count = 0

        for case_data in LANDMARK_CASES:
            case, created = CaseLaw.objects.update_or_create(
                case_name=case_data['case_name'],
                citation=case_data['citation'],
                defaults=case_data
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded case law: {created_count} created, {updated_count} updated'
            )
        )
        self.stdout.write(f'Total cases in database: {CaseLaw.objects.count()}')
