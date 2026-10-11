# after the final chain: fresh reads by the NEW builder on Freya -- S7 (unseen raw material) and Brief A (consistency)
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
until grep -q "done" out/chain_final2.out 2>/dev/null; do sleep 30; done
until grep -q "END build" ../traces/s7_new.log 2>/dev/null; do sleep 30; done
A7=$(python -c "import json;print(json.load(open('.freya-agents.json'))['s7_new']['agent_id'])")
echo "$(date +%H:%M) s7_new $A7"
bash sim/freya_chain.sh s7_new_ppt $A7 --brief S7 --cases synthetic/S7_unseen_real/freya_cases.json --styles plain,pieces,talkative --reps 3
until grep -q "END build" ../traces/a_new.log 2>/dev/null; do sleep 30; done
AA=$(python -c "import json;print(json.load(open('.freya-agents.json'))['a_new']['agent_id'])")
echo "$(date +%H:%M) a_new $AA"
bash sim/freya_chain.sh a_new_ppt $AA --brief A --styles plain,pieces,talkative --reps 3
echo "$(date +%H:%M) done"
