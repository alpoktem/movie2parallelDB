# -*- coding: utf-8 -*-
from optparse import OptionParser
import os
import sys
import re
import subprocess
import csv
import cPickle
import xml.etree.ElementTree as ET
import credentials
from nltk.tokenize import RegexpTokenizer
from datetime import *

#CONSTANTS
TIME_ROUNDUP_FOR_AVCONV = 3
TEMP_SUB_WAV_BUFFER = 0.5  
SCRIBE_AVG_SCORE_THRESHOLD = 0.5
SENTENCE_END_BUFFER = 0
END_WORD_MISDETECTION_COMPANSATION = 0.30
MAX_SENTENCE_DURATION = 15.0
SENTENCE_END_MARKS = ['.', '?', '!', ':', '...']
PUNCTUATION_MARKS = [',', ';', '/', '"']
WAV_BITRATE = 16000

AVCONV_LOC = "avconv"

temptextfile="tmp_subtext.txt"
tempwavfile="tmp_subaudio.wav"
tempscribefile="tmp_scribe.xml"

def readSrt(subfile):
	'''
	read srt file line by line, each entry (seperated by empty line) has 4 lines:
	1 - entry id --> stored as id in dict
	2 - time values --> processed and stored as start and dur in dict
	3 - subtitle line 1 --> stored as line1 in dict
	4 - subtitle line 2 --> stored as line2 in dict
	'''
	subData = []
	
	with open(subfile) as f:
		lines = f.read().decode("utf-8-sig").encode("utf-8").splitlines()
		linetype=1		#1-id, 2-timestamps, 3..-text
				
		subEntry = {'id':0, 'start':"", 'end':"", 'duration':"", 'textline1':"", 'textline2':"", 'subtext':""}
		for line in lines:
			#print(line, linetype)
			if not line:
				subEntry['subtext'] = subEntry['subtext'][1:]   #take out the extra whitespace at the beginning
				#print(subEntry['subtext'])
				subData.append(subEntry)
				subEntry = {'id':0, 'start':"", 'end':"", 'duration':"", 'textline1':"", 'textline2':"", 'subtext':""}
				linetype=1
				continue
			elif linetype==1:
				subEntry['id']=line		
				linetype=linetype+1;
			elif linetype==2: 
				timestamp=line
				 
				[startstamp, endstamp] = timestamp.split(" --> ")
				[startstamp, endstamp] = [startstamp.replace(",", ":"), endstamp.replace(",", ":")]
				[s_hour,s_min,s_sec,s_mil]=startstamp.split(':')
				[e_hour,e_min,e_sec,e_mil]=endstamp.split(':')

				t_end = time(int(e_hour),int(e_min),int(e_sec),int(e_mil)*1000)
				dt_end = datetime.combine(date.today(), t_end)

				delta_start = timedelta(hours=int(s_hour), minutes=int(s_min), seconds=int(s_sec), microseconds=int(s_mil)*1000)

				t_dur = (dt_end - delta_start).time()
				[dur_sec, dur_mil] = [t_dur.second, t_dur.microsecond/1000]
				
				#NOTE: system call will be --> avconv -i audio -ss s_hour:s_min:s_sec.s_mil -t s.mmm -ac 1 -ar 16000 <output-dir>id.wav
				
				subEntry['start'] = "%s:%s:%s.%s"%(s_hour, s_min, s_sec, s_mil)
				subEntry['end'] = "%s:%s:%s.%s"%(e_hour, e_min, e_sec, e_mil)
				subEntry['duration'] = "%i.%i"%(dur_sec, dur_mil)

				subEntry['startSecs'] = round(timestamp2secs(startstamp),TIME_ROUNDUP_FOR_AVCONV)
				subEntry['endSecs'] = round(timestamp2secs(endstamp),TIME_ROUNDUP_FOR_AVCONV)
				subEntry['durSecs'] = round(subEntry['endSecs'] - subEntry['startSecs'],TIME_ROUNDUP_FOR_AVCONV)
				#print"start:%f, end:%f, dur:%f"%(subEntry['startSecs'], subEntry['endSecs'], subEntry['durSecs'])
				linetype=3
			else:
				subEntry['subtext'] += ' ' + line
			# elif linetype==3:
			# 	subEntry['textline1']=line
			# 	linetype=4
			# elif linetype==4:
			# 	subEntry['textline2']=line
			#print(subEntry)
	return subData

