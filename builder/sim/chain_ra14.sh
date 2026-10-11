cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 240); do [ -f out/batch_rab12_kit.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=b42cd61c-3046-4b20-b368-801b4b858798; B=f0b04d67-cbe7-4658-84ba-1709ac28d7d9
bash sim/freya_chain.sh ra14_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh ad_ra14 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
bash sim/freya_chain.sh rab14_kit $B --brief B --styles $ST --reps 3
