"""
Sample test stories for testing the Tell Your Story AI parsing feature.
Only available to users with is_test_user=True.

Each story contains mixed violations and realistic details that can be
extracted into multiple form sections.
"""

TEST_STORIES = [
    {
        "id": 1,
        "title": "Recording + Detention + Force (Post Office)",
        "story": """I was filming outside the post office in Austin Texas on March 15th around 2pm. Officer Martinez told me I couldn't record and grabbed my phone out of my hand. When I asked for it back, he twisted my arm behind my back and detained me in the back of his car for about 40 minutes. He never arrested me or charged me with anything, just left me sitting there. My wrist was swollen for a week. A postal worker named Linda saw the whole thing from the window."""
    },
    {
        "id": 2,
        "title": "Protest + Arrest + Search (Phoenix)",
        "story": """On July 4th I was at the peaceful protest in downtown Phoenix around 11am. I was just holding a sign on the sidewalk. Officer Thompson and Officer Davis approached and said the protest was unlawful. When I said we had a permit, Officer Thompson arrested me and searched my backpack without asking. He found nothing illegal but kept my camera saying it was evidence. I spent 14 hours in jail and they dropped the charges the next day. I missed work and lost $200 in wages. My friend Marcus was there and recorded part of it on his phone."""
    },
    {
        "id": 3,
        "title": "Traffic Stop + Search + Seizure + Profiling (Scottsdale)",
        "story": """I'm Black and I was driving home from church in Scottsdale Arizona on Sunday September 3rd around 1pm. Officer White pulled me over and said my air freshener was blocking my view which is ridiculous. He made me get out and searched my whole car without my consent. He found $1,500 cash I had just withdrawn for rent and seized it saying it might be drug money. I've never done drugs in my life. He also took my phone to look through it. I still haven't gotten my money back. There was a white family in the car next to me with the same air freshener and he didn't stop them. This was at the corner of Scottsdale Road and Camelback."""
    },
    {
        "id": 4,
        "title": "Journalist + Force + Property Damage (Portland)",
        "story": """I'm a freelance journalist and I was covering the city council meeting protest on October 10th in Portland Oregon around 7pm. I had my press credentials visible. When police declared an unlawful assembly, I identified myself as press. Officer Kelly pushed me to the ground anyway and stepped on my camera, destroying it. That camera cost $2,400. I got scrapes on my hands and knees. Several other journalists saw this happen. I have video from a bystander that caught part of it."""
    },
    {
        "id": 5,
        "title": "Recording + Retaliation + Wrongful Arrest (San Antonio)",
        "story": """On August 22nd around 3pm I was recording police making an arrest outside the Walmart in San Antonio. I was standing 30 feet away on public property. Officer Rodriguez came over and told me to stop recording. I said it was my First Amendment right. He said I was interfering and arrested me for obstruction. The charges were dropped but I spent the night in jail. I lost my job because I didn't show up the next day. The Walmart security camera should have footage of the whole thing. I was not interfering in any way, just standing there with my phone."""
    },
    {
        "id": 6,
        "title": "Home Entry + Search + Force + Property (Denver)",
        "story": """On December 5th at 6am, four officers broke down my door without a warrant looking for someone named James who doesn't live here. This was in Denver Colorado. Officer Patterson pointed his gun at me while I was in my underwear. They searched my whole apartment and broke my TV when they threw it off the stand. I told them they had the wrong address but they wouldn't listen. Sergeant Williams was in charge. My neighbor heard the commotion and saw them drag me outside in handcuffs. I was detained for 2 hours before they admitted their mistake. The door replacement cost me $800."""
    },
    {
        "id": 7,
        "title": "Mental Health + Excessive Force + Medical (Seattle)",
        "story": """My brother was having a mental health crisis on November 18th so I called 911 for help around 9pm. Officers Garcia and Chen responded to our house in Seattle. Instead of helping, they immediately tackled him and tased him three times even though he wasn't violent, just confused. They handcuffed him and left him face down on the floor for 20 minutes. He begged for water and they ignored him. He has burn marks from the taser and a dislocated shoulder. They took him to jail instead of the hospital. I recorded part of it on my phone before Officer Garcia told me to stop or I'd be arrested too."""
    },
    {
        "id": 8,
        "title": "First Amendment Audit + Detention (LA DMV)",
        "story": """I was doing a First Amendment audit at the DMV in Los Angeles on January 8th around 10am. I was filming in the public lobby. A supervisor named Karen called the police. Officer Kim arrived and told me I had to leave or be arrested for trespassing even though it's a public building. When I asked for his badge number he refused to give it and grabbed my arm, leaving bruises. He detained me outside for an hour and wrote me a trespassing warning. I never entered any restricted area. Two other people waiting in line witnessed this and one gave me her name, Sarah Johnson."""
    },
    {
        "id": 9,
        "title": "Checkpoint + Prolonged Detention + K9 (Houston)",
        "story": """I was driving through a DUI checkpoint in Houston on New Year's Eve around 11:30pm. Officer Hernandez asked if I'd been drinking and I said no. He said he smelled marijuana which was a lie - I don't use drugs. He made me pull over and wait for a K-9 unit for 90 minutes. The dog didn't alert on anything but they searched my car anyway and found nothing. Meanwhile they let dozens of other cars through without any wait. I missed my family's New Year's party. I have dashcam footage of the entire stop showing I did nothing wrong."""
    },
    {
        "id": 10,
        "title": "Mass Arrest + Force + Jail Conditions (Minneapolis)",
        "story": """On June 1st I was at the BLM protest in Minneapolis around 8pm. Police surrounded our group with no warning and arrested everyone, about 50 people. I was thrown into a police van by Officer Anderson who slammed my head against the door. We were held in a warehouse for 16 hours with no food, water, or bathrooms. I wet myself because they wouldn't let me use the restroom. Several of us were zip-tied so tight we lost feeling in our hands. All charges were dropped. I have anxiety and nightmares now. My coworker James was arrested with me and can verify everything."""
    },
    {
        "id": 11,
        "title": "Recording City Hall + Phone Seizure (OKC)",
        "story": """I was at city hall in Oklahoma City on April 3rd around 2pm to get a permit. While waiting, I started recording the lobby with my phone. Security guard Bob told me to stop but I explained filming in public areas of government buildings is legal. He called Officer Stevens who seized my phone without a warrant. He said he was deleting the footage for security reasons. When I got my phone back 3 hours later, all my videos were gone including personal family photos. I lost irreplaceable memories of my grandmother who passed away. A woman named Patricia who was also getting a permit saw the whole interaction."""
    },
    {
        "id": 12,
        "title": "Miranda Violation + Coerced Statement (Chicago)",
        "story": """I was brought in for questioning about a robbery on February 14th at the Chicago police station. Detective Moore questioned me for 5 hours without reading me my Miranda rights or letting me call a lawyer. He kept saying if I was innocent I didn't need one. He threatened to arrest my girlfriend if I didn't cooperate. I was exhausted and scared so I signed a statement that wasn't even accurate. The next week they realized it wasn't me from security footage. But that false statement is still in my record. I lost sleep for months and had to see a therapist."""
    },
    {
        "id": 13,
        "title": "School Board + Removal + Arrest (Tampa)",
        "story": """At the school board meeting in Tampa on March 8th I was speaking during public comment time about the mask policy around 7:30pm. I had signed up and was given 3 minutes. After about 90 seconds, board member Wilson said I was being disruptive and had Officer Drake remove me. I wasn't being disruptive, she just didn't like what I was saying about her voting record. I was arrested for disorderly conduct. My wife Jennifer recorded the whole speech on her phone - you can see I was calm the entire time. The charges were eventually dropped but I was banned from future meetings for a year."""
    },
    {
        "id": 14,
        "title": "Selective Enforcement + False Citation (San Jose)",
        "story": """I'm Hispanic and I was having a BBQ in my backyard in San Jose on July 4th around 9pm. My neighbors were also having parties and setting off fireworks. Officer Bradley came only to my house and gave me a $500 citation for noise violation and illegal fireworks even though I wasn't setting off any fireworks. The white family two doors down was literally launching fireworks in the street and he walked right past them. I have video from my Ring doorbell showing Officer Bradley ignoring their fireworks and coming straight to my house. My neighbor Mike will testify he saw the same thing."""
    },
    {
        "id": 15,
        "title": "Contempt of Cop + Force + False Charges (Denver)",
        "story": """On September 15th around 5pm I asked Officer Palmer for his badge number after he yelled at a homeless man in downtown Denver. He got in my face and said I needed to mind my own business. When I stood my ground, he shoved me against a wall and arrested me for assault on an officer which is completely false. He hit my head against the bricks and I needed 4 stitches. A street vendor named Miguel saw everything and said he would testify for me. The charges were reduced to disorderly conduct which I pled to just to get out of jail. I still have the scar on my forehead."""
    },
    {
        "id": 16,
        "title": "Property Seizure Without Due Process (Austin)",
        "story": """The city of Austin condemned my food truck on May 20th without any hearing or notice. Health inspector Thomas showed up with two police officers around 11am and just took my truck. I had just passed my health inspection two weeks before. They said my permit was revoked but wouldn't say why or give me any paperwork. I lost $15,000 in equipment and my entire income. When I went to city hall to fight it, they said I had to hire a lawyer. It's been 6 months and I still don't have my truck or any explanation. My employees Jorge and Maria lost their jobs too."""
    },
    {
        "id": 17,
        "title": "Recording Arrest + Retaliation + Phone Destroyed (LA)",
        "story": """I was walking home on October 31st around 8pm in Los Angeles when I saw police arresting someone on the street. I stopped about 20 feet away and started recording with my phone. Officer Kim ran over, grabbed my phone, and threw it on the ground, cracking the screen. She said I was interfering even though I wasn't even talking to anyone. When I said I wanted her badge number, she arrested me for failure to disperse even though no dispersal order was given. The guy getting arrested, who I don't know, was yelling that he saw everything. My phone was damaged beyond repair - that was an $1,100 iPhone."""
    },
    {
        "id": 18,
        "title": "Unlawful Welfare Check + Entry + Handcuffing (Phoenix)",
        "story": """On August 8th around 3am, Officer Johnson and Officer Lee broke into my apartment in Phoenix for a welfare check that nobody requested. I was asleep and woke up to flashlights in my face and guns drawn. They handcuffed me and searched my entire apartment without consent. They wouldn't tell me who called or why. After an hour they just left without explanation or apology. My door frame was destroyed and I couldn't sleep for weeks without having panic attacks. My girlfriend Ashley was there and was also handcuffed despite being in her pajamas and clearly terrified."""
    },
    {
        "id": 19,
        "title": "Protest + Pepper Spray + Medical Emergency (DC)",
        "story": """I was at the women's march on January 21st in Washington DC around noon. I was standing peacefully with my 65-year-old mother when Officer Barnes pepper sprayed our entire group with no warning. My mother has asthma and collapsed. Instead of calling medical help, Officer Barnes told us to move. A stranger helped me drag my mother to safety. She spent 2 days in the hospital. We both have ongoing eye problems. A photographer named David took pictures of the incident that ended up in the news. We were never given any order to disperse before being sprayed."""
    },
    {
        "id": 20,
        "title": "Park Photography + Detention + Photo Deletion (San Diego)",
        "story": """I was taking photos in Balboa Park San Diego on June 12th around 4pm for my photography hobby. Park ranger Collins said I needed a permit to take photos. I said I was just a hobbyist not a commercial photographer. He called Officer Reynolds who demanded my ID. I asked if I was being detained and he said I was for suspicious activity. He held me for 45 minutes while running my name, then let me go with no citation or explanation of what was suspicious. He deleted photos from my camera saying they might be surveillance for a crime. I lost beautiful sunset photos I can never recreate. Another photographer named Tom witnessed the whole thing and was shocked."""
    },
]


def get_test_stories():
    """Return list of test stories for dropdown selection."""
    return TEST_STORIES


def get_story_by_id(story_id):
    """Get a specific story by ID."""
    for story in TEST_STORIES:
        if story['id'] == story_id:
            return story
    return None
