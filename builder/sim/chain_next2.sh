cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
for i in $(seq 1 300); do [ -f out/batch_ra8_kit.json ] && break; sleep 60; done
# deploy the latest code (same reads) to the slots the next experiments use
for s in "ra8 reader_ra8" "rab8 reader_rab8"; do set -- $s
  python -m compiler.c2 out/$1.json ../kit/build-the-builder/tools/openapi.json out/wf_$2.json
  python -c "import json,sys; sys.path.insert(0,'../kit/build-the-builder'); import freya; print(freya.save_workflow('$2', json.load(open('out/wf_$2.json',encoding='utf-8')), state_file='.freya-agents.json'))"
done
ST=plain,talkative,pieces,corrects,asks_back,in_words
bash sim/freya_chain.sh ad_ra9 e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab9_kit b3aa3b96-4223-4e86-9a2a-c28cc633f558 --brief B --styles $ST --reps 3
bash sim/freya_chain.sh fr_ra9 e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --scenarios synthetic/fragment_scenarios.json --reps 3
bash sim/freya_chain.sh comp_ra9 e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --scenarios synthetic/competition_scenarios.json --priority 1 --reps 3
