cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
for i in $(seq 1 240); do [ -f out/batch_ra18_kit.json ] && break; sleep 30; done
bash sim/freya_chain.sh ctrl_kit 10f242f7-6574-4f25-90c1-20f0051ef7db --brief A --styles plain,talkative,pieces,corrects,asks_back,in_words --reps 3
