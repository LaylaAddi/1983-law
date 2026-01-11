class BaseStateLookup:
    """Base class for state-specific federal district court lookups."""
    
    STATE_CODE = None
    STATE_NAME = None
    DISTRICTS = {}
    
    @classmethod
    def lookup_court_by_city(cls, city):
        """Look up federal district court by city name."""
        if not city or not cls.DISTRICTS:
            return None
            
        city = city.strip().lower()
        
        # Check each district for exact city match
        for district_key, district_info in cls.DISTRICTS.items():
            if city in district_info.get('cities', []):
                return {
                    'court_name': district_info['name'],
                    'confidence': 'high',
                    'method': 'city_match',
                    'district': district_key,
                    'state': cls.STATE_CODE
                }
        
        return None