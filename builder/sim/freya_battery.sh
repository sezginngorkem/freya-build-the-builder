#!/usr/bin/env bash
# Full Freya experiment battery on one agent version, run one simulation at a time (the workspace allows one).
# Usage: bash sim/freya_battery.sh <tag> <agent_id_A> <agent_id_AB>
set -u
TAG=$1; AG=$2; AB=$3
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh
O="$(pwd)/builder/out"
cd kit/build-the-builder
echo "[$(date +%H:%M)] default x3" >> $O/battery_$TAG.log
python -u tools/run_cases.py $AG --brief A --reps 3 --out $O/sim_${TAG}_default.json > $O/sim_${TAG}_default.log 2>&1
for s in talkative corrects pieces asks_back in_words; do
  echo "[$(date +%H:%M)] style $s x2" >> $O/battery_$TAG.log
  python -u tools/run_cases.py $AG --brief A --reps 2 --style $s --out $O/sim_${TAG}_$s.json > $O/sim_${TAG}_$s.log 2>&1
done
cd ../../builder
echo "[$(date +%H:%M)] probes x2" >> $O/battery_$TAG.log
python -u sim/freya_probe.py $AG --reps 2 --tag $TAG > $O/probe_$TAG.log 2>&1
echo "[$(date +%H:%M)] brief B x3" >> $O/battery_$TAG.log
cd ../kit/build-the-builder
python -u tools/run_cases.py $AB --brief B --reps 3 --out $O/sim_${TAG}_B.json > $O/sim_${TAG}_B.log 2>&1
cd ../../builder
echo "[$(date +%H:%M)] hard personas x1" >> $O/battery_$TAG.log
python -u sim/freya_personas.py $AG --reps 1 --tag $TAG > $O/persona_$TAG.log 2>&1
echo "[$(date +%H:%M)] done" >> $O/battery_$TAG.log
