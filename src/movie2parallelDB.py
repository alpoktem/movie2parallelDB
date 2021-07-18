import os
import sys
import re
import csv
import copy
import nltk
import string
import unicodedata
from optparse import OptionParser
from datetime import datetime, date, time, timedelta
from proscript.proscript import Word, Proscript, Segment
from proscript.utilities import utils
from subsegment_movie import *
import numpy as np
import nltk.data
from nltk.tokenize.toktok import ToktokTokenizer

MERGED_MATCH_CORRELATION_THRESHOLD = 80.0
SURE_MATCH_CORRELATION_THRESHOLD = 70.0
OK_MATCH_CORRELATION_THRESHOLD = 30.0
PARTIAL_MATCH_CORRELATION_THRESHOLD = 8.0
MAX_MERGE_NO = 3
MAX_SEGMENT_DISTANCE = 10.0 #seconds
MAX_NO_WORDS_IN_SEGMENT = 30

UNK_TOKEN = 'UNKNOWN'

toktok = ToktokTokenizer()
 
tokenizer_es = nltk.data.load('tokenizers/punkt/spanish.pickle')
tokenizer_en = nltk.data.load('tokenizers/punkt/english.pickle')

DEBUG = False

'''
Returns indexes of matching segments in proscripts. Proscript with less segments should be given as first argument (proscript_spa)
'''
def map_segments(proscript_spa, proscript_eng):
	matched = []	#spa-eng
	spa_index = 0
	eng_index = 0
	eng_end = False

	while spa_index < len(proscript_spa.segment_list) and eng_index < len(proscript_eng.segment_list):
		correlation = get_segments_correlation(proscript_spa.segment_list[spa_index], proscript_eng.segment_list[eng_index])
		if correlation >= SURE_MATCH_CORRELATION_THRESHOLD:
			if DEBUG: print("Match (%f) between spa:%i and eng:%i"%(correlation, proscript_spa.segment_list[spa_index].id, proscript_eng.segment_list[eng_index].id))
			matched.append(([spa_index], [eng_index]))
			eng_index += 1
			spa_index += 1
			#break
		elif correlation >= PARTIAL_MATCH_CORRELATION_THRESHOLD:
			if DEBUG: print("Partial Correlation of %i between spa:%i and eng:%i"%(correlation, proscript_spa.segment_list[spa_index].id, proscript_eng.segment_list[eng_index].id))
			#Try merging with the next one and see if it gets better

			match_candidates_eng = [eng_index]
			match_candidates_spa = [spa_index]
			for plus_check in range(1,MAX_MERGE_NO):
				total_no_words = len(proscript_eng.segment_list[eng_index].transcript.split())
				if eng_index + plus_check < len(proscript_eng.segment_list) and proscript_eng.segment_list[eng_index].speaker_id == proscript_eng.segment_list[eng_index + plus_check].speaker_id and proscript_eng.segment_list[eng_index + plus_check].start_time - proscript_eng.segment_list[eng_index + plus_check - 1].end_time <= MAX_SEGMENT_DISTANCE and not total_no_words >= MAX_NO_WORDS_IN_SEGMENT:
					match_candidates_eng.append(eng_index + plus_check)
					total_no_words += len(proscript_eng.segment_list[eng_index + plus_check].transcript.split())
				else:
					break
			for plus_check in range(1,MAX_MERGE_NO):
				total_no_words = len(proscript_spa.segment_list[spa_index].transcript.split())
				if spa_index + plus_check < len(proscript_spa.segment_list) and proscript_spa.segment_list[spa_index].speaker_id == proscript_spa.segment_list[spa_index + plus_check].speaker_id and proscript_spa.segment_list[spa_index + plus_check].start_time - proscript_spa.segment_list[spa_index + plus_check - 1].end_time <= MAX_SEGMENT_DISTANCE and not total_no_words >= MAX_NO_WORDS_IN_SEGMENT:
					match_candidates_spa.append(spa_index + plus_check)
					total_no_words += len(proscript_spa.segment_list[spa_index + plus_check].transcript.split())
				else:
					break

			#populate match candidate list
			match_candidates = []
			for i, a1 in enumerate(match_candidates_spa):
				for j, a2 in enumerate(match_candidates_eng):
					match_candidates.append(([match_candidates_spa[l] for l in range(0, i + 1)],[match_candidates_eng[k] for k in range(0,j + 1)]))

			candidate_scores = []
			best_2_match_index = -1
			best_3_match_index = -1
			if DEBUG: print("candidates")
			for index, candidate in enumerate(match_candidates):
				merged_correlation = get_segments_correlation([proscript_spa.segment_list[spa_index] for spa_index in candidate[0]], 
															   [proscript_eng.segment_list[eng_index] for eng_index in candidate[1]])
				candidate_scores.append(merged_correlation)
				if DEBUG: print("%i-%s - %s:%i"%(index + 1, [proscript_spa.segment_list[spa_index].id for spa_index in candidate[0]], [proscript_eng.segment_list[eng_index].id for eng_index in candidate[1]], merged_correlation))
				if len(candidate[0]) > 2 or len(candidate[1]) > 2:
					if best_3_match_index == -1:
						best_3_match_index = index
					elif merged_correlation > candidate_scores[best_3_match_index]:
						best_3_match_index = index
				elif (len(candidate[0]) > 1  and len(candidate[0]) <= 2) or (len(candidate[1]) > 1  and len(candidate[1]) <= 2):
					if best_2_match_index == -1:
						best_2_match_index = index
					elif merged_correlation > candidate_scores[best_2_match_index]:
						best_2_match_index = index

			best_2_match = match_candidates[best_2_match_index]
			best_3_match = match_candidates[best_3_match_index]
			if DEBUG: print("Best 2 match %i of %i"%(best_2_match_index + 1, len(match_candidates)))
			if DEBUG: print("Best 3 match %i of %i"%(best_3_match_index + 1, len(match_candidates)))

			#Find the best match preferring shorter matches.
			if not best_2_match_index == -1 and candidate_scores[best_2_match_index] >= candidate_scores[0] and candidate_scores[best_2_match_index] >= MERGED_MATCH_CORRELATION_THRESHOLD:
				if DEBUG: print("Merged match (%f) between spa:%s and eng:%s"%(candidate_scores[best_2_match_index], [proscript_spa.segment_list[spa_index].id for spa_index in best_2_match[0]], [proscript_eng.segment_list[eng_index].id for eng_index in best_2_match[1]]))
				matched.append(best_2_match)
				spa_index += len(best_2_match[0])
				eng_index += len(best_2_match[1])
			elif not best_3_match_index == -1 and candidate_scores[best_3_match_index] >= candidate_scores[0] and candidate_scores[best_3_match_index] >= MERGED_MATCH_CORRELATION_THRESHOLD:
				if DEBUG: print("Merged match (%f) between spa:%s and eng:%s"%(candidate_scores[best_3_match_index], [proscript_spa.segment_list[spa_index].id for spa_index in best_3_match[0]], [proscript_eng.segment_list[eng_index].id for eng_index in best_3_match[1]]))
				matched.append(best_3_match)
				spa_index += len(best_3_match[0])
				eng_index += len(best_3_match[1])
			elif candidate_scores[0] >= OK_MATCH_CORRELATION_THRESHOLD:
				if DEBUG: print("OK match (%f) between spa:%s and eng:%s"%(candidate_scores[0], [proscript_spa.segment_list[spa_index].id for spa_index in match_candidates[0][0]], [proscript_eng.segment_list[eng_index].id for eng_index in match_candidates[0][1]]))
				matched.append(match_candidates[0])
				spa_index += 1
				eng_index += 1
			else:
				#merge fail
				if proscript_spa.segment_list[spa_index].start_time < proscript_eng.segment_list[eng_index].start_time:
					if DEBUG: print("Missed SPA segment %i: %s"%(proscript_spa.segment_list[spa_index].id, proscript_spa.segment_list[spa_index].transcript))
					spa_index += 1
				else:
					eng_index += 1
		else:
			#make indexes catch up
			if proscript_spa.segment_list[spa_index].start_time < proscript_eng.segment_list[eng_index].start_time:
				if DEBUG: print("Catch up Missed SPA segment %i: %s"%(proscript_spa.segment_list[spa_index].id, proscript_spa.segment_list[spa_index].transcript))
				spa_index += 1
			else:
				eng_index += 1
		# if eng_end:
		# 	break
	return matched

