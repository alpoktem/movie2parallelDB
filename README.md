# movie2parallelDB 
Prosodically annotated parallel speech corpus generation using dubbed movies. 

## Description 
Dubbing is a carefully designed process where the movie content is first translated and then acted by professionals to reflect original movie lines. Dubbed media content is a valuable resource for generating prosodically rich parallel audio corpora. `movie2parallelDB` automates this process taking in audio tracks and subtitles and outputting aligned voice segments annotated with transcription and prosodic features. 

## Requirements


## Raw data preparation

In order to obtain mp3 audio from a multichannel video file, you can use `ffmpeg`:

`ffmpeg -i <multichannel-movie-file> -map 0:1 -c:a libmp3lame -b:a:0 320k <audio_1.mp3>`

## Run

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
