# final experiment, reordered: (running) old S8 -> B -> S8 built by the NEW builder -> A
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
put() {
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
until [ -f out/batch_final_s8.json ] || ! ps -ef | grep -q "[f]reya_batch"; do sleep 30; done
AB=$(put out/wf_final_b.json final_b); echo "$(date +%H:%M) final_b $AB"
[ -n "$AB" ] && bash sim/freya_chain.sh final_b $AB --brief B --styles $ST --reps 3
until grep -q "END build" ../traces/s8_new.log 2>/dev/null; do sleep 30; done
AN=$(python -c "import json;print(json.load(open('.freya-agents.json'))['s8_new']['agent_id'])")
echo "$(date +%H:%M) s8_new $AN"
[ -n "$AN" ] && bash sim/freya_chain.sh s8_new_pp $AN --brief S8 --cases synthetic/S8_uk_unseen/freya_cases.json --styles plain,pieces,talkative --reps 3
AA=$(put out/wf_final_a.json final_a); echo "$(date +%H:%M) final_a $AA"
[ -n "$AA" ] && bash sim/freya_chain.sh final_a $AA --brief A --styles $ST --reps 3
echo "$(date +%H:%M) done"
