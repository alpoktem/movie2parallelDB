# -*- coding: utf-8 -*-
from optparse import OptionParser
import os
import sys
import re
import csv
import copy
import shutil
import paths
from datetime import datetime, date, time, timedelta
import pysrt
import nltk
from pydub import AudioSegment
from shutil import copyfile
from proscript.proscript import Word, Proscript, Segment
from proscript.utilities import utils

#CONSTANTS
TIME_ROUNDUP_FOR_AVCONV = 3
TEMP_SUB_WAV_BUFFER = 0.5  
SCRIBE_AVG_SCORE_THRESHOLD = 0.5
SENTENCE_END_BUFFER = 0
END_WORD_MISDETECTION_COMPANSATION = 0.30
MAX_SENTENCE_DURATION = 30.0
MERGE_SEGMENT_MAX_SECONDS = 5.0
SCRIPT_SEARCH_RANGE = 10
SCRIPT_MATCH_THRESHOLD = 0.7
SENTENCE_END_MARKS = ['.', '?', '!', ':', '"']
PUNCTUATION_MARKS = [',', ';', '/', '"']
PUNCTUATION_TRANS = str.maketrans('', '', '!"#$%&\()*+,./:;<=>?@[\\]^_`{|}~')
WAV_BITRATE = 16000
DEFAULT_SPEAKER_ID = "UNKNOWN"
DEFAULT_FILE_ID = "movie"
DELETE_TMP_WAV = False
NO_MFA_RUN = True #For saving time in debugging


'''
Helper function for checking arguments.
'''
def checkArgument(argname, isFile=False, isDir=False, createDir=False, resetDir=False):
	if not argname:
		return False
	else:
		if isFile and not os.path.isfile(argname):
			return False
		if isDir or createDir:
			if not os.path.isdir(argname):
				if createDir:
					print("Creating directory %s"%(argname))
					os.makedirs(argname)
				else:
					return False
			elif resetDir:
				shutil.rmtree(argname)
				print("Creating directory %s"%(argname))
				os.makedirs(argname)
	return True

'''
Guesses encoding of the given file.
'''
def sniff_file_encoding(filepath):
	from chardet.universaldetector import UniversalDetector
	detector = UniversalDetector()
	with open(filepath, 'rb') as f:
		for line in f.readlines():
			detector.feed(line)
			if detector.done: break
	detector.close()
	return detector.result['encoding']
'''
Speech recognition functions. Uses Wit.ai or Google Cloud
'''
def witAiRecognize(segment, WIT_AI_KEY):
	r = sr.Recognizer()
	with sr.AudioFile(segment) as source:
		audio = r.record(source) # read the entire audio file

	result = None
	try:
		result = r.recognize_wit(audio, key=WIT_AI_KEY)
		#print("*** " + r.recognize_wit(audio, key=WIT_AI_KEY))
	except sr.UnknownValueError:
		print("Wit.ai could not understand audio: %s"%segment)
	except sr.RequestError as e:
		print("Could not request results from Wit.ai service; {0}".format(e))

	return result

def googleCloudRecognize(segment_file, recognizer, CREDENTIALS_JSON):
	with sr.AudioFile(segment_file) as source:
		audio = recognizer.record(source) # read the entire audio file

	result = None
	try:
		result = recognizer.recognize_google_cloud(audio, credentials_json=CREDENTIALS_JSON)
	except sr.UnknownValueError:
		print("Google Speech Recognition could not understand audio")
	except sr.RequestError as e:
		print("Could not request results from Google Speech Recognition service; {0}".format(e))

	return result

'''
Cuts audio at given timestamps
'''
def cutAudioWithPydub(audio_segment, start_time, end_time, outputfile, output_audio_format='wav'):
	extract = audio_segment[int(start_time*1000):int(end_time*1000)]
	extract.export(outputfile, format=output_audio_format)

