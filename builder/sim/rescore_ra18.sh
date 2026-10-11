cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon" && source kit/build-the-builder/env.sh && cd builder
SID=055f3778-3d06-4c70-91d4-fde417ca06fd
AID=$(python -c "import json;print(json.load(open('.freya-agents.json'))['reader_ra18']['agent_id'])")
for i in $(seq 1 90); do
  st=$(python -c "
import sys; sys.path.insert(0,'../kit/build-the-builder'); import freya
try:
    s = freya.api('GET', '/api/v2/simulations/$SID'); s = s.get('simulation') or s; print(s.get('status'))
except Exception as e: print('err')")
  [ "$st" = "completed" ] && break
  sleep 60
done
python -u sim/freya_batch.py $AID --brief A --styles plain,talkative,pieces,corrects,asks_back,in_words --reps 3 --tag ra18_kit --rescore $SID >> out/batch_ra18_kit.log 2>&1
python -u sim/freya_archive.py >> out/archive.log 2>&1
