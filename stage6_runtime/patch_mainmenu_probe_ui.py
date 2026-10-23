#!/usr/bin/env python3
import re,sys
from pathlib import Path

DECLS=('Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)\n'
       'Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)\n')

def extract_animation(text,ref='ShieldScale1'):
    m=re.search(r'Animation:\([^\n]+\) ref:'+re.escape(ref)+r'\s*\n\s*\{',text)
    if not m: raise ValueError(f'animation {ref} not found')
    start=m.start(); brace=text.find('{',m.start()); depth=0; i=brace
    while i<len(text):
        if text[i]=='{': depth+=1
        elif text[i]=='}':
            depth-=1
            if depth==0:
                return text[start:i+1]
        i+=1
    raise ValueError(f'unterminated animation {ref}')

def patch_text(main_ui:str,shield_ui:str)->str:
    if 'Stage6ProbeA' in main_ui or 'Stage6ProbeB' in main_ui or 'Stage6ProbeC' in main_ui:
        raise ValueError('Stage6 main-menu UI probe already present')
    base=extract_animation(shield_ui,'ShieldScale1')
    clones=[]
    for ref,ns in [('Stage6ProbeA','Stage6A'),('Stage6ProbeB','Stage6B'),('Stage6ProbeC','Stage6C')]:
        c=base.replace('ref:ShieldScale1','ref:'+ref,1).replace('MatchColours',ns)
        clones.append(c)
    probe='''
// STAGE6_REAL_LOGO_RUNTIME_PROBES
PushOrigin:(0,0)
    AnimInstance:(150,320,Stage6ProbeA)
    AnimInstance:(360,320,Stage6ProbeB)
    AnimInstance:(570,320,Stage6ProbeC)
PopOrigin
'''
    return DECLS+main_ui.rstrip()+'\n\n'+'\n\n'.join(clones)+'\n'+probe

def main():
    if len(sys.argv)!=4: raise SystemExit(f'usage: {sys.argv[0]} MAINMENU.uis SHIELDANIMS.uih OUT.uis')
    mainp,shieldp,outp=map(Path,sys.argv[1:])
    outp.write_text(patch_text(mainp.read_text(encoding='utf-8-sig'),shieldp.read_text(encoding='utf-8-sig')),encoding='utf-8')
    print('STAGE6_MAINMENU_UI_PROBE=PASS refs=Stage6ProbeA,B,C')
if __name__=='__main__': main()
