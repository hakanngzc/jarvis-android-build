import hashlib
FIELD_INDEX={'sdate':0,'clubnationid':1,'clubid':2,'fullname':3,'shortname':4,'careerapps':13,'goalbonus':33,'wage':34,'lastnegotiations':59,'lasttransferdate':60}
STRING_FIELDS={'fullname','shortname'}
MIN_PLAYER_TOKENS=max(FIELD_INDEX.values())+1

def strip_tweaks_prefix(state):
    if state.startswith('#TWEAKS'):
        marker='#ENDTWEAKS'; end=state.find(marker)
        if end<0: raise ValueError('unterminated tweaks prefix')
        state=state[end+len(marker):].lstrip('\r\n')
    return state

def digest(v): return hashlib.sha256(v.encode()).hexdigest()
def extract_checkpoint(state,slot):
    records=strip_tweaks_prefix(state).split(';'); base=slot*5
    player=records[base+1]; tokens=player.rstrip('\r\n').split(',')
    if len(tokens)<MIN_PLAYER_TOKENS: raise ValueError('player record too short')
    out={}
    for name,index in FIELD_INDEX.items():
        value=tokens[index]; out[name]=value if name in STRING_FIELDS else int(value)
    out['playerrecordsha256']=digest(player); out['clubrecordsha256']=digest(records[base+2]); out['competitionrecordsha256']=digest(records[base+3]); out['additionalclubrecordsha256']=digest(records[base+4])
    return out

def extract_monkeystate_from_prefs_xml(xml_text):
    import xml.etree.ElementTree as ET
    root=ET.fromstring(xml_text); values={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}
    state=values.get('.monkeystate') or values.get('gxtkAppState')
    if not state: raise ValueError('monkeystate key not found')
    return state
