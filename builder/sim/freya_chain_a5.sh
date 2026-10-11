#!/bin/bash
# a5 measurement chain; each step archives every simulation afterwards (nothing goes unreviewed)
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
run() { tag=$1; shift; python -u sim/freya_batch.py "$@" --tag $tag > out/batch_$tag.log 2>&1; python -u sim/freya_archive.py >> out/archive.log 2>&1; }
run a5_kit 159481f2-08dd-47c9-ba1d-541d5f85943b --brief A --styles plain,talkative,pieces,corrects,asks_back,in_words --reps 3
