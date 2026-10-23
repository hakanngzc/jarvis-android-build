#!/usr/bin/env python3
import unittest

import patch_mainmenu_probe_smali as smali_patch
import patch_mainmenu_probe_ui as ui_patch

MAIN_SMALI='''.class public Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;
.super Ljava/lang/Object;

.method public static m_SetUpScreen()I
    .registers 7
    const/4 v0, 0x1
    return v0
.end method
'''

MAIN_UI='''Import:(ButtonDefs.uis)\nCAT:(BootMenu,EXC)\nDraw:(White,0,0,720,1280)\n'''

SHIELD_UI='''
Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)
Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)
        Animation:(5000,Loop,80) ref:ShieldScale1
        {
            During:(30,79)
            {
                Draw:(MapShieldWhite,0,0,-105,142)
                Rect:(0,0,0,0)
                    ColReadout(MatchColours,Badge1Col2)
                    Selector(MatchColours,BadgeStyle1)
                {
                    Rect:(0,0,0,0)
                    Draw:(MapShieldDesign7,0,0,-105,142)
                    Draw:(MapShieldDesign15,0,0,-105,142)
                    Draw:(RebornBadge3141,0,0,-105,142)
                    Draw:(RebornBadge3163,0,0,-105,142)
                }
                Draw:(MapShieldFrameAll,0,0,-105,142)
            }
        }
'''


class MainMenuSmaliProbeTests(unittest.TestCase):
    def test_real_club_ids_are_loaded_and_applied_to_three_namespaces(self):
        out=smali_patch.patch_text(MAIN_SMALI)
        self.assertIn('invoke-static {}, Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;->m_Stage6LoadBadgeProbes()V',out)
        self.assertIn('const/16 v0, 0xc45',out)
        self.assertIn('const/16 v0, 0xc5b',out)
        self.assertIn('const/16 v0, 0xc55',out)
        self.assertEqual(out.count('->m_LoadClub(I)Lcom/newstargames/newstarsoccer/c_TClub;'),3)
        self.assertIn('const-string v1, "Stage6A"',out)
        self.assertIn('const-string v1, "Stage6B"',out)
        self.assertIn('const-string v1, "Stage6C"',out)
        self.assertIn('->m_badgecol1:Lcom/newstargames/newstarsoccer/c_GColour;',out)
        self.assertIn('->m_badgecol2:Lcom/newstargames/newstarsoccer/c_GColour;',out)
        self.assertIn('->m_badgestyle:I',out)
        self.assertIn('Lcom/newstargames/newstarsoccer/c_TweakValueFloat;->m_Get',out)

    def test_smali_probe_refuses_second_application(self):
        once=smali_patch.patch_text(MAIN_SMALI)
        with self.assertRaises(ValueError): smali_patch.patch_text(once)


class MainMenuUiProbeTests(unittest.TestCase):
    def test_stock_shield_animation_is_cloned_for_three_runtime_namespaces(self):
        out=ui_patch.patch_text(MAIN_UI,SHIELD_UI)
        self.assertEqual(out.count('ref:Stage6ProbeA'),1)
        self.assertEqual(out.count('ref:Stage6ProbeB'),1)
        self.assertEqual(out.count('ref:Stage6ProbeC'),1)
        self.assertIn('Selector(Stage6A,BadgeStyle1)',out)
        self.assertIn('Selector(Stage6B,BadgeStyle1)',out)
        self.assertIn('Selector(Stage6C,BadgeStyle1)',out)
        self.assertIn('ColReadout(Stage6A,Badge1Col2)',out)
        self.assertEqual(out.count('AnimInstance:(150,320,Stage6ProbeA)'),1)
        self.assertEqual(out.count('AnimInstance:(360,320,Stage6ProbeB)'),1)
        self.assertEqual(out.count('AnimInstance:(570,320,Stage6ProbeC)'),1)
        self.assertEqual(out.count('Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)'),1)
        self.assertEqual(out.count('Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)'),1)

    def test_ui_probe_refuses_second_application(self):
        once=ui_patch.patch_text(MAIN_UI,SHIELD_UI)
        with self.assertRaises(ValueError): ui_patch.patch_text(once,SHIELD_UI)


if __name__=='__main__': unittest.main()