'''
Outputs mapping to a text file
'''
def mapping_to_file(mapping, file_path, proscript_spa, proscript_eng):
	with open(file_path, "w") as f:
		aligned_segment_index = 1
		for matching_segment_indexes in mapping:
			spa_indexes = [proscript_spa.segment_list[segment_index].id for segment_index in matching_segment_indexes[0]]
			eng_indexes = [proscript_eng.segment_list[segment_index].id for segment_index in matching_segment_indexes[1]]
			spa_transcript = ' '.join([proscript_spa.segment_list[segment_index].transcript for segment_index in matching_segment_indexes[0]])
			eng_transcript = ' '.join([proscript_eng.segment_list[segment_index].transcript for segment_index in matching_segment_indexes[1]])
			f.write("%i:%s-%s:%s|%s\n"%(aligned_segment_index, spa_indexes, eng_indexes, spa_transcript, eng_transcript))
			aligned_segment_index += 1

'''
Outputs mapping to a text file
'''
def mapping_as_tmx(mapping, file_path, proscript_spa, proscript_eng):
	with open(file_path, "w") as f:		
		for matching_segment_indexes in mapping:
			spa_transcript = ' '.join([proscript_spa.segment_list[segment_index].transcript for segment_index in matching_segment_indexes[0]])
			eng_transcript = ' '.join([proscript_eng.segment_list[segment_index].transcript for segment_index in matching_segment_indexes[1]])
			spa_transcript_norm = normalize_string(spa_transcript, 'es')
			eng_transcript_norm = normalize_string(eng_transcript, 'en')

			f.write('\t<tu>\n\t\t<tuv xml:lang="en"><seg>%s</seg></tuv>\n\t\t<tuv xml:lang="es"><seg>%s</seg></tuv>\n\t</tu>\n'%(eng_transcript_norm, spa_transcript_norm))


