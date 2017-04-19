from yandex_translate import YandexTranslate
from optparse import OptionParser
import sys
import subprocess
import os
import credentials
from nltk.tokenize import word_tokenize
import numpy as np

reload(sys)  
sys.setdefaultencoding('utf8')

translate = YandexTranslate(credentials.YANDEX_TRANSLATE_KEY)
METEOR_THRESHOLD = 0.1
PAIR_SEARCH_RANGE = 5  #in seconds

TMP_REFERENCES_FILENAME = 'tmp_references.txt'
TMP_HYPOTHESIS_FILENAME = 'tmp_hypothesis.txt'
METEOR_PATH = '/home/alp/extSW/meteor-1.5/meteor-1.5.jar'

data_es = []
data_en = []
pairs = []  #order: ES-EN
pairsScores = []   #same indexing as pairs

def checkFile(filename):
    if not filename:
        print "%s file not given"%variable
        sys.exit()
    else:
        if not os.path.isfile(filename):
            print "can't find %s"%(filename)
            sys.exit()

def cleanup(filename):
	command = "rm %s"%(filename)
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output, error = process.communicate()


def sendToMeteor(trans, candidates):
	bestIndex = -1
	score = 0
	scores = []

	if len(candidates) == 0:
		return bestIndex, score
	#prepare files to send to METEOR
	f_references = open(TMP_REFERENCES_FILENAME, "w")
	for sentence in candidates:
		f_references.write("%s\n"%(sentence))
	f_references.close()

	f_hypothesis = open(TMP_HYPOTHESIS_FILENAME, "w")
	for i in range(0,len(candidates)):
		f_hypothesis.write("%s\n"%(trans))
	f_hypothesis.close()

	command = "java -Xmx2G -jar %s %s %s -l en -norm -noPunct -q"%(METEOR_PATH, TMP_HYPOTHESIS_FILENAME, TMP_REFERENCES_FILENAME)
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#process = subprocess.Popen(command.split())
	out, err = process.communicate()

	for candidateIndex, candidateScore in enumerate(err.split()):
		scores.append(float(candidateScore))

	bestIndex = np.argmax(scores)
	score = scores[bestIndex]

	#raw_input("Press Enter to continue...")
	cleanup(TMP_REFERENCES_FILENAME)
	cleanup(TMP_HYPOTHESIS_FILENAME)

	return bestIndex, score 

def main(options):
	print("Processing...(this might take a while, insert -d on command to see progress)")
	checkFile(METEOR_PATH)
	#read data to memory
	with open(options.sentenceData_es) as file_es:
		lines = file_es.read().strip().split("\n")
		for line in lines:
			idx, _ , start, dur, sentence, folder_id, audiofile = line.split("\t")
			#print(sentence)
			data_es.append({'id': int(idx), 'start': start, 'duration': dur, 'sentence': sentence, 'folder_id': folder_id})

	with open(options.sentenceData_en) as file_en:
		lines = file_en.read().strip().split("\n")
		for line in lines:
			idx, _ , start, dur, sentence, folder_id, audiofile = line.split("\t")
			#print(sentence)
			data_en.append({'id': int(idx), 'start': start, 'duration': dur, 'sentence': sentence, 'folder_id': folder_id})

	#now go through spanish data and find their correspondings in english subtitles. Put pairs in _pairs_
	last_en = -1
	for entry_es in data_es:
		if options.debug == True: print('--------------------------ES: (' + str(entry_es['id']) + ') ' + entry_es['sentence'] + '--------------------------')
		translated_english = translate.translate(entry_es['sentence'], 'es-en')['text'].pop()
		#tokens_trans = word_tokenize(translated_english)
		candidates = []
		candidateIndexes = []
		#look for the closest sentence in english data within a range
		checkIndex = last_en + 1
		checkTime = float(data_en[checkIndex]['start'])
		while checkTime < float(entry_es['start']) - PAIR_SEARCH_RANGE:
			checkIndex += 1
			if checkIndex < len(data_en):
				checkTime = float(data_en[checkIndex]['start'])
			else:
				break
				last_en = checkIndex

		bestScoreIndex = checkIndex
		bestScore = 0

		#check if it's in +-PAIR_SEARCH_RANGE second range of the current spanish entry
		while float(entry_es['start'])  - PAIR_SEARCH_RANGE <= checkTime and checkTime <= float(entry_es['start']) + PAIR_SEARCH_RANGE:
			if options.debug == True: print('comparing: "' + translated_english + '" - "' + data_en[checkIndex]['sentence'] + '" (' + str(data_en[checkIndex]['id']) + ')')
			#tokens_sub = word_tokenize(data_en[checkIndex]['sentence'])

			candidates.append(data_en[checkIndex]['sentence'])
			#candidateIndexes.append(data_en[checkIndex]['id'])
			candidateIndexes.append(checkIndex)
			checkIndex += 1

			if checkIndex < len(data_en):
				checkTime = float(data_en[checkIndex]['start'])
			else:
				break

		bestIndex, bestScore = sendToMeteor(translated_english, candidates)
		#bestIndex, bestScore = 0, 1.0
		
		if bestScore >= METEOR_THRESHOLD and not bestIndex == -1:
			if options.debug:
				print('winner: ' + candidates[bestIndex]) 
				print('score: ' + str(bestScore))
			new_pair = [entry_es['folder_id'], data_en[candidateIndexes[bestIndex]]['folder_id']]
			addPair(new_pair, bestScore)
		#raw_input("Press Enter to continue...")

	#write pairs and their scores to the output file
	if options.debug:
		print("---RESULT---")
		print("---pairs---")
		print(pairs)
		print("---scores---")
		print(pairsScores)
	pairs2Txt(options.mappingsFile)
	print("Done. Sentence alignment written to...%s"%(options.mappingsFile))
		
def addPair(new_pair, score):
	#check if pair already exists.
	alreadyPaired = False
	for idx, pair in enumerate(pairs):
		if pair[1] == new_pair[1]:
			if options.debug: print('already paired with higher score')
			alreadyPaired = True
			if score > pairsScores[idx]:
				pairs[idx] = new_pair
				pairsScores[idx] = score
				if options.debug: print('old pair replaced with ' + str(new_pair))

	if not alreadyPaired:
		pairs.append(new_pair)
		pairsScores.append(score)
		if options.debug: print('add to pairs: ' + str(new_pair))
	
def pairs2Txt(filename):
	with open(filename, 'w') as datafile:
		datafile.write("ES\tEN\tSimilarity\n")
		for idx, pair in enumerate(pairs):
			datafile.write("%s\t%s\t%s\n"%(pair[0], pair[1], pairsScores[idx] ))
		datafile.close()


if __name__ == "__main__":
    usage = "usage: %prog [-s infile] [option]"
    parser = OptionParser(usage=usage)
    parser.add_option("-e", "--english", dest="sentenceData_en", default=None, help="english sentence data", type="string")
    parser.add_option("-s", "--spanish", dest="sentenceData_es", default=None, help="spanish sentence data", type="string")
    parser.add_option("-o", "--output", dest="mappingsFile", default=None, help="file to output mappings", type="string")
    parser.add_option("-d", "--debug", action="store_true", dest="debug")
    
    (options, args) = parser.parse_args()
    
    main(options)