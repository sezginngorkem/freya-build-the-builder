cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
deploy() {
  python -m compiler.c2 "$1" $K/tools/openapi.json "out/wf_$2.json" > /dev/null || return 1
  python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('out/wf_$2.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])"
}
# wait for the running control batch (ctrl_kit) to finish
for i in $(seq 1 240); do [ -f out/batch_ctrl_kit.json ] && break; sleep 30; done
bash sim/freya_chain.sh arm_no_pub09 c36934b7-0af9-4df8-bf0e-a7738981d784 --brief A --styles $ST --reps 3 --only PUB-09
bash sim/freya_chain.sh arm_toomuch_pub09 1bc1d9e7-b6db-498e-b9e6-da3ab2481785 --brief A --styles $ST --reps 3 --only PUB-09
# cand22 = the ra18 read (ra15 IR) + current code (weekday anaphora, continuer note in the extraction contract)
A=$(deploy out/ra15.json cand22) && bash sim/freya_chain.sh cand22_tpc $A --brief A --styles talkative,pieces,corrects --reps 3
# cand24 = cand22 + echo continuer (a cut message is answered with the customer's own unfinished words)
export C2_FLAGS=echo_continuer=1; A24=$(deploy out/ra15.json cand24); unset C2_FLAGS; [ -n "$A24" ] && bash sim/freya_chain.sh cand24_tpc $A24 --brief A --styles talkative,pieces,corrects --reps 3
# cand23 = cand22 + the choice-form second intent reading (C2_INTENT_CHOICE=1); PUB-09 first, then the same styles
export C2_INTENT_CHOICE=1; A23=$(deploy out/ra15.json cand23); unset C2_INTENT_CHOICE; [ -n "$A23" ] && bash sim/freya_chain.sh cand23_pub09 $A23 --brief A --styles $ST --reps 3 --only PUB-09 && bash sim/freya_chain.sh cand23_tpc $A23 --brief A --styles talkative,pieces,corrects --reps 3
for r in rq_a1 rq_a2 rq_a3; do A=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $A --brief A --styles $ST --reps 3; done
for r in rq_ab1 rq_ab2; do B=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $B --brief B --styles $ST --reps 3; done