'''
Cuts each segment and outputs as wav+transcript(+proscript) to given directory
'''
def extract_segments_to_disk(proscript, audiofile, output_dir, extract_audio, extract_proscript, file_prefix="", output_audio_format='wav', segments_subdir='segments'):
	segments_output_dir = os.path.join(output_dir, segments_subdir)
	checkArgument(segments_output_dir, createDir = True, resetDir=True)
	if checkArgument(audiofile, isFile=True):
		audio_segment = AudioSegment.from_file(audiofile, format='wav')
	elif extract_audio:
		audio_segment = None
		print("Problem with audio file. Won't extract segments")
	for segment in proscript.segment_list:
		fileId="%s%04d"%(file_prefix, segment.id)
		segmentAudioFile = "%s/%s.wav"%(segments_output_dir, fileId)
		subScriptFile = "%s/%s.txt"%(segments_output_dir, fileId)
		proscriptFile = "%s/%s.csv"%(segments_output_dir, fileId)

		if extract_audio and audio_segment:
			cutAudioWithPydub(audio_segment, segment.start_time, segment.end_time, segmentAudioFile, output_audio_format)
		if extract_proscript:
			segment_proscript = Proscript()
			utils.reset_segment_times(segment, reset_pause_at_beginning_end=False)
			segment_proscript.add_segment(segment)
			segment_proscript.to_csv(proscriptFile, segment_feature_set=['speaker_id'], word_feature_set=['id', "start_time", "end_time", "real_start_time", "real_end_time", "duration", "pause_before", "pause_after", "punctuation_before", "punctuation_after", "f0_mean_hz", "i0_mean_db", "f0_mean", "i0_mean"])

		#write subtitle text to a separate file
		with open(subScriptFile, 'w') as f:
			f.write(segment.transcript)

def extract_proscript_data_to_disk(proscript, output_dir, language, cut_audio_portions = False, extract_segments_as_proscript = False, output_audio_format = 'wav', segments_subdir='segments'):
	#assert if cut_audio portions then proscript.audio is set
	segments_proscript_file = os.path.join(output_dir, "%s.segments-proscript.csv"%(proscript.id))
	proscript.segments_to_csv(segments_proscript_file, ['id', 'start_time', 'end_time', 'speaker_id', 'transcript'], delimiter='|')

	words_proscript_file = os.path.join(output_dir, "%s.words-proscript.csv"%(proscript.id))
	proscript.to_csv(words_proscript_file, segment_feature_set=['speaker_id'], word_feature_set=['id', "start_time", "end_time", "real_start_time", "real_end_time", "duration", "pause_before", "pause_after", "punctuation_before", "punctuation_after", "f0_mean_hz", "i0_mean_db", "f0_mean", "i0_mean"])

	if cut_audio_portions or extract_segments_as_proscript:
		extract_segments_to_disk(proscript, 
								 proscript.audio_file, 
								 output_dir, 
								 extract_audio = cut_audio_portions, 
								 extract_proscript = extract_segments_as_proscript, 
								 file_prefix='%s_%s'%(proscript.id, language), 
								 output_audio_format=output_audio_format,
								 segments_subdir=segments_subdir)


	print("Data extracted to %s."%output_dir)
'''
Converts SubRipTime object to seconds
'''
def subriptime_to_seconds(srTime):
	t = datetime.combine(date.min, srTime.to_time()) - datetime.min
	return t.total_seconds()

'''
All text normalization here
'''
def normalize_transcript(transcript, lang_code):
	if lang_code == 'en' or lang_code == 'eng':
		transcript = re.sub('mr\.', 'mister', transcript, flags=re.IGNORECASE)
		transcript = re.sub('mrs\.', 'mrs', transcript, flags=re.IGNORECASE)
	elif lang_code == 'es' or lang_code == 'spa':
		transcript = re.sub('ud\.', 'usted', transcript, flags=re.IGNORECASE)
		transcript = re.sub('sr\.', 'señor', transcript, flags=re.IGNORECASE)
		transcript = re.sub('sra\.', 'señora', transcript, flags=re.IGNORECASE)
		transcript = re.sub('srta\.', 'señorita', transcript, flags=re.IGNORECASE)
	transcript = re.sub('dr\.', 'doctor', transcript, flags=re.IGNORECASE)

	transcript = re.sub('[#*^+=_@~\|><\}\{]', '', transcript)
	transcript = re.sub('’', "'", transcript)
	transcript = re.sub('"', ' ', transcript)
	transcript = re.sub('\n', ' ', transcript)   #new line to space
	transcript = re.sub(r"(\(|\[)(.|\s)+(\]|\))", "", transcript)	#remove entries with non-speech information such as [LAUGHTER] [MOAN] (HORN HONKING)
	transcript = re.sub(r"-*[A-Z|0-9][A-Z| |0-9]+:", "-", transcript)  #convert speaker tag to dash
	transcript = re.sub('^-', '', transcript)		#remove dash at the beginning
	transcript = re.sub(' -', ' - ', transcript)	#Maintain speech dashes as separate tokens
	transcript = re.sub(r'(\w)-(\w)', r'\1 \2', transcript)
	transcript = re.sub(' +',' ', transcript)  #remove repeating whitespaces
	transcript = transcript.strip()
	transcript = re.sub(',\.\.\.$', ',', transcript)   #convert trailing three dots with comma to only comma
	transcript = re.sub('^\.\.\.', '', transcript)   #remove leading three dots
	return transcript

