#!/bin/bash
# usage: bash sim/freya_chain.sh <tag> <agent_id> [freya_batch args...]  (one step; chains call it in sequence)
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
export FREYA_SIM_CONCURRENCY=${FREYA_SIM_CONCURRENCY:-15}
tag=$1; shift
python -u sim/freya_batch.py "$@" --tag $tag > out/batch_$tag.log 2>&1
python -u sim/freya_archive.py >> out/archive.log 2>&1
