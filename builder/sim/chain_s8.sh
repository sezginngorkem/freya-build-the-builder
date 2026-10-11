# after cand24: cand23 PUB-09, then S8 (unseen brief) old read vs new read on the same current code, then cand23 wide
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
deploy() {   # $1 IR, $2 slot; retries platform errors
  python -m compiler.c2 "$1" $K/tools/openapi.json "out/wf_$2.json" > /dev/null || return 1
  for t in 1 2 3 4 5 6 7 8 9 10; do
    A=$(python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('out/wf_$2.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])" 2>/dev/null) && [ -n "$A" ] && echo $A && return 0
    sleep 60
  done
  return 1
}
until [ -f out/batch_cand24_tpc.json ]; do sleep 30; done
echo "$(date +%H:%M) cand24 done"
export C2_INTENT_CHOICE=1; A23=$(deploy out/ra15.json cand23); unset C2_INTENT_CHOICE
echo "cand23 agent $A23"
[ -n "$A23" ] && bash sim/freya_chain.sh cand23_pub09 $A23 --brief A --styles $ST --reps 3 --only PUB-09
S8C=synthetic/S8_uk_unseen/freya_cases.json
O=$(deploy out/s8_e2e3/policy_ir.json s8_old_cur); echo "s8 old agent $O"
[ -n "$O" ] && bash sim/freya_chain.sh s8_old_pp $O --brief S8 --cases $S8C --styles plain,pieces --reps 3
N=$(deploy out/s8_fast1/policy_ir.json s8_new_cur); echo "s8 new agent $N"
[ -n "$N" ] && bash sim/freya_chain.sh s8_new_pp $N --brief S8 --cases $S8C --styles plain,pieces --reps 3
[ -n "$A23" ] && bash sim/freya_chain.sh cand23_tpc $A23 --brief A --styles talkative,pieces,corrects --reps 3
echo "$(date +%H:%M) chain done"
