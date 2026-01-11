class CourtLookupService:
    """Main coordinator for federal district court lookups across all states."""
    
    @classmethod
    def lookup_court_by_location(cls, city, state, county=None):
        """Look up federal district court by location."""
        if not city or not state:
            return None
        
        state = state.strip().upper()
        
        # Multi-district states
        if state == 'NY':
            try:
                from .court_data.states.new_york_lookup import NewYorkLookup
                return NewYorkLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'PA':
            try:
                from .court_data.states.pennsylvania_lookup import PennsylvaniaLookup
                return PennsylvaniaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'CA':
            try:
                from .court_data.states.california_lookup import CaliforniaLookup
                return CaliforniaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'TX':
            try:
                from .court_data.states.texas_lookup import TexasLookup
                return TexasLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'FL':
            try:
                from .court_data.states.florida_lookup import FloridaLookup
                return FloridaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'IL':
            try:
                from .court_data.states.illinois_lookup import IllinoisLookup
                return IllinoisLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'OH':
            try:
                from .court_data.states.ohio_lookup import OhioLookup
                return OhioLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'GA':
            try:
                from .court_data.states.georgia_lookup import GeorgiaLookup
                return GeorgiaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'MI':
            try:
                from .court_data.states.michigan_lookup import MichiganLookup
                return MichiganLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        # Single-district states
        elif state == 'AK':
            try:
                from .court_data.states.alaska_lookup import AlaskaLookup
                return AlaskaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'DE':
            try:
                from .court_data.states.delaware_lookup import DelawareLookup
                return DelawareLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'HI':
            try:
                from .court_data.states.hawaii_lookup import HawaiiLookup
                return HawaiiLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'ID':
            try:
                from .court_data.states.idaho_lookup import IdahoLookup
                return IdahoLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'ME':
            try:
                from .court_data.states.maine_lookup import MaineLookup
                return MaineLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        elif state == 'MT':
            try:
                from .court_data.states.montana_lookup import MontanaLookup
                return MontanaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'NV':
            try:
                from .court_data.states.nevada_lookup import NevadaLookup
                return NevadaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'NH':
            try:
                from .court_data.states.new_hampshire_lookup import NewHampshireLookup
                return NewHampshireLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'RI':
            try:
                from .court_data.states.rhode_island_lookup import RhodeIslandLookup
                return RhodeIslandLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'SD':
            try:
                from .court_data.states.south_dakota_lookup import SouthDakotaLookup
                return SouthDakotaLookup.lookup_court_by_city(city)
            except ImportError:
                pass

        elif state == 'UT':
            try:
                from .court_data.states.utah_lookup import UtahLookup
                return UtahLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'VT':
            try:
                from .court_data.states.vermont_lookup import VermontLookup
                return VermontLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'WY':
            try:
                from .court_data.states.wyoming_lookup import WyomingLookup
                return WyomingLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'DC':
            try:
                from .court_data.states.district_of_columbia_lookup import DistrictOfColumbiaLookup
                return DistrictOfColumbiaLookup.lookup_court_by_city(city)
            except ImportError:
                pass

        elif state == 'VA':
            try:
                from .court_data.states.virginia_lookup import VirginiaLookup
                return VirginiaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'NC':
            try:
                from .court_data.states.north_carolina_lookup import NorthCarolinaLookup
                return NorthCarolinaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'TN':
            try:
                from .court_data.states.tennessee_lookup import TennesseeLookup
                return TennesseeLookup.lookup_court_by_city(city)
            except ImportError:
                pass

        elif state == 'WI':
            try:
                from .court_data.states.wisconsin_lookup import WisconsinLookup
                return WisconsinLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'IN':
            try:
                from .court_data.states.indiana_lookup import IndianaLookup
                return IndianaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'MO':
            try:
                from .court_data.states.missouri_lookup import MissouriLookup
                return MissouriLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'AL':
            try:
                from .court_data.states.alabama_lookup import AlabamaLookup
                return AlabamaLookup.lookup_court_by_city(city)
            except ImportError:
                pass

        elif state == 'SC':
            try:
                from .court_data.states.south_carolina_lookup import SouthCarolinaLookup
                return SouthCarolinaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'KY':
            try:
                from .court_data.states.kentucky_lookup import KentuckyLookup
                return KentuckyLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'LA':
            try:
                from .court_data.states.louisiana_lookup import LouisianaLookup
                return LouisianaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'MS':
            try:
                from .court_data.states.mississippi_lookup import MississippiLookup
                return MississippiLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'AR':
            try:
                from .court_data.states.arkansas_lookup import ArkansasLookup
                return ArkansasLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'IA':
            try:
                from .court_data.states.iowa_lookup import IowaLookup
                return IowaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'KS':
            try:
                from .court_data.states.kansas_lookup import KansasLookup
                return KansasLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'NE':
            try:
                from .court_data.states.nebraska_lookup import NebraskaLookup
                return NebraskaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'OK':
            try:
                from .court_data.states.oklahoma_lookup import OklahomaLookup
                return OklahomaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'WV':
            try:
                from .court_data.states.west_virginia_lookup import WestVirginiaLookup
                return WestVirginiaLookup.lookup_court_by_city(city)
            except ImportError:
                pass

        elif state == 'MA':
            try:
                from .court_data.states.massachusetts_lookup import MassachusettsLookup
                return MassachusettsLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'CT':
            try:
                from .court_data.states.connecticut_lookup import ConnecticutLookup
                return ConnecticutLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'NJ':
            try:
                from .court_data.states.new_jersey_lookup import NewJerseyLookup
                return NewJerseyLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'MD':
            try:
                from .court_data.states.maryland_lookup import MarylandLookup
                return MarylandLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'WA':
            try:
                from .court_data.states.washington_lookup import WashingtonLookup
                return WashingtonLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'OR':
            try:
                from .court_data.states.oregon_lookup import OregonLookup
                return OregonLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'CO':
            try:
                from .court_data.states.colorado_lookup import ColoradoLookup
                return ColoradoLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'AZ':
            try:
                from .court_data.states.arizona_lookup import ArizonaLookup
                return ArizonaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'MN':
            try:
                from .court_data.states.minnesota_lookup import MinnesotaLookup
                return MinnesotaLookup.lookup_court_by_city(city)
            except ImportError:
                pass
        
        elif state == 'ND':
            try:
                from .court_data.states.north_dakota_lookup import NorthDakotaLookup
                return NorthDakotaLookup.lookup_court_by_city(city)
            except ImportError:
                pass

            
        
        # State not supported yet
        else:
            return {
                'court_name': f'Federal District Court (State: {state})',
                'confidence': 'low',
                'method': 'unsupported_state',
                'note': f'Detailed court lookup not yet available for {state}.'
            }



