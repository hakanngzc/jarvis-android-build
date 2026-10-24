'use strict';

const SCENARIO = '__SCENARIO__';
const SENTINEL_WAGE = 4321;
const SENTINEL_GOAL = 321;
const SENTINEL_ASSIST = 123;
const SENTINEL_RETIRED = 777777;

Java.perform(function () {
  function readState(player) {
    return {
      clubid: player.m_clubid.value,
      clubnationid: player.m_clubnationid.value,
      wage: player.m_wage.value,
      goalbonus: player.m_goalbonus.value,
      assistbonus: player.m_assistbonus.value,
      lastnegotiations: player.m_lastnegotiations.value,
      lasttransferdate: player.m_lasttransferdate.value,
      retired: player.m_retired.value,
      sdate: player.m_date.value.m_sdate.value
    };
  }

  function makeOffer(Offer, club) {
    const offer = Offer.$new();
    offer.m_club.value = club;
    offer.m_offerclubid.value = club.m_id.value;
    offer.m_wage.value = SENTINEL_WAGE;
    offer.m_goalbonus.value = SENTINEL_GOAL;
    offer.m_assistbonus.value = SENTINEL_ASSIST;
    offer.m_endofseason.value = false;
    offer.m_negotiationsuccess.value = 100;
    return offer;
  }

  try {
    const Globals = Java.use('com.newstargames.newstarsoccer.bb_');
    const Offer = Java.use('com.newstargames.newstarsoccer.c_TContractOffer');
    const Club = Java.use('com.newstargames.newstarsoccer.c_TClub');
    const Contract = Java.use('com.newstargames.newstarsoccer.c_TScreen_Contract');
    const Retirement = Java.use('com.newstargames.newstarsoccer.c_TScreen_Retirement');
    const player = Globals.g_player.value;
    if (player === null) throw new Error('g_player is null');

    const before = readState(player);
    let targetClubId = before.clubid;
    let branchReturn = null;

    if (SCENARIO === 'accept') {
      const offer = makeOffer(Offer, player.m_myclub.value);
      Contract.m_offer.value = offer;
      branchReturn = Contract.m_ButtonAccept(false);
    } else if (SCENARIO === 'reject') {
      const offer = makeOffer(Offer, player.m_myclub.value);
      Contract.m_offer.value = offer;
      branchReturn = Contract.m_ButtonReject();
    } else if (SCENARIO === 'transfer') {
      let target = null;
      for (let delta = 1; delta <= 256; delta++) {
        const candidate = Club.m_SelectById(before.clubid + delta, false);
        if (candidate !== null && candidate.m_id.value !== before.clubid) {
          target = candidate;
          break;
        }
      }
      if (target === null) throw new Error('could not find a different valid club within +256 IDs');
      targetClubId = target.m_id.value;
      const offer = makeOffer(Offer, target);
      Contract.m_offer.value = offer;
      branchReturn = Contract.m_ButtonAccept(false);
    } else if (SCENARIO === 'retirement') {
      Retirement.m_SetUpScreen();
      const score = Retirement.m_score.value;
      score[0] = SENTINEL_RETIRED;
      branchReturn = Retirement.m_ButtonPlay();
    } else {
      throw new Error('unknown Stage2 scenario: ' + SCENARIO);
    }

    const after = readState(player);
    send({
      type: 'stage2-scenario',
      ok: true,
      scenario: SCENARIO,
      before: before,
      after: after,
      target_clubid: targetClubId,
      branch_return: branchReturn,
      sentinels: {
        wage: SENTINEL_WAGE,
        goalbonus: SENTINEL_GOAL,
        assistbonus: SENTINEL_ASSIST,
        retired: SENTINEL_RETIRED
      }
    });
  } catch (e) {
    send({type: 'stage2-scenario', ok: false, scenario: SCENARIO, error: String(e), stack: e.stack || ''});
  }
});