'''
Text normalization methods
'''
def tokenize_nltk(string, lang, to_lower = False):
    tokens = []
    if lang == 'en':
        for sent in tokenizer_en.tokenize(normalize(string)):
            tokens.extend(toktok.tokenize(sent))
    elif lang == 'es':
        for sent in tokenizer_en.tokenize(normalize(string)):
            tokens.extend(toktok.tokenize(sent))
    return tokens

def normalize(line):
	normalized = re.sub('-', ' - ', line)		#remove dash at the beginning
	return normalized

def normalize_string(string, lang_code):
	return ' '.join(tokenize_nltk(string, 'es'))

'''
Returns the percentage of time correlation between two segment sets
'''
def get_segments_correlation(segments1, segments2):
	if type(segments1) == list:
		segments1_list = segments1
	else:
		segments1_list = [segments1]
	if type(segments2) == list:
		segments2_list = segments2
	else:
		segments2_list = [segments2]
	#print("correlating: %f - %f"%(max(segments1_list[0].start_time, segments2_list[0].start_time), min(segments1_list[-1].end_time, segments2_list[-1].end_time)))
	#print("span: %f - %f"%(min(segments1_list[0].start_time, segments2_list[0].start_time), max(segments1_list[-1].end_time, segments2_list[-1].end_time) ))
	correlating = min(segments1_list[-1].end_time, segments2_list[-1].end_time) - max(segments1_list[0].start_time, segments2_list[0].start_time)
	span = max(segments1_list[-1].end_time, segments2_list[-1].end_time) - min(segments1_list[0].start_time, segments2_list[0].start_time)
	return round(max(0, correlating/span * 100))