'''
Returns true if the transcript ends a sentence. 
'''
def check_sentence_end(transcript, three_dots_as_end=False):
	if transcript[-1] in SENTENCE_END_MARKS:
		#check if it's '...' then it might not be a sentence ending
		if check_discontinued_end(transcript):
			return three_dots_as_end
		return True
	else:
		return False

#TODO: return if there's a comma left. Then the segment is continueing in the next entry. 
def check_discontinued_end(transcript):
	if transcript[-1] == '.':
		word_reversed = transcript[::-1]
		if re.search(r"^\W",word_reversed):
			punc = word_reversed[:re.search(r"\w", word_reversed).start()][::-1]
			if punc == '...':
				return True
	return False

'''
Reads subtitle data to proscript segments.
'''
def to_proscript(srt_data, lang_code):
	proscript = Proscript()

	no_sentences = 0 #tmp

	segment_count = 0
	curr_seg_defined = False

	for index, srt_entry in enumerate(srt_data):
		start_time = subriptime_to_seconds(srt_entry.start)
		end_time = subriptime_to_seconds(srt_entry.end)

		transcript = srt_entry.text_without_tags.strip()
		normalized_transcript = normalize_transcript(transcript, lang_code)

		#print("srt:%s"%transcript)
		#print("srt.normal:%s"%normalized_transcript)

		if not curr_seg_defined:
			#print("curr seg not defined")
			if normalized_transcript and not normalized_transcript.isspace():
				curr_seg = Segment()
				curr_seg.speaker_id = DEFAULT_SPEAKER_ID
				curr_seg.start_time = start_time
				curr_seg.end_time = end_time
				curr_seg.transcript += normalized_transcript
				curr_seg_defined = True
				#print("new curr_seg: %s"%curr_seg.transcript)
			else:
				pass
				#print("no info in srt")
		else:
			#print("curr seg defined")
			if check_sentence_end(curr_seg.transcript, three_dots_as_end=True) or start_time - curr_seg.end_time > MERGE_SEGMENT_MAX_SECONDS:
				#print("----==add.seg==----")
				segment_count += 1
				curr_seg.id = segment_count
				proscript.add_segment(curr_seg)
				#curr_seg.to_string()
				curr_seg_defined = False
				#print("----==added==----")
				if normalized_transcript and not normalized_transcript.isspace():
					curr_seg = Segment()
					curr_seg.speaker_id = DEFAULT_SPEAKER_ID
					curr_seg.start_time = start_time
					curr_seg.end_time = end_time
					curr_seg.transcript += normalized_transcript
					curr_seg_defined = True
					#print("new curr_seg: %s"%curr_seg.transcript)
				else:
					curr_seg_defined = False
					#print("no info in srt")
			elif normalized_transcript and not normalized_transcript.isspace():
				curr_seg.end_time = subriptime_to_seconds(srt_entry.end)
				curr_seg.transcript += ' ' + normalized_transcript
				#print("update curr_seg: %s"%curr_seg.transcript)
			else:
				pass
				#print("Here. seg wasted probably")
		#print("-----")

		if index == len(srt_data) - 1:
			if curr_seg_defined and curr_seg.transcript and not curr_seg.transcript.isspace():
				segment_count += 1
				curr_seg.id = segment_count
				curr_seg.transcript = normalized_transcript
				#print("----==last.add.seg==----")
				proscript.add_segment(curr_seg)
				#curr_seg.to_string()
				#print("----==last.added==----")
	#print("Exiting to_proscript")
	#print("No of segs: %i"%len(proscript.segment_list))
	print("%s|no_sentences|%i"%(lang_code, no_sentences))
	return proscript