def timestamp2secs(timestamp):
	#converts timestamp in hh:mm:ss:mmm form to s.mmm
	[s_hour,s_min,s_sec,s_mil]=timestamp.split(':')
	#print"%s,%s,%s,%s"%(s_hour,s_min,s_sec,s_mil)
	seconds=int(s_hour)*60*60 + int(s_min)*60 + int(s_sec)
	milliseconds=float(s_mil)*0.001
	return seconds+milliseconds

def isSentenceEndMark(text):
    text_stripped = text.strip()
    if text_stripped in SENTENCE_END_MARKS:
        return True
    else:
        return False

def isPunctuationMark(text):
    text_stripped = text.strip()
    if text_stripped in PUNCTUATION_MARKS:
        return True
    else:
        return False

def cleanSrtData(srtData):
	#preprocesses raw subtitle data
	for i in reversed(range(len(srtData))):
		entry = srtData[i]
		#1 - remove entries with non-speech information such as [LAUGHTER] [MOAN] (HORN HONKING)
		if re.search(r"(\(|\[)(.|\s)+(\]|\))", entry['subtext']):
			del srtData[i]

		#2 - take out informative marks
		if re.search(r"<.+>", entry['subtext']):
			entry['subtext'] = re.sub(r"<[a-z]>|</[a-z]>", "", entry['subtext'])

		#3 - clear speech dashes (happens when two speakers speak in the same sub entry)
		if re.match(r"^-.*", entry['subtext']):
			entry['subtext'] = re.sub(r"-\s", "", entry['subtext'])

		#4 - clear names from beginning (i.e. DON: blablabla)
		if re.search(r"[^|^-].+:", entry['subtext']):
			entry['subtext'] = re.sub(r"^.*:\s", "", entry['subtext'])

		#5 - take out the dots in Mr. Mrs. Dr. Ms. 
		entry['subtext'] = re.sub(r"Dr(\.\s|\s)", "Doctor ", entry['subtext'])
		if options.movielang == "eng":
			entry['subtext'] = re.sub(r"Mr(\.\s|\s)", "Mister ", entry['subtext'])
			entry['subtext'] = re.sub(r"Mrs(\.\s|\s)", "Mrs ", entry['subtext'])
			entry['subtext'] = re.sub(r"Ms(\.\s|\s)", "Miss ", entry['subtext'])
		if options.movielang == "spa":
			entry['subtext'] = re.sub(r"Sr(\.\s|\s)", "Señor ", entry['subtext'])
			entry['subtext'] = re.sub(r"Sra(\.\s|\s)", "Señora ", entry['subtext'])
			entry['subtext'] = re.sub(r"Ud(\.\s|\s)", "usted ", entry['subtext'])
			entry['subtext'] = re.sub(r"Uds(\.\s|\s)", "ustedes ", entry['subtext'])
	return srtData

def checkFile(filename, variable):
    if not filename:
        print "%s file not given"%variable
        sys.exit()
    else:
        if not os.path.isfile(filename):
            print "%s file %s does not exist"%(variable, filename)
            sys.exit()

def checkFolder(dir):
	if not os.path.exists(dir):
		print "Creating folder ./%s"%(dir)
		os.makedirs(dir)	

def segmentSentences(sentenceData):
	#segments audio according to SENTENCE time values in sentenceData
	
	count = 0
	for entry in sentenceData:
		fileId="%s%04d"%(options.movielang, int(entry['id']))
		output_path = os.path.join(options.outdir, fileId)
		if not os.path.exists(output_path):
			os.makedirs(output_path)
		
		segmentAudioFile = "%s/%s.wav"%(output_path, fileId)	
		print"Segmenting sentence %s to %s..."%(entry['id'], segmentAudioFile)
		#call avconv to segment the subtitle time
		cutAudioWithAvconv(options.audio, entry['start'], entry['duration'], segmentAudioFile)

		entry['fileId'] = fileId
		entry['fileName'] = segmentAudioFile

		#write subtitle text to a textfile (includes punctuation)
		subtext = entry['sentence'].encode('utf8')
		segmentTextFile="%s/%s.subtext"%(output_path, fileId)
		f_s = open(segmentTextFile, "w")
		f_s.write(subtext)
		f_s.close()

		#write raw speech to a textfile
		rawtext = subTextToRawText(subtext)
		
		#print(rawtext)
		segmentRawTextFile="%s/%s.rawtext"%(output_path, fileId)
		f_r = open(segmentRawTextFile, "w")
		f_r.write(rawtext)
		f_r.close()
		
