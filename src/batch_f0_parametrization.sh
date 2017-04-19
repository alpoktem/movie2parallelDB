praat_loc="lib/praat"
xml2textgrid_loc="lib/xml2textgrid_v2.pl"
prosodyPro_script="cmdautomated_ProsodyPro.praat"
prosodyPro_loc="lib/$prosodyPro_script"
credentials_loc="src/credentials.py"



segments_dir=$1	#input directory with wav files and transcriptions
lang=$2


if [ ! -d "$segments_dir" ]; then
	echo "Input directory doesn't exist"
	exit
fi

if [ ! -f "$prosodyPro_loc" ]; then
    echo "cmdautomated_ProsodyPro.praat not found!"
    exit
fi

if [ ! -f "$xml2textgrid_loc" ]; then
    echo "xml2textgrid_v2.pl not found!"
    exit
fi

if [ ! -d "lib" ]; then
	echo "This script should be called from main project directory"
	exit
fi

if [ ! -d "src" ]; then
	echo "This script should be called from main project directory"
	exit
fi

#get credentials for scribe from credentials.py
if [ ! -f "$credentials_loc" ]; then
    echo "$credentials_loc not found!"
    exit
fi

scribe_username=`cat $credentials_loc | grep SCRIBE_USERNAME | cut -f2 -d'"'`
scribe_password=`cat $credentials_loc | grep SCRIBE_PASSWORD | cut -f2 -d'"'`

if [[ -z "$scribe_username" ]]; then 
	echo "scribe username not set in src/credentials.py" 
fi

if [[ -z "$scribe_password" ]]; then 
	echo "scribe password not set in src/credentials.py" 
fi

echo $segments_dir
for segment_dir in `ls -d $segments_dir/*/ | sed 's/\/\//\//g'`; do
	#echo $segment_dir
	base=`echo $segment_dir | rev | cut -f2 -d/ | rev`
	echo $base

	txtfile="$segment_dir${base}.rawtext"
	wavfile="$segment_dir${base}.wav"

	#create alignment file of wav and txt
	vocfile="$segment_dir${base}_wordAlignment.xml"
	curl -ksS -u $scribe_username:$scribe_password https://rest1.vocapia.com:8093/voxsigma -F method=vrbs_align -F model=$lang -Faudiofile=@$wavfile -Ftextfile=@$txtfile > $vocfile 2> $vocfile.err
	echo $vocfile created

	#create textgrid from alignment file
	txtgridfile="$segment_dir${base}.TextGrid"
	perl $xml2textgrid_loc < $vocfile > $txtgridfile
	echo $txtgridfile created

	#run prosodypro with textgrid and wavfile (praat script has to be copied there)
	cp $prosodyPro_loc $segment_dir
	$praat_loc $segment_dir$prosodyPro_script "2. Process all sounds without pause" 1 1 0 0 "repetition_list.txt" 0 ".TextGrid" "SSS" ".wav" "./" "speaker_folders.txt" 75 500 10 100 0 -0.03 0.07 0 1 0 500 250 5 5000
	echo Prosodic parameters extracted for $base
	rm $segment_dir$prosodyPro_script
	echo "--"
done
