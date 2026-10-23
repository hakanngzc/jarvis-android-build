#!/usr/bin/env python3
import re,sys
from pathlib import Path

SETUP_RE=re.compile(r'(?ms)^\.method public static m_SetUpScreen\(\)I\n(?P<body>.*?)^\.end method\s*$')
MARK='m_Stage6LoadBadgeProbes'

HELPERS=r'''
.method public static m_Stage6ApplyBadgeProbe(Lcom/newstargames/newstarsoccer/c_TBase_Team;Ljava/lang/String;)V
    .registers 6

    const-string v0, "Badge1Col1"
    invoke-static {p1, v0}, Lcom/newstargames/newstarsoccer/c_TweakValueColour;->m_Get(Ljava/lang/String;Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TweakValueColour;
    move-result-object v0
    iget-object v0, v0, Lcom/newstargames/newstarsoccer/c_TweakValueColour;->m_col:Lcom/newstargames/newstarsoccer/c_GColour;
    iget-object v1, p0, Lcom/newstargames/newstarsoccer/c_TBase_Team;->m_badgecol1:Lcom/newstargames/newstarsoccer/c_GColour;
    invoke-virtual {v0, v1}, Lcom/newstargames/newstarsoccer/c_GColour;->p_Clone4(Lcom/newstargames/newstarsoccer/c_GColour;)I

    const-string v0, "Badge1Col2"
    invoke-static {p1, v0}, Lcom/newstargames/newstarsoccer/c_TweakValueColour;->m_Get(Ljava/lang/String;Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TweakValueColour;
    move-result-object v0
    iget-object v0, v0, Lcom/newstargames/newstarsoccer/c_TweakValueColour;->m_col:Lcom/newstargames/newstarsoccer/c_GColour;
    iget-object v1, p0, Lcom/newstargames/newstarsoccer/c_TBase_Team;->m_badgecol2:Lcom/newstargames/newstarsoccer/c_GColour;
    invoke-virtual {v0, v1}, Lcom/newstargames/newstarsoccer/c_GColour;->p_Clone4(Lcom/newstargames/newstarsoccer/c_GColour;)I

    const-string v0, "BadgeStyle1"
    invoke-static {p1, v0}, Lcom/newstargames/newstarsoccer/c_TweakValueFloat;->m_Get(Ljava/lang/String;Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TweakValueFloat;
    move-result-object v0
    iget v1, p0, Lcom/newstargames/newstarsoccer/c_TBase_Team;->m_badgestyle:I
    int-to-float v1, v1
    iput v1, v0, Lcom/newstargames/newstarsoccer/c_TweakValueFloat;->m_value:F
    return-void
.end method

.method public static m_Stage6LoadBadgeProbes()V
    .registers 2

    const/16 v0, 0xc45
    invoke-static {v0}, Lcom/newstargames/newstarsoccer/c_TClub;->m_LoadClub(I)Lcom/newstargames/newstarsoccer/c_TClub;
    move-result-object v0
    const-string v1, "Stage6A"
    invoke-static {v0, v1}, Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;->m_Stage6ApplyBadgeProbe(Lcom/newstargames/newstarsoccer/c_TBase_Team;Ljava/lang/String;)V

    const/16 v0, 0xc5b
    invoke-static {v0}, Lcom/newstargames/newstarsoccer/c_TClub;->m_LoadClub(I)Lcom/newstargames/newstarsoccer/c_TClub;
    move-result-object v0
    const-string v1, "Stage6B"
    invoke-static {v0, v1}, Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;->m_Stage6ApplyBadgeProbe(Lcom/newstargames/newstarsoccer/c_TBase_Team;Ljava/lang/String;)V

    const/16 v0, 0xc55
    invoke-static {v0}, Lcom/newstargames/newstarsoccer/c_TClub;->m_LoadClub(I)Lcom/newstargames/newstarsoccer/c_TClub;
    move-result-object v0
    const-string v1, "Stage6C"
    invoke-static {v0, v1}, Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;->m_Stage6ApplyBadgeProbe(Lcom/newstargames/newstarsoccer/c_TBase_Team;Ljava/lang/String;)V
    return-void
.end method
'''

def patch_text(text:str)->str:
    if MARK in text:
        raise ValueError('Stage6 main-menu probe already present')
    ms=list(SETUP_RE.finditer(text))
    if len(ms)!=1:
        raise ValueError(f'expected exactly one m_SetUpScreen()I, found {len(ms)}')
    m=ms[0]; body=m.group('body')
    reg=re.search(r'(?m)^(\s*\.(?:registers|locals)\s+\d+\s*)$',body)
    if not reg: raise ValueError('m_SetUpScreen has no registers/locals directive')
    inject='\n    invoke-static {}, Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;->m_Stage6LoadBadgeProbes()V\n'
    body=body[:reg.end()]+inject+body[reg.end():]
    out=text[:m.start('body')]+body+text[m.end('body'):]
    return out.rstrip()+"\n\n"+HELPERS.strip()+"\n"

def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} IN.smali OUT.smali')
    src,dst=map(Path,sys.argv[1:]); dst.write_text(patch_text(src.read_text()),encoding='utf-8')
    print('STAGE6_MAINMENU_SMALI_PROBE=PASS ids=3141,3163,3157')
if __name__=='__main__': main()
