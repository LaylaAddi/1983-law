from .base_state_lookup import BaseStateLookup

class DelawareLookup(BaseStateLookup):
    STATE_CODE = 'DE'
    STATE_NAME = 'Delaware'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Delaware',
            'cities': ['wilmington', 'dover', 'newark', 'middletown', 'smyrna', 'milford', 'seaford', 'georgetown']
        }
    }