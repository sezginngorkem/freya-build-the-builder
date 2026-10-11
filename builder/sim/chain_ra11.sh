cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 120); do [ -f out/batch_rab10_kit.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=c55f7406-c8e2-49a1-ba0b-62b53d548a56; B=ad37d945-f85e-42cb-ae1c-a92d370a4c13
bash sim/freya_chain.sh ra11_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh fr_ra11 $A --brief A --scenarios synthetic/fragment_scenarios.json --reps 3
bash sim/freya_chain.sh ad_ra11 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab11_kit $B --brief B --styles $ST --reps 3
