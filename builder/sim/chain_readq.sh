#!/bin/bash
# Read-quality battery: same code, several fresh reads; each read compiled, deployed and run on Freya (3 reps).
# Order: ra18 (read ra15 + current code: the code effect alone), then fresh reads rq_a1..3 (A kit) and rq_ab1..2 (B kit).
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
K=../kit/build-the-builder
ST=plain,talkative,pieces,corrects,asks_back,in_words
for i in $(seq 1 240); do [ -f out/batch_expB_pub09.json ] && break; sleep 30; done

deploy() {   # $1 = IR json, $2 = slot -> prints agent id
  python -m compiler.c2 "$1" $K/tools/openapi.json "out/wf_$2.json" > /dev/null || return 1
  python -c "
import json, sys
sys.path.insert(0, '$K'); import freya
r = freya.save_workflow('$2', json.load(open('out/wf_$2.json', encoding='utf-8')), state_file='.freya-agents.json')
print(r['agent_id'])"
}

A=$(deploy out/ra15.json reader_ra18) && bash sim/freya_chain.sh ra18_kit $A --brief A --styles $ST --reps 3
for r in rq_a1 rq_a2 rq_a3; do
  for i in $(seq 1 120); do [ -f out/$r.json ] && break; sleep 30; done
  [ -f out/$r.json ] || continue
  A=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $A --brief A --styles $ST --reps 3
done
for r in rq_ab1 rq_ab2; do
  for i in $(seq 1 120); do [ -f out/$r.json ] && break; sleep 30; done
  [ -f out/$r.json ] || continue
  B=$(deploy out/$r.json $r) && bash sim/freya_chain.sh ${r}_kit $B --brief B --styles $ST --reps 3
done
