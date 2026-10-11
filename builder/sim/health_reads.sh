# Reader health: fresh reads of unseen-style briefs with the current reader, in parallel; then local tests per suite.
cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
run() {   # $1 tag, $2 suite dir
  d=$2; files=$(ls $d | grep -v -E "^(cases|freya_cases)\.json$|ANSWER_KEY|FREYA_KEY|SOURCES|openapi\.json" | sed "s#^#$d/#")
  s=$(date +%s); python -m reader.read out/h_$1.json $files $d/openapi.json > out/h_$1.log 2>&1; e=$(date +%s)
  echo "$1 read_seconds=$((e-s))" >> out/health_reads.out
}
: > out/health_reads.out
run s1 synthetic/S1_company_clean & run s2 synthetic/S2_raw_material & run s5 synthetic/S5_realworld_style &
run s6 synthetic/S6_messy_chain & run s7 synthetic/S7_unseen_real &
wait
echo "all reads done $(date +%H:%M)" >> out/health_reads.out
