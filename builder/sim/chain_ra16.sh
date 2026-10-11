cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 240); do [ -f out/batch_ad_ra15.json ] && break; sleep 30; done
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=26193f93-25e7-485b-8b49-8b649ec480d1; B=f0f36090-996b-4f5f-8a20-b476924b9438
bash sim/freya_chain.sh ra16_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh rab16_kit $B --brief B --styles $ST --reps 3
bash sim/freya_chain.sh ad_ra16 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
