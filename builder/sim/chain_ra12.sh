cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=2df9003d-9c4f-4d5f-a4f6-06864a9332d8; B=ea60e3d8-2be4-4c98-abb9-5da1273a3a06
bash sim/freya_chain.sh ad_ra12 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh ra12_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh fr_ra12 $A --brief A --scenarios synthetic/fragment_scenarios.json --reps 3
bash sim/freya_chain.sh rab12_kit $B --brief B --styles $ST --reps 3
