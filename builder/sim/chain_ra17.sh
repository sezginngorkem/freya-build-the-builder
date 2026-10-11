cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
ST=plain,talkative,pieces,corrects,asks_back,in_words
A=b1176b5e-e1ff-4f34-9f86-6f9f858c72ba; B=1765d30e-f61e-472b-bc6b-9e13f1ef1b7e
bash sim/freya_chain.sh ra17_kit $A --brief A --styles $ST --reps 3
bash sim/freya_chain.sh rab17_kit $B --brief B --styles $ST --reps 3
bash sim/freya_chain.sh ad_ra17 $A --brief A --scenarios synthetic/adversarial_scenarios.json --reps 3