'''
Splits segments that have more than one speaker turn.
'''
def split_multispeaker_segments(proscript, default_speaker_id = DEFAULT_SPEAKER_ID):
	proscript.word_list = []
	new_segment_list = []
	for index, segment in enumerate(proscript.segment_list):
		if len(segment.word_list) and segment.transcript:
			transcript_parts = [tr.strip() for tr in segment.transcript.split(' - ')]
			split_at = [0] + segment.needs_split_at + [len(segment.word_list)]
			for split_index in range(len(split_at) - 1):
				try:
					new_segment = Segment()
					new_segment.id = len(new_segment_list) + 1
					new_segment.speaker_id = default_speaker_id
					new_segment.start_time = segment.word_list[split_at[split_index]].start_time
					new_segment.end_time = segment.word_list[split_at[split_index + 1] - 1].end_time
					new_segment.transcript = transcript_parts[split_index]
					new_segment.proscript_ref = proscript
					for word in segment.word_list[split_at[split_index]:split_at[split_index + 1]]:
						new_segment.add_word(word)

					new_segment.word_aligned = True
					new_segment_list.append(new_segment)
				except:
					print("Multispeaker split problem at")
					print(index)
					print(segment.transcript)
					print("Split at:")
					print(split_at)

	proscript.segment_list = new_segment_list   

'''
Merges segments that end with three dots. (If they are of the same speaker)
'''
def merge_discontinued_segments(proscript):
	proscript.word_list = []
	new_segment_list = []
	#iterate thru segments
	segment_index = 0
	new_segment_count = 0
	while segment_index < proscript.get_no_of_segments():
		curr_seg = proscript.segment_list[segment_index]
		new_segment_count += 1
		curr_seg.id = new_segment_count

		#merge following segments as long as they end with ...
		merge_index = 1
		while check_discontinued_end(curr_seg.transcript) and segment_index + merge_index < proscript.get_no_of_segments() and proscript.segment_list[segment_index].speaker_id == proscript.segment_list[segment_index + merge_index].speaker_id:
			segment_to_merge = proscript.segment_list[segment_index + merge_index]
			curr_seg.transcript += " " + segment_to_merge.transcript
			curr_seg.end_time = segment_to_merge.end_time
			curr_seg.word_list += segment_to_merge.word_list
			merge_index += 1

		new_segment_list.append(curr_seg)
		segment_index += merge_index

	proscript.segment_list = new_segment_list
	proscript.repopulate_word_list()
	return 1

'''
Helper functions for getting speaker information in transcript
'''
def get_list_intersection(list_a, list_b):
	intersection = []
	list_b_copy = copy.copy(list_b)
	for item in list_a:
		if item in list_b_copy:
			intersection.append(item)
			list_b_copy.remove(item)
	return intersection

def remove_list_from_list(aList, removeList):
	for item in removeList:
		if item in aList:
			aList.remove(item)
	return aList

'''
Reads movie transcript to memory. Returns each line tokenized and plain with aligned speaker list.
Transcript format: 
SPEAKER X: Line...
'''
def read_movie_transcript(scriptfile):
	script_data = []
	script_speaker_data = []
	with open(scriptfile, encoding="utf-8") as file:
		for line in file:
			if re.match(r"^[a-z|A-Z|\s|\.|\(|\)|0-9]*:.+", line):
				speaker = line[:line.find(":")]
				script = line[line.find(":") + 1:]
				
				#print(speaker)
				script = re.sub('^\s|"|\.\.\.', '', script)
				script = re.sub('’', "'", script)
				script = script.strip()
				#print(script)
				if not len(script_speaker_data) == 0 and speaker == script_speaker_data[-1]:
					script_data[-1] += " " + script
				else:
					script_data.append(script)
					script_speaker_data.append(speaker)
	#Mark subtitled segments in speaker name
	for index, (speaker_name, script) in enumerate(zip(script_speaker_data, script_data)):
		if "(subtitled)" in script:
			script_speaker_data[index] = speaker_name + " (SUBTITLED)"

	script_data_list = [nltk.word_tokenize(script_transcript.translate(PUNCTUATION_TRANS).lower()) for script_transcript in script_data]
	return script_data_list, script_speaker_data, script_data

