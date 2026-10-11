# Last Freya wave, every agent with ALL of today's fixes: A (6 styles x3), 70 hard scenarios x2, S7 fixed, B fixed
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
put() {   # $1 wf, $2 slot
  for t in $(seq 1 15); do
    A=$(python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('$1', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])" 2>/dev/null) && [ -n "$A" ] && echo $A && return 0
    sleep 30
  done
  return 1
}
until grep -q "done" out/chain_more.out 2>/dev/null; do sleep 30; done
AA=$(put out/wf_final_a.json final_a); echo "$(date +%H:%M) final_a $AA"
[ -n "$AA" ] && bash sim/freya_chain.sh final_a $AA --brief A --styles $ST --reps 3
[ -n "$AA" ] && bash sim/freya_chain.sh scen_comp $AA --brief A --scenarios synthetic/competition_scenarios.json --reps 2
[ -n "$AA" ] && bash sim/freya_chain.sh scen_adv $AA --brief A --scenarios synthetic/adversarial_scenarios.json --reps 2
A7=$(put out/wf_s7_fix.json s7_fix); echo "$(date +%H:%M) s7_fix $A7"
[ -n "$A7" ] && bash sim/freya_chain.sh s7_fix $A7 --brief S7 --cases synthetic/S7_unseen_real/freya_cases.json --styles plain,pieces,talkative --reps 3
AB=$(put out/wf_b_fix.json b_fix); echo "$(date +%H:%M) b_fix $AB"
[ -n "$AB" ] && bash sim/freya_chain.sh b_fix $AB --brief B --styles $ST --reps 3
echo "$(date +%H:%M) done"
