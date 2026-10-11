# Fresh reads by the final builder, recompiled with the current engine/glue (lost-request resend), scored on Freya
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
deploy() {   # $1 IR, $2 openapi, $3 slot
  python -m compiler.c2 "$1" "$2" "out/wf_$3.json" > /dev/null || return 1
  for t in 1 2 3 4 5 6 7 8 9 10; do
    A=$(python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$3', json.load(open('out/wf_$3.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])" 2>/dev/null) && [ -n "$A" ] && echo $A && return 0
    sleep 30
  done
  return 1
}
built() { until grep -q "END build" ../traces/$1.log 2>/dev/null || grep -q "Traceback" out/$1.out 2>/dev/null; do sleep 30; done; grep -q "END build" ../traces/$1.log; }
AB=$(deploy out/ab_final/policy_ir.json $K/tools/openapi.json ab_final); echo "$(date +%H:%M) ab $AB"
[ -n "$AB" ] && bash sim/freya_chain.sh ab_fresh2 $AB --brief B --styles $ST --reps 3; echo "$(date +%H:%M) ab_fresh2 done"
AA=$(deploy out/a_new/policy_ir.json $K/tools/openapi.json a_resend); echo "$(date +%H:%M) a $AA"
[ -n "$AA" ] && bash sim/freya_chain.sh a_resend $AA --brief A --styles pieces,corrects,talkative,in_words --reps 3; echo "$(date +%H:%M) a_resend done"
built s7_final && A7=$(deploy out/s7_final/policy_ir.json synthetic/S7_unseen_real/openapi.json s7_final) && bash sim/freya_chain.sh s7_fresh $A7 --brief S7 --cases synthetic/S7_unseen_real/freya_cases.json --styles plain,pieces,talkative --reps 3; echo "$(date +%H:%M) s7_fresh done"
built s8_final && A8=$(deploy out/s8_final/policy_ir.json synthetic/S8_uk_unseen/openapi.json s8_final) && bash sim/freya_chain.sh s8_fresh $A8 --brief S8 --cases synthetic/S8_uk_unseen/freya_cases.json --styles plain,pieces,talkative --reps 3; echo "$(date +%H:%M) s8_fresh done"
echo "$(date +%H:%M) done"
