#This is an example script for running subsegment_movie.py

audio_format=mp3
audio_eng=/Users/alp/Movies/heroes/episodes/s2_8/heroes_s2_8_eng.mp3
audio_spa=/Users/alp/Movies/heroes/episodes/s2_8/heroes_s2_8_spa.mp3

sub_eng=/Users/alp/Movies/heroes/episodes/s2_8/heroes_s2_8_eng_ocr.srt
sub_spa=/Users/alp/Movies/heroes/episodes/s2_8/heroes_s2_8_spa_ocr.srt
sub_eng_mini=/Users/alp/Movies/heroes/s2_8/heroes_s2_8_eng_mini.srt

script_eng=/Users/alp/Movies/heroes/episodes/s2_8/heroes_s2_8_transcript.txt

output_eng=/Users/alp/Movies/heroes/corpus_new/heroes_s2_8/eng
output_spa=/Users/alp/Movies/heroes/corpus_new/heroes_s2_8/spa
output_eng_mini=/Users/alp/Movies/heroes/s2_8/corpus/eng_mini

python src/subsegment_movie.py -a $audio_eng -s $sub_eng -o $output_eng -l eng -f $audio_format -c $script_eng
python src/subsegment_movie.py -a $audio_spa -s $sub_spa -o $output_spa -l spa -f $audio_format

#mini
#python src/subsegment_movie.py -a $audio_eng -s $sub_eng -o $output_eng -l eng -f $audio_format -c $script_eng 