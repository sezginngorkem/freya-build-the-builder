# Fresh builds by the final builder, scored on Freya (user-approved priority, 18:15): A+B, S7, S8, then scen_adv on final_a
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
agent() { python -c "import json;print(json.load(open('.freya-agents.json'))['$1']['agent_id'])" 2>/dev/null; }
built() { until grep -q "END build" ../traces/$1.log 2>/dev/null || grep -q "Traceback" out/$1.out 2>/dev/null; do sleep 30; done; grep -q "END build" ../traces/$1.log; }
# S10 done -> start the S7 and S8 fresh builds (two at a time, as at 20:00)
built s10_final; echo "$(date +%H:%M) s10 built"
python -u build.py synthetic/S7_unseen_real/codes.csv synthetic/S7_unseen_real/email_thread.txt synthetic/S7_unseen_real/memo.txt synthetic/S7_unseen_real/policy_extract.txt synthetic/S7_unseen_real/openapi.json --slot s7_final > out/s7_final.out 2>&1 &
python -u build.py synthetic/S8_uk_unseen/brief synthetic/S8_uk_unseen/openapi.json --slot s8_final > out/s8_final.out 2>&1 &
# Freya is free once final_a's batch is over
while tasklist //FI "PID eq 12384" 2>/dev/null | grep -q python; do sleep 30; done; echo "$(date +%H:%M) final_a over"
built ab_final && bash sim/freya_chain.sh ab_fresh $(agent ab_final) --brief B --styles $ST --reps 3; echo "$(date +%H:%M) ab_fresh done"
built s7_final && bash sim/freya_chain.sh s7_fresh $(agent s7_final) --brief S7 --cases synthetic/S7_unseen_real/freya_cases.json --styles plain,pieces,talkative --reps 3; echo "$(date +%H:%M) s7_fresh done"
built s8_final && bash sim/freya_chain.sh s8_fresh $(agent s8_final) --brief S8 --cases synthetic/S8_uk_unseen/freya_cases.json --styles plain,pieces,talkative --reps 3; echo "$(date +%H:%M) s8_fresh done"
bash sim/freya_chain.sh scen_adv $(agent final_a) --brief A --scenarios synthetic/adversarial_scenarios.json --reps 2
echo "$(date +%H:%M) done"
