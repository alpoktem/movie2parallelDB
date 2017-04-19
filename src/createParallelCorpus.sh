en_clips_dir=$1
es_clips_dir=$2
mappings_file=$3
output_dir=$4
txt_out=$5

en_out_dir=$output_dir/lang1
es_out_dir=$output_dir/lang2

echo Restructuring parallel sentence files to directory $output_dir

if [ ! -d $en_out_dir ]; then
  mkdir -p $en_out_dir;
fi

if [ ! -d $es_out_dir ]; then
  mkdir -p $es_out_dir;
fi

echo -e "PAIR.ID\tLANG1\tLANG2"> $txt_out

pair_index=0
while read pair; do
	if [ $pair_index = 0 ]; then
		let pair_index=pair_index+1
		continue
	fi
	set -- $pair
	es_id=$1
	en_id=$2
	score=$3
	#echo READ: ES:$es_id EN:$en_id $score

	en_txt="$en_id.subtext"
	es_txt="$es_id.subtext"

	formatted_index=`printf %04d ${pair_index%.*}`

	for file in `ls $en_clips_dir/$en_id | grep $en_id`; do
		mkdir -p $en_out_dir/$formatted_index
		cp $en_clips_dir/$en_id/$file $en_out_dir/$formatted_index/$formatted_index-$file
	done

	for file in `ls $es_clips_dir/$es_id | grep $es_id`; do
		mkdir -p $es_out_dir/$formatted_index
		cp $es_clips_dir/$es_id/$file $es_out_dir/$formatted_index/$formatted_index-$file
	done


	echo -e -n "$pair_index\t" >> $txt_out; cat $es_clips_dir/$es_id/$es_txt >> $txt_out; echo -e -n "\t" >> $txt_out; cat $en_clips_dir/$en_id/$en_txt >> $txt_out
	echo >> $txt_out

	let pair_index=pair_index+1
done < $mappings_file

echo Done