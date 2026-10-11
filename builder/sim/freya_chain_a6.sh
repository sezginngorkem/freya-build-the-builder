#!/bin/bash
# queued after the a5 chain: a6 (same IR as a5, new engine: controlled A/B) then ra6 (fresh read: the real builder)
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
for i in $(seq 1 240); do [ -f out/batch_a5_kit.json ] && break; sleep 60; done
run() { tag=$1; shift; python -u sim/freya_batch.py "$@" --tag $tag > out/batch_$tag.log 2>&1; python -u sim/freya_archive.py >> out/archive.log 2>&1; }
ST=plain,talkative,pieces,corrects,asks_back,in_words
run a6_kit 7aff3075-f1b2-4b8e-b72d-68251f4339a5 --brief A --styles $ST --reps 3
run ra6_kit 0787392a-bf7c-4682-9924-e21420ee2ec3 --brief A --styles $ST --reps 3