def subTextToRawText(text):
	tokenizer = RegexpTokenizer(r'[\w|\']+')
	tokens = tokenizer.tokenize(text)

	#form string while converting numbers to text
	rawtext = ""
	for token in tokens:
		if re.match(r"[0-9]+", token):
			rawtext += int2word(token)
		else:
			rawtext += token + " "

	rawtext = rawtext[:-1]
	return rawtext

def cutAudioWithAvconv(audioFilename, start_time, cut_duration, outputAudioFilename):
	#if output file already exists, delete it
	if os.path.isfile(outputAudioFilename):
		os.remove(outputAudioFilename)
	command = "%s -i %s -ss %s -t %s -ac 1 -ar %s %s"%(AVCONV_LOC, audioFilename, start_time, cut_duration, WAV_BITRATE, outputAudioFilename)
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()

def checkIfAvconvInstalled():
	command = "%s"%(AVCONV_LOC)
	try:
		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output, error = process.communicate()
	except:
		print("avconv software not found. Either install it or set the AVCONV_LOC variable to its correct path.")
		sys.exit()

def getWordAlignmentFromScribe(audiofile, transcriptfile, outputfile, language):
	command = "curl -ksS -u %s:%s https://rest1.vocapia.com:8093/voxsigma -F method=vrbs_align -F model=%s -Faudiofile=@%s -Ftextfile=@%s"%(credentials.SCRIBE_USERNAME, credentials.SCRIBE_PASSWORD, language, audiofile, transcriptfile)
	try:
		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output, error = process.communicate()
	except:
		print("Cannot connect to Scribe. Check credentials in credentials.py.")
		sys.exit()
	fs = open(outputfile, "w")
	fs.write(output)
	fs.close()

