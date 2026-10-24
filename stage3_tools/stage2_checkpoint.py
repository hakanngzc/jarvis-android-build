import hashlib

# Stable scalar positions in the serialized NSS 4.31 player record.
#
# IMPORTANT: p_GetPlayerData's static StringStack push ordinal is NOT always
# the runtime CSV index. Between wage/goalbonus and the contract date markers
# it executes two fixed-size loops:
#   10 iterations x 3 pushes  -> 30 runtime tokens (3 visible statically)
#   100 iterations x 5 pushes -> 500 runtime tokens (5 visible statically)
# So static ordinals 59/60 for m_lastnegotiations/m_lasttransferdate acquire
# +27 +495 = +522 runtime positions, yielding fixed NSS 4.31 indexes 581/582.
FIELD_INDEX = {
    'sdate': 0,
    'clubnationid': 1,
    'clubid': 2,
    'fullname': 3,
    'shortname': 4,
    'careerapps': 13,
    'goalbonus': 33,
    'wage': 34,
    'lastnegotiations': 581,
    'lasttransferdate': 582,
}

STRING_FIELDS = {'fullname', 'shortname'}
MIN_PLAYER_TOKENS = max(FIELD_INDEX.values()) + 1


def strip_tweaks_prefix(state):
    if state.startswith('#TWEAKS'):
        marker = '#ENDTWEAKS'
        end = state.find(marker)
        if end < 0:
            raise ValueError('unterminated tweaks prefix')
        state = state[end + len(marker):].lstrip('\r\n')
    return state


def digest(v):
    return hashlib.sha256(v.encode()).hexdigest()


def player_record_without_date_digest(tokens):
    # Retirement.m_ButtonPlay deliberately decrements m_sdate before QuickSave.
    # Keep a second durable-record fingerprint with token 0 normalized so a
    # retirement runtime proof can demonstrate state changed beyond the date
    # adjustment without guessing an unverified m_retired CSV index.
    normalized = list(tokens)
    normalized[FIELD_INDEX['sdate']] = '<SDATE>'
    return digest(','.join(normalized))


def extract_checkpoint(state, slot):
    records = strip_tweaks_prefix(state).split(';')
    base = slot * 5
    player = records[base + 1]
    tokens = player.rstrip('\r\n').split(',')
    if len(tokens) < MIN_PLAYER_TOKENS:
        raise ValueError(f'player record too short: {len(tokens)} < {MIN_PLAYER_TOKENS}')
    out = {}
    for name, index in FIELD_INDEX.items():
        value = tokens[index]
        out[name] = value if name in STRING_FIELDS else int(value)
    out['playerrecordsha256'] = digest(player)
    out['playerrecordnodatesha256'] = player_record_without_date_digest(tokens)
    out['clubrecordsha256'] = digest(records[base + 2])
    out['competitionrecordsha256'] = digest(records[base + 3])
    out['additionalclubrecordsha256'] = digest(records[base + 4])
    return out


def extract_monkeystate_from_prefs_xml(xml_text):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)
    values = {n.attrib.get('name'): (n.text or '') for n in root.findall('string')}
    state = values.get('.monkeystate') or values.get('gxtkAppState')
    if not state:
        raise ValueError('monkeystate key not found')
    return state
