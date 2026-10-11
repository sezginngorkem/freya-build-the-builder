cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 240); do [ -f out/batch_ad_ra17.json ] && break; sleep 30; done
bash sim/freya_chain.sh expB_pub09 467b5a62-62a5-40f8-933a-b4f9cf632e03 --brief A --styles plain,talkative,pieces,corrects,asks_back,in_words --reps 3 --only PUB-09
