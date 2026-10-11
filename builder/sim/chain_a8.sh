cd "/c/Users/sezgi/OneDrive/Masaüstü/hackathon/builder"
ST=plain,talkative,pieces,corrects,asks_back,in_words
bash sim/freya_chain.sh a8_kit 2ae0a326-17ef-443a-bbaf-27801b6dfd98 --brief A --styles $ST --reps 3
bash sim/freya_chain.sh fr_a8 2ae0a326-17ef-443a-bbaf-27801b6dfd98 --brief A --scenarios synthetic/fragment_scenarios.json --reps 3
bash sim/freya_chain.sh ra8_kit e4236f22-c2db-44d4-9805-3854e3815e70 --brief A --styles $ST --reps 3