def subData2sentences(srtData):
	sentenceData = []
	sentenceNo = 0

	#FIRST PASS: Split subtitle entries with text belonging to separate sentences
	for i in range(len(srtData)):
		entry = srtData[i]
		#There are two sentences in one sub entry if the first line ends with a sentence ending punctuation(.|!|?|...) and there's a second line.

		#create a temporary text file for the transcription of the audio tmp_scribefile.txt
		ft = open(temptextfile, "w")
		ft.write("%s"%(entry['subtext']))
		ft.close()

		#create a temporary audio file of the subtitle segment +0.2 sec on begin and end
		cutstart = entry['startSecs'] - TEMP_SUB_WAV_BUFFER
		cutdur = entry['durSecs'] + TEMP_SUB_WAV_BUFFER*2
		cutAudioWithAvconv(options.audio, cutstart, cutdur, tempwavfile)

		#call vocapia scriber and write its output to tempscribefile
		getWordAlignmentFromScribe(tempwavfile, temptextfile, tempscribefile, options.movielang)

		#parse scribe file, output sentences
		parseError = 0
		try:
			xmltree = ET.parse(tempscribefile).getroot()
		except ET.ParseError:
			print "Can't parse scribe output, skipping sentence."
			parseError = 1
    	
		if not parseError:
			sentenceEntry = {'id':0, 'start':0.0, 'end':0.0, 'duration':0.0, 'sentence':"", 'subId': entry['id'], 'fileId':0, 'fileName':""}
			misdetected_words_error = 0.0
			for speechseg in xmltree.findall('SegmentList/SpeechSegment'):
				sentenceConfScoreTotal = 0.0   #for checking quality of scribe
				noOfWordsInSentence = 0
				for wordelem in speechseg:
					if isSentenceEndMark(wordelem.text) and noOfWordsInSentence > 0:   #sentence end
						sentenceEntry['sentence'] += wordelem.text[1:]
						sentenceEntry['duration'] = round(float(wordelem.attrib['stime']) - sentenceEntry['start'] + misdetected_words_error, TIME_ROUNDUP_FOR_AVCONV)
						sentenceEntry['end'] = round(sentenceEntry['start'] + sentenceEntry['duration'] + cutstart, TIME_ROUNDUP_FOR_AVCONV)
						sentenceEntry['start'] += round(cutstart, TIME_ROUNDUP_FOR_AVCONV) #add the starttime of the subtitle 
						
						sentenceConfScore = sentenceConfScoreTotal / noOfWordsInSentence
						if sentenceEntryOK(sentenceEntry, sentenceConfScore):
							
							sentenceEntry['id'] = sentenceNo
							#print "%d - %s"%(sentenceNo, sentenceEntry['sentence'])
							sentenceData.append(sentenceEntry)
							sentenceNo += 1

						sentenceEntry = {'id':0, 'start':0.0, 'end': 0.0, 'duration':0.0, 'sentence':"", 'subId': entry['id'], 'fileId':0, 'fileName':""}
						misdetected_words_error = 0.0
						sentenceConfScoreTotal = 0.0
						noOfWordsInSentence = 0
					else:
						#if first word (sentence empty) set starttime
						if not sentenceEntry['sentence']:
							sentenceEntry['start'] = round(float(wordelem.attrib['stime']), TIME_ROUNDUP_FOR_AVCONV)
						sentenceEntry['sentence'] += wordelem.text[1:]
						noOfWordsInSentence += 1
						if not isPunctuationMark(wordelem.text[1:]):
							sentenceConfScoreTotal += float(wordelem.attrib['conf'])
						#sometimes only the last words in a sentence are not recognized well by the scriber and their durations are detected as 0. 
						#To compansate this for each word with duration 0 we add 0.25 (average word length) for each misdetected word to the duration of the sentence at the end.
						if re.match(r'\s[A-Z|a-z|0-9]+\s', wordelem.text) and wordelem.attrib['dur'] == "0.00":
							misdetected_words_error += END_WORD_MISDETECTION_COMPANSATION
						else:
							misdetected_words_error = 0.00

			#if no sentence end is met and at end of subtitle			
			if sentenceEntry['sentence']:
				sentenceEntry['duration'] = round(float(wordelem.attrib['stime']) - sentenceEntry['start'] + misdetected_words_error, TIME_ROUNDUP_FOR_AVCONV)
				sentenceEntry['end'] = round(float(wordelem.attrib['stime']) + cutstart, TIME_ROUNDUP_FOR_AVCONV)
				sentenceEntry['start'] += round(cutstart, TIME_ROUNDUP_FOR_AVCONV) #add the starttime of the subtitle 
				
				if sentenceEntryOK(sentenceEntry, sentenceConfScoreTotal / noOfWordsInSentence):
					sentenceNo += 1
					sentenceEntry['id'] = sentenceNo
					sentenceData.append(sentenceEntry)

		#CLEANUP delete temp wav file, temp text file, temp scribe file
		cleanup(tempwavfile, entry['id'])
		cleanup(temptextfile, entry['id'])
		cleanup(tempscribefile, entry['id'])

	#SECOND PASS: Merge sentences that spans over two subtitle entries 
	sentenceDataMerged = []
	i = 0  #index to iterate over sentenceData
	idCount = 1   #new ids for sentences
	while i < len(sentenceData):
		newSEntry = {'id':0, 'start':0.0, 'duration':0.0, 'sentence':"", 'subId':[]}

		text = sentenceData[i]['sentence']
		start = sentenceData[i]['start']
		end = sentenceData[i]['end']
		duration = sentenceData[i]['duration']
		subIds = [sentenceData[i]['subId']]

		#Make sure current sentence is a sentence start (full or partial) - check if it starts with a lowercase
		if not re.search(r'^[a-z]', text):
			#check next sentences
			re.search(r'\s[.|?|!|:]\s$', text)
			connects = not (re.search(r'\s[.|?|!|:]\s$', text) or re.search(r'\s\.\.\.\s$', text))    #connects with the next subtitle if it doesn't end with .|?|!|:...
			j = i+1
			while j < len(sentenceData) and connects:

				nexttext = sentenceData[j]['sentence']
				text += nexttext
				connects = not (re.search(r'\s[.|?|!|:]\s$', text) or re.search(r'\s\.\.\.\s$', text))
				end = sentenceData[j]['end']
				subIds.append(sentenceData[j]['subId'])
				j += 1
				i += 1
			newSEntry['id'] = idCount
			idCount += 1
			newSEntry['start'] = start
			newSEntry['sentence'] = text
			newSEntry['end'] = end
			newSEntry['duration'] = round(end - start, TIME_ROUNDUP_FOR_AVCONV)
			newSEntry['subIds'] = subIds

			sentenceDataMerged.append(newSEntry)
		i += 1

	return sentenceDataMerged

def sentenceData2Txt(sentenceData, filename):
	with open(filename, 'w') as datafile:
		for data in sentenceData:
			datafile.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n"%(data['id'], data['subIds'], data['start'], data['duration'], data['sentence'].encode('utf8'), data['fileId'], data['fileName']))
		datafile.close()