def vectorize_sentence(sentence, w2v_model, stopwords = []):
	sentence_tokenized = nltk.word_tokenize(sentence)
	sentence_tokenized = [token for token in sentence_tokenized if token not in stopwords]
	emb_vector_size = w2v_model.layer1_size
	vectorized_sentence = np.zeros(shape = (len(sentence_tokenized), emb_vector_size), dtype='float32')

	for token_index in range(len(sentence_tokenized)):
		token = sentence_tokenized[token_index]
		try:
			word_vector = w2v_model.wv[token]
		except KeyError as e:
			word_vector = w2v_model.wv[UNK_TOKEN]
		vectorized_sentence[token_index] = word_vector

	return np.average(vectorized_sentence, axis=0)

def get_sentence_similarity(sentence_1, sentence_2, w2v_model, stopwords = []):
	vector_1 = vectorize_sentence(sentence_1, w2v_model, stopwords)
	vector_2 = vectorize_sentence(sentence_2, w2v_model, stopwords)

	return np.linalg.norm(vector_1 - vector_2)

def array_to_slice(index_array):
	if len(index_array) == 1:
		return slice(index_array[0], index_array[0] + 1)
	else:
		return slice(index_array[0], index_array[1] + 1)

'''
Creates one segment from a list of adjacent segments given in order in a list
'''
def merge_segments_to_new_segment(segment_list, new_segment_id, new_speaker_id = None, proscript_ref = None):
	assert len(segment_list) > 0, "Given segment list is empty"
	#assert speaker id's are the same
	new_segment = Segment()
	new_segment.id = new_segment_id
	new_segment.start_time = segment_list[0].start_time
	new_segment.end_time = segment_list[-1].end_time
	if new_speaker_id:
		new_segment.speaker_id = new_speaker_id
	else:
		new_segment.speaker_id = segment_list[0].speaker_id
	new_segment.transcript = ' '.join([segment.transcript for segment in segment_list])
	if proscript_ref:
		new_segment.proscript_ref = proscript_ref
	#fill in words
	for segment in segment_list:
		for word in segment.word_list:
			new_segment.add_word(word)
	return new_segment

def get_aligned_proscripts(mapping_list, proscript_spa, proscript_eng, copy_speaker_info_from='0', skip_subtitled_segment = True):
	aligned_proscript_spa = Proscript()
	aligned_proscript_spa.id = proscript_spa.id + "_aligned"
	aligned_proscript_spa.audio_file = proscript_spa.audio_file
	aligned_proscript_spa.duration = proscript_spa.duration

	aligned_proscript_eng = Proscript()
	aligned_proscript_eng.id = proscript_eng.id + "_aligned"
	aligned_proscript_eng.audio_file = proscript_eng.audio_file
	aligned_proscript_eng.duration = proscript_eng.duration

	new_spa_segment_id = 1
	new_eng_segment_id = 1
	for mapping in mapping_list:
		new_segment_eng = merge_segments_to_new_segment( [proscript_eng.segment_list[segment_index] for segment_index in mapping[1]], 
														 new_eng_segment_id, 
														 proscript_ref = aligned_proscript_eng)
		new_segment_spa = merge_segments_to_new_segment( [proscript_spa.segment_list[segment_index] for segment_index in mapping[0]], 
														 new_spa_segment_id, 
														 new_speaker_id = new_segment_eng.speaker_id, 
														 proscript_ref = aligned_proscript_spa)


		if skip_subtitled_segment and 'SUBTITLED' in new_segment_eng.speaker_id:
			print('subtitled found')
			continue

		aligned_proscript_spa.add_segment(new_segment_spa)
		aligned_proscript_eng.add_segment(new_segment_eng)

		new_spa_segment_id += 1
		new_eng_segment_id += 1

	utils.assign_word_ids(aligned_proscript_spa)
	utils.assign_word_ids(aligned_proscript_eng)

	aligned_proscript_spa.populate_speaker_ids()
	aligned_proscript_eng.populate_speaker_ids()

	return aligned_proscript_spa, aligned_proscript_eng

