package com.hakan.jarvis;

import java.util.*;

public final class ContactActionsMatchTest {
    static int pass=0,fail=0;
    static void ok(boolean v,String n){if(v)pass++;else{fail++;System.out.println("FAIL "+n);}}
    public static void main(String[]args){
        ok(ContactActions.scoreName("ahmet","Ahmet Yılmaz")>=90,"prefix");
        ok(ContactActions.scoreName("ikbal","İkbal")==120,"exact");
        ok(ContactActions.targetVariants("biraderimi").contains("birader"),"birader possessive");
        ok(ContactActions.targetVariants("annemi").contains("anne"),"anne possessive");
        ok(ContactActions.whatsAppNumber("0555 123 45 67").equals("905551234567"),"TR local");
        ok(ContactActions.whatsAppNumber("+90 555 123 45 67").equals("905551234567"),"TR intl");
        ok(ContactActions.whatsAppNumber("5551234567").equals("905551234567"),"TR short mobile");
        System.out.println("ContactActionsMatch: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
