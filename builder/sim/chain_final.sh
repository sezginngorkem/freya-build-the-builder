# Final-candidate experiment: the builder's current output (echo + choice reading + today's fixes, all default ON),
# on (1) S8 = unseen raw-material brief read by the builder, 1-3 products; (2) Brief B multi-product; (3) Brief A full.
# The code is compiled NOW into wf files (frozen copies), deployed when Freya is free.
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
put() {   # $1 wf file, $2 slot; retries platform errors
  for t in $(seq 1 15); do
    A=$(python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('$1', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])" 2>/dev/null) && [ -n "$A" ] && echo $A && return 0
    sleep 60
  done
  return 1
}
# wait until no simulation of ours is running (cand24 may still be on Freya)
until [ -f out/batch_cand24_tpc.json ] || ! ps -ef | grep -q "[f]reya_batch"; do sleep 30; done
echo "$(date +%H:%M) start"
A8=$(put out/wf_final_s8.json final_s8); echo "final_s8 $A8"
[ -n "$A8" ] && bash sim/freya_chain.sh final_s8 $A8 --brief S8 --cases synthetic/S8_uk_unseen/freya_cases.json --styles plain,pieces,talkative --reps 3
AB=$(put out/wf_final_b.json final_b); echo "final_b $AB"
[ -n "$AB" ] && bash sim/freya_chain.sh final_b $AB --brief B --styles $ST --reps 3
AA=$(put out/wf_final_a.json final_a); echo "final_a $AA"
[ -n "$AA" ] && bash sim/freya_chain.sh final_a $AA --brief A --styles $ST --reps 3
echo "$(date +%H:%M) done"