'''
Aligns proscript segments with movie transcript and gets speaker info.
'''
def get_speaker_info_from_transcript(proscript, scriptfile):
	script_data_list, script_speaker_data, script_data = read_movie_transcript(scriptfile)

	index_segment = 0
	index_script = 0
	last_matched_script_index = 0
	while index_segment < proscript.get_no_of_segments() and index_script < len(script_data_list):
		curr_seg = proscript.segment_list[index_segment]
		entry_segment_list = nltk.word_tokenize(curr_seg.transcript.translate(PUNCTUATION_TRANS).lower())
		entry_script_list = script_data_list[index_script]

		#print("seg:%s"%entry_segment_list)
		#print("scr:%s"%entry_script_list)
		intersecting = get_list_intersection(entry_segment_list, entry_script_list)
		no_of_intersecting = len(intersecting)
		#print("%i/%i intersects"%(no_of_intersecting, len(entry_segment_list)))  
		meh = False
		if no_of_intersecting >= len(entry_segment_list) * SCRIPT_MATCH_THRESHOLD:
			#print("match")
			#print("seg(%i):%s\nscr(%i):%s"%(index_segment, curr_seg.transcript, index_script, script_data[index_script]))
			curr_seg.speaker_id = script_speaker_data[index_script]
			remove_list_from_list(entry_script_list, intersecting)
			script_data_list[index_script] = entry_script_list

			index_segment += 1
			last_matched_script_index = index_script
		else:
			#print("meh")
			#print("seg(%i):%s\nscr(%i):%s"%(index_segment, curr_seg.transcript, index_script, script_data[index_script]))
			meh = True
			curr_seg.speaker_id = DEFAULT_SPEAKER_ID
		if len(entry_script_list) == 0 or meh:
			index_script += 1
		if index_script - last_matched_script_index >= SCRIPT_SEARCH_RANGE:
			#print(">>>go back to last match. skip segment.")
			index_segment += 1
			index_script = last_matched_script_index
		#print("---")

	proscript.populate_speaker_ids()
	return 1

'''
Fills task list from a file with tab separated info: file id, audio file, srt file, script file, language
'''
def fill_task_list_from_file(file_list_file, output_dir):
	task_list = []
	if not checkArgument(file_list_file, isFile=True):
		print("File list file doesn't exist")

	with open(file_list_file) as f:
		for line in f:
			if line and not line.isspace() and not line.startswith('#'):
				file_id = line.split('\t')[0]
				file_in_audio = line.split('\t')[1].strip()
				file_in_srt = line.split('\t')[2].strip()
				file_in_script = line.split('\t')[3].strip()
				file_lang = line.split('\t')[4].strip()
				if checkArgument(file_in_audio, isFile=True):
					if checkArgument(file_in_srt, isFile=True):
						file_output_dir = os.path.join(output_dir, file_id, file_lang)
						checkArgument(file_output_dir, isDir=True, createDir=True)
						task_list.append({'file_id': file_id, 'file_in_audio':file_in_audio, 'file_in_srt':file_in_srt, 'file_in_script':file_in_script, 'output_dir':file_output_dir, 'lang':file_lang})	
					else:
						print("srt file %s doesn't exist"%(file_in_srt))
				else:
					print("audio file %s doesn't exist"%(file_in_audio))
	return task_list

'''
Fills task list from given arguments
'''
def fill_task_list(file_id, audio_file, sub_file, script_file, output_dir, lang):
	if not checkArgument(audio_file, isFile=True):
		print("audio file doesn't exist")
	if not checkArgument(sub_file, isFile=True):
		print("subtitle file doesn't exist")
	checkArgument(output_dir, isDir=True, createDir=True)
	task_list = {'file_id': file_id, 'file_in_audio':audio_file, 'file_in_srt':sub_file, 'file_in_script':script_file, 'output_dir':output_dir, 'lang':lang}
	return [task_list]

