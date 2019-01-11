# movie2parallelDB 
Prosodically annotated parallel speech corpus generation using dubbed movies. 

## Description 
Dubbed media content is a valuable resource for generating prosodically rich parallel audio corpora. `movie2parallelDB` automates this process taking in audio tracks and subtitles of a movie and outputting aligned voice segments with text and prosody annotation. 

A parallel audio corpus is obtained in three stages: (1) a monolingual step, where audio+text pairs are extracted from the movie in both languages using transcripts and cues in subtitles, (2) paralinguistic feature annotation (speaker information and prosody) and (3) alignment of monolingual material to extract the bilingual segments. Figure below illustrates the whole process on an example portion of a movie.

![movie2parallelDB pipeline illustrated](https://raw.githubusercontent.com/alpoktem/movie2parallelDB/master/data/movie2parallelDB-example_pipeline.png =250x)

## Requirements

* Required installations:
	- Python 3.x
	- [Montreal forced aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html)
	- [Praat](http://www.fon.hum.uva.nl/praat/)

Binary and model paths of MFA and Praat should be set in `src/paths.py`.

* Required packages:
	- [proscript](https://github.com/alpoktem/proscript), pydub, pysrt, nltk

## Raw data preparation

`movie2parallelDB` works with `wav` or `mp3` format audio files and `srt` format subtitles in both languages (original and dubbed) of the media file. MKV type video files usually contain all audio tracks and subtitle information. `mkvinfo` can be used to get track information on the video file. Once track id's are known audio tracks can be extracted using `mkvextract`: 

`mkvextract <movie-mkv-file> tracks 1:movie_spa.aac 2:movie_eng.aac 3:sub_spa.srt 4:sub_eng.srt`

In order to obtain mp3 format audio `ffmpeg` can be used:

`ffmpeg -i movie_spa.aac -c:a libmp3lame -ac 2 -b:a 320k movie_spa.mp3`
`ffmpeg -i movie_eng.aac -c:a libmp3lame -ac 2 -b:a 320k movie_eng.mp3`

Make sure that subtitles and audio match in both timing and transcription. Dubbing scripts might differ from subtitle transcripts. 

## Run

`movie2parallelDB`

Monolingual segments can be generated using:

Sample data is placed in `example` directory. Run `subseg_run.sh` to test the system on the example data.

## Disclaimer


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
