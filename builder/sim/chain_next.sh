cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 300); do [ -f out/batch_ra8_kit.json ] && break; sleep 60; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
bash sim/freya_chain.sh ad_ra8 e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab8_kit b3aa3b96-4223-4e86-9a2a-c28cc633f558 --brief B --styles $ST --reps 3
bash sim/freya_chain.sh comp_ra8 e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --scenarios synthetic/competition_scenarios.json --priority 1 --reps 3
