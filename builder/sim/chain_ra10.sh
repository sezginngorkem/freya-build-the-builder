cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 120); do [ -f out/batch_comp_ra9.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=8c5556c6-8af5-43e7-a65a-c9c54b824e6b; B=651ffcd9-5cec-4b0d-a809-869cf3e945c0
bash sim/freya_chain.sh ra10_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh fr_ra10 $A --brief A --scenarios synthetic/fragment_scenarios.json --reps 3
bash sim/freya_chain.sh ad_ra10 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab10_kit $B --brief B --styles $ST --reps 3