def main(options):
	process_list_eng = fill_task_list_from_file(options.list_of_files_eng, options.output_dir)
	process_list_spa = fill_task_list_from_file(options.list_of_files_spa, options.output_dir)

	assert len(process_list_eng) == len(process_list_spa), "Process lists are not the same length"

	for task_index, (proscript_eng, proscript_spa) in enumerate(zip(process_tasks(process_list_eng, options.input_audio_format, skip_mfa=options.skip_mfa), process_tasks(process_list_spa, options.input_audio_format, skip_mfa=options.skip_mfa))):
		proscript_mapping = map_segments(proscript_spa, proscript_eng)

		aligned_proscript_spa, aligned_proscript_eng = get_aligned_proscripts(proscript_mapping, proscript_spa, proscript_eng)

		aligned_proscript_spa.get_speaker_means()
		aligned_proscript_eng.get_speaker_means()
		utils.assign_acoustic_means(aligned_proscript_spa)
		utils.assign_acoustic_means(aligned_proscript_eng)

		#Determine paths for parallel data
		task_output_path = process_list_eng[task_index]['output_dir']
		parallel_output_path = os.path.join(task_output_path, '..', 'spa-eng')
		checkArgument(parallel_output_path, createDir = True)

		#write mapping to file
		mapping_file_path = os.path.join(parallel_output_path, '%s_mapping.txt'%aligned_proscript_eng.id)
		mapping_to_file(proscript_mapping, mapping_file_path, proscript_spa, proscript_eng)
		mapping_tmx_file_path = os.path.join(parallel_output_path, '%s.tmx'%aligned_proscript_eng.id)
		mapping_as_tmx(proscript_mapping, mapping_tmx_file_path, proscript_spa, proscript_eng)
		print("Mapping extracted to %s"%mapping_file_path)

		print("Spanish audio: %s"%aligned_proscript_spa.audio_file)
		print("English audio: %s"%aligned_proscript_eng.audio_file)

		#generate textgrid files
		utils.proscript_to_textgrid(aligned_proscript_spa, parallel_output_path)
		utils.proscript_to_textgrid(aligned_proscript_eng, parallel_output_path)
		print("Spanish Textgrid: %s"%aligned_proscript_spa.textgrid_file)
		print("English Textgrid: %s"%aligned_proscript_eng.textgrid_file)

		#store aligned proscript data to disk
		extract_proscript_data_to_disk(aligned_proscript_spa, parallel_output_path, 'spa', cut_audio_portions = True, extract_segments_as_proscript = True, output_audio_format = 'wav', segments_subdir='segments_spa')
		extract_proscript_data_to_disk(aligned_proscript_eng, parallel_output_path, 'eng', cut_audio_portions = True, extract_segments_as_proscript = True, output_audio_format = 'wav', segments_subdir='segments_eng')
	
	#merge segments merged in the mapping. output

if __name__ == "__main__":
	usage = "usage: %prog [-s infile] [option]"
	parser = OptionParser(usage=usage)
	parser.add_option("-e", "--filelist-eng", dest="list_of_files_eng", default=None, help="list of files to process in english. Each line with id, audio, xml, lang (tab separated)", type="string")	
	parser.add_option("-s", "--filelist-spa", dest="list_of_files_spa", default=None, help="list of files to process in spanish. Each line with id, audio, xml, lang (tab separated)", type="string")	
	parser.add_option("-o", "--output-dir", dest="output_dir", default=None, help="Output directory", type="string")
	parser.add_option("-f", "--input-audio-format", dest="input_audio_format", default="mp3", help="Audio format (wav, mp3 etc.)", type="string")
	parser.add_option("-m", "--skip-mfa", dest="skip_mfa", default=False, action="store_true", help='Flag to take already made word aligned textgrid in output folder')

	(options, args) = parser.parse_args()
	main(options)