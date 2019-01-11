# movie2parallelDB 
Prosodically annotated parallel speech corpus generation using dubbed movies. 

## Description 
Dubbed media content is a valuable resource for generating prosodically rich parallel audio corpora. `movie2parallelDB` automates this process taking in audio tracks and subtitles of a movie and outputting aligned voice segments with text and prosody annotation. 

A parallel audio corpus is obtained in three stages: (1) a monolingual step, where audio+text pairs are extracted from the movie in both languages using transcripts and cues in subtitles, (2) paralinguistic feature annotation (speaker information and prosody) and (3) alignment of monolingual material to extract the bilingual segments. Figure below illustrates the whole process on an example portion of a movie.

<p align="center"><img src="https://raw.githubusercontent.com/alpoktem/movie2parallelDB/master/data/movie2parallelDB-example_pipeline.png" width="500"></p>

## Requirements

* Required installations:
	- Python 3.x
	- [Montreal forced aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html)
	- [Praat](http://www.fon.hum.uva.nl/praat/)

Binary and model paths of MFA and Praat should be set in `src/paths.py`.

* Required packages:
	- [proscript](https://github.com/alpoktem/proscript), pydub, pysrt, nltk

## Raw data preparation

`movie2parallelDB` works with `wav` or `mp3` format audio files and `srt` format subtitles in both languages (original and dubbed) of the media file. MKV type video files often contain multiple audio tracks and subtitle information. `mkvinfo` can be used to get track information on the video file. Once track id's are known, audio tracks can be extracted using `mkvextract` tool of [mkvtoolnix](https://mkvtoolnix.download/): 

`mkvextract <movie-mkv-file> tracks 1:movie_spa.aac 2:movie_eng.aac 3:sub_spa.srt 4:sub_eng.srt`

In order to obtain mp3 format audio `ffmpeg` can be used:

`ffmpeg -i movie_spa.aac -c:a libmp3lame -ac 2 -b:a 320k movie_spa.mp3`
`ffmpeg -i movie_eng.aac -c:a libmp3lame -ac 2 -b:a 320k movie_eng.mp3`

Make sure that subtitles and audio match in both timing and transcription. Dubbing scripts might differ from subtitle transcripts. 

Speaker labelling is made possible with the use of script files. Script files contain a speaker turn at each line with the speaker name followed by a colon and then the line. Example of a script can be seen in the figure above. 

## Run

Monolingual segment extraction can be performed with the script `subsegment_movie.py`:

`python src/subsegment_movie.py -a <audio_eng> -s <sub_eng> -o <output_directory> -l eng -f <audio_format:wav|mp3> -c <script_eng>`

Alternatively, a batch of files specified in a text file can be given to process. Each line in the file should contain the tab separated columns: movie_id, audio_path, srt_path, script_path (optional: put NA if not available), language_id. 

`python src/subsegment_movie.py -i <process-list_eng> -o <output_directory> -l eng -f <audio_format:wav|mp3> -c <script_eng>`

Parallel corpus generation is performed using parallel text files that contain path information in the two languages:

`python src/movie2parallelDB.py -e <process-list_eng> -s <process-list_spa> -o <output_directory> -f <audio_format:wav|mp3>`

This process executes the monolingual process for both languages and then aligns the extracted segments. 

## Disclaimer

[Heroes corpus](https://repositori.upf.edu/handle/10230/35572) is generated using this library. 

## Citing

Final version of this library is explained in Iberspeech 2018: [Paper link](https://www.isca-speech.org/archive/IberSPEECH_2018/abstracts/IberS18_P1-1_Oktem.html)
	
	@inproceedings{Öktem2018,
		author={Alp Öktem and Mireia Farrús and Antonio Bonafonte},
		title={{Bilingual Prosodic Dataset Compilation for Spoken Language Translation}},
		year=2018,
		booktitle={Proc. IberSPEECH 2018},
		pages={20--24},
		doi={10.21437/IberSPEECH.2018-5},
		url={http://dx.doi.org/10.21437/IberSPEECH.2018-5}	
	}

This work is originally introduced in BUCC workshop under ACL 2017: [Paper link](https://repositori.upf.edu/handle/10230/32716)

	@inproceedings{movie2parallelDB,
		author = {Alp Oktem and Mireia Farrus and Leo Wanner},
		title = {Automatic extraction of parallel speech corpora from dubbed movies},
		booktitle = {Proceedings of the 10th Workshop on Building and Using Comparable Corpora (BUCC)},
		year = {2017},
		address = {Vancouver, Canada}
	}

(See `README_beta.md` for instructions of the earlier version)
