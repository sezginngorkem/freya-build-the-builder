cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 360); do [ -f out/batch_rab14_kit.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=9c554b25-d655-477d-8779-c5bd1a4fd71b
bash sim/freya_chain.sh ra15_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh ad_ra15 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
