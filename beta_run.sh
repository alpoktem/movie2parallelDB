python src/segment_movie.py -a data/theman/audio_spa.wav -s data/theman/spa.srt -o data/theman/corpus/sentences_spa -l spa
python src/segment_movie.py -a data/theman/audio_eng.wav -s data/theman/eng.srt -o data/theman/corpus/sentences_eng -l eng

./src/batch_f0_parametrization.sh data/theman/corpus/sentences_eng eng
./src/batch_f0_parametrization.sh data/theman/corpus/sentences_spa spa

python src/sentenceMapper.py -e data/theman/corpus/sentences_eng/eng_sentenceData.csv -s data/theman/corpus/sentences_spa/spa_sentenceData.csv -o data/theman/corpus/eng-spa_alignment.txt -d

./src/createParallelCorpus.sh data/theman/corpus/sentences_eng data/theman/corpus/sentences_spa data/theman/corpus/eng-spa_alignment.txt data/theman/corpus/parallel-db data/theman/corpus/parallel-db/parallel-db.txt

