from .base_state_lookup import BaseStateLookup

class NevadaLookup(BaseStateLookup):
    STATE_CODE = 'NV'
    STATE_NAME = 'Nevada'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Nevada',
            'cities': ['las vegas', 'henderson', 'reno', 'north las vegas', 'sparks', 'carson city', 'fernley', 'elko']
        }
    }
    