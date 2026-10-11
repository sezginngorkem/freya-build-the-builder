cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
for i in $(seq 1 240); do [ -f out/batch_ra18_kit.json ] && break; sleep 30; done
bash sim/freya_chain.sh ctrl_kit 10f242f7-6574-4f25-90c1-20f0051ef7db --brief A --styles $ST --reps 3
bash sim/freya_chain.sh arm_no_pub09 c36934b7-0af9-4df8-bf0e-a7738981d784 --brief A --styles $ST --reps 3 --only PUB-09
bash sim/freya_chain.sh arm_toomuch_pub09 1bc1d9e7-b6db-498e-b9e6-da3ab2481785 --brief A --styles $ST --reps 3 --only PUB-09
deploy() {
  python -m compiler.c2 "$1" $K/tools/openapi.json "out/wf_$2.json" > /dev/null || return 1
  python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('out/wf_$2.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])"
}
for r in rq_a1 rq_a2 rq_a3; do A=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $A --brief A --styles $ST --reps 3; done
for r in rq_ab1 rq_ab2; do B=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $B --brief B --styles $ST --reps 3; done
