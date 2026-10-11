# Resume after the Freya outage: score cand22's finished simulation, then deploy and run cand24 and cand23 (retrying 5xx).
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
up() { python -c "
import sys; sys.path.insert(0, '$K'); import freya
freya.api('GET', '/api/v2/simulations/9a79482e-2b6d-46ae-a807-149bab2e54bf')" >/dev/null 2>&1; }
for i in $(seq 1 120); do up && break; echo "$(date +%H:%M) Freya not answering"; sleep 60; done
echo "$(date +%H:%M) Freya answers"
python -u sim/freya_batch.py 5fe6db06-e28f-4ae4-a00e-c01220ced32b --brief A --styles talkative,pieces,corrects --reps 3 --tag cand22_tpc --rescore 9a79482e-2b6d-46ae-a807-149bab2e54bf > out/batch_cand22_tpc.log 2>&1
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
export C2_FLAGS=echo_continuer=1; A24=$(deploy out/ra15.json cand24); unset C2_FLAGS
echo "cand24 agent $A24"
[ -n "$A24" ] && bash sim/freya_chain.sh cand24_tpc $A24 --brief A --styles talkative,pieces,corrects --reps 3
export C2_INTENT_CHOICE=1; A23=$(deploy out/ra15.json cand23); unset C2_INTENT_CHOICE
echo "cand23 agent $A23"
[ -n "$A23" ] && bash sim/freya_chain.sh cand23_pub09 $A23 --brief A --styles $ST --reps 3 --only PUB-09 && bash sim/freya_chain.sh cand23_tpc $A23 --brief A --styles talkative,pieces,corrects --reps 3
echo "$(date +%H:%M) chain done"
