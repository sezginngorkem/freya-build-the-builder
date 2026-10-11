cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 240); do [ -f out/batch_rab12_kit.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=83765219-e873-4885-8c95-e75b2d3ffcf6; B=7c8fd351-3770-428b-aad4-82a7f4463c24
bash sim/freya_chain.sh ra13_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh ad_ra13 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab13_kit $B --brief B --styles $ST --reps 3
