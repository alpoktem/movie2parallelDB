#Sample commands to process sample data

audio_format=mp3
audio_eng=data/heroes/s2_7_excerpt/heroes_s2_7_excerpt_eng.mp3
audio_spa=data/heroes/s2_7_excerpt/heroes_s2_7_excerpt_spa.mp3

sub_eng=data/heroes/s2_7_excerpt/heroes_s2_7_excerpt_eng.srt
sub_spa=data/heroes/s2_7_excerpt/heroes_s2_7_excerpt_spa.srt

script_eng=data/heroes/s2_7_excerpt/heroes_s2_7_excerpt_transcript.txt

output_eng=data/heroes/corpus_eng
output_spa=data/heroes/corpus_spa
output=data/heroes/corpus

episode_list_eng=data/heroes/episode_list_eng.txt
episode_list_spa=data/heroes/episode_list_spa.txt

#To generate monolingual corpus
# python src/subsegment_movie.py -a $audio_eng -s $sub_eng -o $output_eng -l eng -f $audio_format -c $script_eng
# python src/subsegment_movie.py -a $audio_spa -s $sub_spa -o $output_spa -l spa -f $audio_format

# #To generate parallel corpus
python src/movie2parallelDB.py -e $episode_list_eng -s $episode_list_spa -o $output