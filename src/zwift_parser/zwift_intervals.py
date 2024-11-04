import xml.etree.ElementTree as ET 

def parse_cadence(row: str) -> int:
    """Parses cadence value string 'Xrpm' and returns X as int"""

    keyword = 'rpm'

    if keyword not in row: return -1, row 
    if ',' in row: keyword += ','

    cadence, rest = row.split(keyword)
    if '/' in cadence: cadence = sum([int(c) for c in cadence.split('/')])/2 
    return int(cadence), rest 

def parse_power(row: str) -> int:
    """Parses power value string 'X%' or 'XW' and returns X as int"""

    power = row 
    if '%' in power: power, _ = power.split('%')
    if 'W' in power: power, _ = power.split('W')
    return float(power)/100

def parse_duration(row: str) -> int: 
    """Parses duration value string 'Xhr', 'Ymin' or 'Zsec' and returns (X::Y::Z) as seconds"""

    import re 
    def filter_digits(s): return "".join(re.findall('\d+', s))
    seconds = 0 
    if 'hr' in row: 
        hr, row = row.split('hr')
        seconds += int(filter_digits(hr)) * 3600 
    if 'min' in row: 
        min, row = row.split('min')
        seconds += int(filter_digits(min)) * 60 
    if 'sec' in row: 
        sec, _ = row.split('sec')
        seconds += int(filter_digits(sec))
    return seconds


class ZBikeSteadyState: 
    def __init__(self, row: str) -> None:
        duration, row = [r.strip() for r in row.split('@')]
        duration = parse_duration(duration)
        cadence, row = parse_cadence(row)
        self.duration = duration
        self.power = parse_power(row)
        self.cadence = cadence 

    def __repr__(self) -> str:
        return f'SteadyState (duration: {self.duration} power: {self.power} cadence: {self.cadence}'

    def to_xml(self, root: ET.Element) -> ET.Element:
        """Creates an XML element from the steady state interval data 

        Params
        root : ET.Element 
                Root of the created steady state interval XML element 
        """
        interval = ET.SubElement(root, 'SteadyState')
        interval.set('Duration', str(self.duration))
        interval.set('Power', str(self.power))
        if self.cadence > 0: interval.set('Cadence', str(self.cadence))
        return interval 

class ZBikeRangedInterval(): 
    def __init__(self, row: str) -> None:
        duration, row = row.split('from')
        cadence = -1
        if '@' in duration: 
            duration, cadence = duration.split('@')
            cadence, _ = parse_cadence(cadence)
        duration = parse_duration(duration)

        from_power, to_power = [parse_power(p) for p in row.split('to')]

        self.duration = duration 
        self.from_power = from_power 
        self.to_power = to_power 
        self.cadence = cadence 
        self.name = "Warmup" if from_power < to_power else "Cooldown"  

    def __repr__(self) -> str:
        return f'{self.name} (duration: {self.duration} from_power: {self.from_power} to_power: {self.to_power} cadence: {self.cadence})'

    def to_xml(self, root: ET.Element) -> ET.Element:
        """Creates an XML element from the ranged interval interval data 

        Params
        root : ET.Element 
                Root of the created free ranged interval XML element 
        """
        interval = ET.SubElement(root, self.name)
        interval.set('Duration', str(self.duration))
        interval.set('PowerLow', str(self.from_power))
        interval.set("PowerHigh", str(self.to_power))
        if self.cadence > 0: interval.set('Cadence', str(self.cadence))

class ZBikeIntervalsT(): 
    def __init__(self, row: str): 
        number, rest =  row.split('x')
        rest = rest.replace("rpm,", 'rpm')
        first_interval, second_interval = [ZBikeSteadyState(r) for r in rest.split(',')]
        self.number = number 
        self.first_interval = first_interval 
        self.second_interval = second_interval 

    def __repr__(self) -> str:
        return f'IntervalT ({self.number} x {self.first_interval}, {self.second_interval})'

    def to_xml(self, root: ET.Element) -> ET.Element:
        """Creates an XML element from the intervals data 

        Params
        root : ET.Element 
                Root of the created free ride intervals XML element 
        """
        interval = ET.SubElement(root, 'IntervalsT')
        interval.set('Repeat', str(self.number))
        interval.set('OnDuration', str(self.first_interval.duration))
        interval.set('OffDuration', str(self.second_interval.duration))
        interval.set("OnPower", str(self.first_interval.power))
        interval.set('OffPower', str(self.second_interval.power))
        interval.set('Cadence', str(self.first_interval.cadence))
        interval.set("CadenceResting", str(self.second_interval.cadence))

class ZFreeRide(): 
    def __init__(self, row: str): 
        duration, _ = row.split('free ride')
        cadence = -1
        if '@' in duration: 
            duration, cadence = duration.split("@")
            cadence = parse_cadence(cadence)
        duration = parse_duration(duration)

        self.duration = duration
        self.cadence = cadence
        self.flat_road = 1 

    def __repr__(self) -> str:
        return f'ZFreeRide (duration: {self.duration} cadence: {self.cadence})'

    def to_xml(self, root: ET.Element) -> ET.Element:
        """Creates an XML element from the free ride interval data 

        Params
        root : ET.Element 
                Root of the created free ride interval XML element 
        """
        interval = ET.SubElement(root, 'FreeRide')
        interval.set('Duration', str(self.duration))
        interval.set('FlatRoad', str(self.flat_road))
        if self.cadence > 0: interval.set("Cadence", str(self.cadence))
        pass 
