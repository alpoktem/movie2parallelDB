# movie2parallelDB
Automated prosodically annotated parallel speech database extraction using dubbed movies.
(Instructions below are for an earlier version of the library which should still work. The latest version uses the scripts `subsegment_movie.py` and `movie2parallelDB.py`. It is not documented yet for time constraints. If you are interested drop the author a line. )

## Usage

* Inputs: 
	- Movie audio in language1 - `<audio_1>`
	- Movie audio in language2 - `<audio_2>`
	- Subtitles (.srt) in language1 - `<srt_1>`
	- Subtitles (.srt) in language2 - `<srt_2>`

* Outputs:
	- Language 1 cropped sentences directory - `<lang1-sentence-segments-output-folder>`
	- Language 2 cropped sentences directory - `<lang2-sentence-segments-output-folder>`
	- Parallel text data - `<parallel-data-textdump>`
	- Parallel speech+prosodic parameters directory - `<parallel-db-folder>`

* Required installations on Linux system:
	- Python 2.7, avconv, meteor

* Required Python libraries:
	- yandex_translate, numpy, nltk

* Required library accesses:
	- Scriber - credentials for scriber (https://scribe.vocapia.com/) should be set on `src/credentials.py` for this step to run. If you don't have access credentials for this service, the word segmentation output should look like `example/example-scriber-wordsegmentation.xml`

## Database Extraction

In order to extract mp3 audio from multichannel video file, you can use ffmpeg:

`ffmpeg -i <multichannel-movie-file> -map 0:1 -c:a libmp3lame -b:a:0 320k <audio_1.mp3>`

Call segment_movie.py to extract sentences from audio and subtitle pair:

`python src/segment_movie.py -a <audio> -s <srt> -o <sentence-segments-output-folder> -l <lang-code> [-d debug_en]`

lang-code is ISO639-1 language code for languages [ara, fre, ger, pol, tur]

To extract prosodic parameters (run from main directory):

`./src/batch_f0_parametrization.sh <sentence-segments-output-folder> <lang-code>`

Until here, a monolingual prosodically annotated corpora is created. Repeat these steps for audio and subtitle pair of each language. Then, to create a parallel corpus execute the following:

To find parallel sentences between two monolingual data:

`python src/sentenceMapper.py -e <lang1-sentence-segments-output-folder>/<lang1-code>_sentenceData.csv -s <lang2-sentence-segments-output-folder>/<lang2-code>_sentenceData.csv -o <sentence-mappings-file>`

To reindex and store only parallel sentences:

`./src/createParallelCorpus.sh <lang1-sentence-segments-output-folder> <lang2-sentence-segments-output-folder> <sentence-mappings-file> <parallel-db-folder> <parallel-data-textdump>`

Sample data is placed in `example` directory. Run `example-run.sh` to test the system on the example data.

## Disclaimer

`lib/cmdautomated_ProsodyPro.praat` is developed by Yi Xu

`lib/xml2textgrid_v2.pl` is developed by Yvan Josse and revised by Iván Latorre & Mónica Domínguez

Sample movie data in example directory is from the film "The Man Who Knew Too Much" (1956) from Universal Pictures

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
