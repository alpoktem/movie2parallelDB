python src/segment_movie.py -a example/input/audio_spa.wav -s example/input/spa.srt -o example/output/sentences_spa -l spa
python src/segment_movie.py -a example/input/audio_eng.wav -s example/input/eng.srt -o example/output/sentences_eng -l eng

./src/batch_f0_parametrization.sh example/output/sentences_eng eng
./src/batch_f0_parametrization.sh example/output/sentences_spa spa

python src/sentenceMapper.py -e example/output/sentences_eng/eng_sentenceData.csv -s example/output/sentences_spa/spa_sentenceData.csv -o example/output/eng-spa_alignment.txt -d

./src/createParallelCorpus.sh example/output/sentences_eng example/output/sentences_spa example/output/eng-spa_alignment.txt example/output/parallel-db example/output/parallel-db/parallel-db.txt

