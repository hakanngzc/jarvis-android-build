'use strict';

Java.perform(function () {
  try {
    const Globals = Java.use('com.newstargames.newstarsoccer.bb_');
    const player = Globals.g_player.value;
    if (player === null) {
      send({type: 'stage2-smoke', ok: false, error: 'g_player is null'});
      return;
    }
    send({
      type: 'stage2-smoke',
      ok: true,
      clubid: player.m_clubid.value,
      clubnationid: player.m_clubnationid.value,
      wage: player.m_wage.value,
      goalbonus: player.m_goalbonus.value,
      assistbonus: player.m_assistbonus.value,
      lastnegotiations: player.m_lastnegotiations.value,
      lasttransferdate: player.m_lasttransferdate.value,
      retired: player.m_retired.value,
      sdate: player.m_date.value.m_sdate.value
    });
  } catch (e) {
    send({type: 'stage2-smoke', ok: false, error: String(e), stack: e.stack || ''});
  }
});