def sentenceEntryOK(sentenceEntry, confScore):
	if sentenceEntry['start'] > 0.0 and sentenceEntry['duration'] > 0.0 and sentenceEntry['duration'] < MAX_SENTENCE_DURATION and confScore >= SCRIBE_AVG_SCORE_THRESHOLD:
		return 1
	else:
		return 0

def cleanup(filename, idx):
	if not options.debugdir:
		os.remove(filename)
	else:
		os.rename(filename, "%s/%i_%s"%(options.debugdir, int(idx), filename))

def int2word(n):
    """
    convert an integer number n into a string of english words
    """
    # break the number into groups of 3 digits using slicing
    # each group representing hundred, thousand, million, billion, ...
    n3 = []
    r1 = ""
    # create numeric string
    ns = str(n)
    for k in range(3, 33, 3):
        r = ns[-k:]
        q = len(ns) - k
        # break if end of ns has been reached
        if q < -2:
            break
        else:
            if  q >= 0:
                n3.append(int(r[:3]))
            elif q >= -1:
                n3.append(int(r[:2]))
            elif q >= -2:
                n3.append(int(r[:1]))
        r1 = r
    
    #print n3  # test
    
    # break each group of 3 digits into
    # ones, tens/twenties, hundreds
    # and form a string
    nw = ""
    for i, x in enumerate(n3):
        b1 = x % 10
        b2 = (x % 100)//10
        b3 = (x % 1000)//100
        #print b1, b2, b3  # test
        if x == 0:
            continue  # skip
        else:
            t = thousands[i]
        if b2 == 0:
            nw = ones[b1] + t + nw
        elif b2 == 1:
            nw = tens[b1] + t + nw
        elif b2 > 1:
            nw = twenties[b2] + ones[b1] + t + nw
        if b3 > 0:
            nw = ones[b3] + "hundred " + nw
    return nw
############# globals ################
ones = ["", "one ","two ","three ","four ", "five ",
    "six ","seven ","eight ","nine "]
tens = ["ten ","eleven ","twelve ","thirteen ", "fourteen ",
    "fifteen ","sixteen ","seventeen ","eighteen ","nineteen "]
twenties = ["","","twenty ","thirty ","forty ",
    "fifty ","sixty ","seventy ","eighty ","ninety "]
thousands = ["","thousand ","million ", "billion ", "trillion ",
    "quadrillion ", "quintillion ", "sextillion ", "septillion ","octillion ",
    "nonillion ", "decillion ", "undecillion ", "duodecillion ", "tredecillion ",
    "quattuordecillion ", "quindecillion", "sexdecillion ", "septendecillion ", 
	"octodecillion ", "novemdecillion ", "vigintillion "]

def main(options):
	checkIfAvconvInstalled()
	checkFile(options.audio,"movie audio")
	checkFile(options.subfile,"subtitle file")
	checkFolder(options.outdir)
	if options.debugdir:
		checkFolder(options.debugdir)

	print "Audio:%s\nSubtitles:%s\nLanguage:%s"%(options.audio, options.subfile, options.movielang)
	print "Reading subtitles...",
	srtData = readSrt(options.subfile)
	srtData = cleanSrtData(srtData)
	
	print "Done reading subtitles"

	print "Extracting sentences...",
	sentenceData = subData2sentences(srtData)
	print"done"
	
	#backup sentenceData
	if options.debugdir:
		dumpSentenceData(sentenceData)

	print "Segmenting sentences..."
	segmentSentences(sentenceData)

	sentenceData2Txt(sentenceData, "%s/%s_sentenceData.csv"%(options.outdir, options.movielang))

def dumpSentenceData(sentenceData):
	with open('%s/sentenceData.pickle'%(options.debugdir), 'wb') as f:
		cPickle.dump(sentenceData, f, cPickle.HIGHEST_PROTOCOL)

if __name__ == "__main__":
    usage = "usage: %prog [-s infile] [option]"
    parser = OptionParser(usage=usage)
    parser.add_option("-a", "--audio", dest="audio", default=None, help="movie audio file to be segmented", type="string")
    parser.add_option("-s", "--sub", dest="subfile", default=None, help="subtitle file (srt)", type="string")
    parser.add_option("-o", "--output-dir", dest="outdir", default=None, help="Directory to output segments and sentences", type="string")
    parser.add_option("-d", "--debug-dir", dest="debugdir", default=None, help="Directory to output temporary files for debugging", type="string")
    parser.add_option("-l", "--lang", dest="movielang", default=None, help="Language of the movie audio (Three letter ISO 639-2/T code)", type="string")

    (options, args) = parser.parse_args()

    main(options)