'''
Uses all info to create proscript. Stores in files. Extracts each segment to separate wav files
'''
def process_movie(movieid, audiofile, subfile, scriptfile, outdir, movielang, input_audio_format, transcribe_dub = False, cut_audio_portions=False, extract_segments_as_proscript = False, skip_mfa=False):
	print("Audio: %s\nSubtitles: %s\nLanguage: %s\nTranscript: %s"%(audiofile, subfile, movielang, scriptfile))
	print("Reading subtitles...", end="")
	srt_encoding = sniff_file_encoding(subfile)
	print(" (encoding: %s) ..."%srt_encoding, end="")
	srtData = pysrt.open(subfile, encoding=srt_encoding)
	print("done")

	#Audio file needs to be stored as wav in the output folder temporarily
	print("Copying audio as wav...", end="")
	audio = AudioSegment.from_file(audiofile, format=input_audio_format)
	audio = audio.set_channels(1)
	tmp_audiopath = os.path.join(outdir, movieid + '_' + movielang + '.wav')
	cutAudioWithPydub(audio, 0, subriptime_to_seconds(srtData[-1].end), tmp_audiopath)
	print("done")

	print("Creating proscript...")
	movie_proscript = to_proscript(srtData, movielang)
	movie_proscript.id = movieid + "_" + movielang
	movie_proscript.audio_file = tmp_audiopath
	movie_proscript.duration = audio.duration_seconds

	if skip_mfa:
		print("Reading TextGrid...")
		utils.proscript_segments_to_textgrid(movie_proscript, outdir, file_prefix="%s_%s"%(movieid, movielang), speaker_segmented=False, no_write=True)
		utils.get_word_features_from_textgrid(movie_proscript)
	else:
		print("Creating TextGrid...")
		utils.proscript_segments_to_textgrid(movie_proscript, outdir, file_prefix="%s_%s"%(movieid, movielang), speaker_segmented=False)
		print("Running forced alignment...")
		if movielang == 'eng':
			utils.mfa_word_align(outdir,  transcript_type="TextGrid", mfa_align_binary=paths.MFA_ALIGN_BINARY, lexicon=paths.MFA_LEXICON_ENG, language_model=paths.MFA_LM_ENG)
		elif movielang == 'spa':
			utils.mfa_word_align(outdir,  transcript_type="TextGrid", mfa_align_binary=paths.MFA_ALIGN_BINARY, lexicon=paths.MFA_LEXICON_SPA, language_model=paths.MFA_LM_SPA)
		utils.get_word_features_from_textgrid(movie_proscript, prosody_tag=True, praat_binary=paths.PRAAT_BINARY)

	split_multispeaker_segments(movie_proscript, default_speaker_id = DEFAULT_SPEAKER_ID)
	print("Getting speaker information...")
	if scriptfile and not scriptfile == "NA":
		get_speaker_info_from_transcript(movie_proscript, scriptfile)

	# #merge_discontinued_segments(movie_proscript)
	utils.assign_word_ids(movie_proscript)

	
	#STORE DATA TO DISK
	extract_proscript_data_to_disk(movie_proscript, outdir, movielang, cut_audio_portions = cut_audio_portions, extract_segments_as_proscript = extract_segments_as_proscript, output_audio_format = 'wav')

	if DELETE_TMP_WAV:
		os.remove(tmp_audiopath)

	return movie_proscript

def process_tasks(task_list, input_audio_format, transcribe_dub = False, cut_audio_portions = False, extract_segments_as_proscript = False, skip_mfa=False):
	#Process files
	for task in task_list:
		movieid = task['file_id']
		audiofile = task['file_in_audio']
		subfile = task['file_in_srt']
		outdir = task['output_dir']
		movielang = task['lang']
		scriptfile = task['file_in_script']

		yield process_movie(movieid, audiofile, subfile, scriptfile, outdir, movielang, input_audio_format, transcribe_dub, cut_audio_portions, extract_segments_as_proscript, skip_mfa)

def main(options):
	task_list = []
	#Fill task list either from a file or from given audio, subtitle pair
	if options.list_of_files:
		task_list = fill_task_list_from_file(options.list_of_files, options.outdir)
	else:
		task_list = fill_task_list(DEFAULT_FILE_ID, options.audiofile, options.subfile, options.scriptfile, options.outdir, options.movielang)

	#Process all files in task list
	for movie_proscript in process_tasks(task_list, options.audioformat, options.transcribe_dub, cut_audio_portions=True, extract_segments_as_proscript = True, skip_mfa=options.skip_mfa):
		print("Processed %s"%movie_proscript.id)
	
if __name__ == "__main__":
	usage = "usage: %prog [-s infile] [option]"
	parser = OptionParser(usage=usage)
	parser.add_option("-i", "--filelist", dest="list_of_files", default=None, help="list of files to process. Each line with id, wav, xml, lang (tab separated)", type="string")	
	parser.add_option("-a", "--audiofile", dest="audiofile", default=None, help="movie audio file to be segmented", type="string")
	parser.add_option("-s", "--sub", dest="subfile", default=None, help="subtitle file (srt)", type="string")
	parser.add_option("-c", "--script", dest="scriptfile", default='NA', help="movie script file with speaker information", type="string")
	parser.add_option("-l", "--lang", dest="movielang", default="", help="Language of the movie audio (Three letter ISO 639-2/T code)", type="string")
	parser.add_option("-o", "--output-dir", dest="outdir", default=None, help="Directory to output segments and sentences", type="string")
	parser.add_option("-t", "--transcribe", dest="transcribe_dub", action="store_true", default=False, help="send dubbed audio segments to wit.ai")
	parser.add_option("-f", "--audioformat", dest="audioformat", default="mp3", help="Audio format (wav, mp3 etc.)", type="string")
	parser.add_option("-m", "--skip_mfa", dest="skip_mfa", default=False, action="store_true", help='Flag to take already made word aligned textgrid in output folder')



	(options, args) = parser.parse_args()

	main(options)