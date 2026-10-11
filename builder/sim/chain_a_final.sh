# re-queue the final Brief A run (it was skipped by a transient fork error) after the fresh-read runs
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
until grep -q "done" out/chain_more.out 2>/dev/null; do sleep 30; done
for t in $(seq 1 15); do
  AA=$(python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('final_a', json.load(open('out/wf_final_a.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])" 2>/dev/null) && [ -n "$AA" ] && break
  sleep 60
done
echo "$(date +%H:%M) final_a $AA"
[ -n "$AA" ] && bash sim/freya_chain.sh final_a $AA --brief A --styles plain,talkative,pieces,corrects,asks_back,in_words --reps 3
echo "$(date +%H:%M) done"
