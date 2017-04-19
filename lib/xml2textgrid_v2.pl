#!/usr/bin/perl -w
#===============================================================================
#
#         FILE:  xml2textgrid_v2.pl
#
#        USAGE:  ./xml2textgrid_v2.pl 
#
#  DESCRIPTION:  
#
#      OPTIONS:  ---
# REQUIREMENTS:  ---
#         BUGS:  ---
#        NOTES:  ---
#       AUTHOR:  Yvan Josse (YJ), <josse@vocapia.com>
#      COMPANY:  Vocapia Research, Orsay
#       REVISORS:  Iván Latorre & Mónica Domínguez, <ivan.latorre|monica.dominguez@upf.edu>
#      COMPANY:  Universitat Pompeu Fabra, Barcelona
#      VERSION:  2.0
#      CREATED:  30/03/2016 14:27:27 CEST
#     REVISION:  31/08/2016 16:27:00 CEST
#===============================================================================

use strict;
use warnings;
use utf8;

binmode STDIN, ":utf8";
binmode STDOUT, ":utf8";

my $verbose=0;
my $strict=0;
my $SILTEXT = "SIL";
my $SKIPPED_WORD_ASSIGNED_LENGTH = 0.04;

while(scalar(@ARGV)>0) {
	if($ARGV[0] eq "-v") {
		$verbose=1;
	} elsif($ARGV[0] eq "-s") {
		$strict=0;
	} elsif($ARGV[0] eq "-h") {
		print "usage : 
xml2textgrid [options] < file.xml >file.textgrid

options :
	* -h print this help and exit
	* -s check that the words are in strict chronologic order in the XML. If not, exit with an error message.
	* -v be verbose
";
		exit 0;
	}
	shift @ARGV;
}


my $sigdur=0;
my @intervals;
my $stime_prev = -1;
my $stime_curr = 0;
my $dur_prev = 0;
my $dur_curr = 0;
my $endtime_prev = 0;
my $endtime_curr = 0;
my $text_prev = 0;

my $last_was_word = 0;

while(<STDIN>) {
	chomp;
	if(/<Channel /) {
		if (/sigdur="([0-9\.]+)"/) {
			$sigdur=sprintf("%.03f", $1);
		}
	}
	if(/<Word /) {
		$last_was_word = 1;
		if (/stime="([0-9\.]+)" dur="([0-9\.]+)"/) {
			my $stime_curr = (sprintf "%.02f", $1);
			my $dur_curr = (sprintf "%.02f", $2);
			my $endtime_curr = ($stime_curr + $dur_curr);
			my $text_curr = 0;


			#temporary crutch for misdetected words
			#if ($dur_curr == 0){
			#	$dur_curr == 0.1
			#}

			if (/> ([^\ ]+) </) {
				$text_curr = $1;
			} else {
				print STDERR "fatal error : no word found line $.\n";
				exit 1;
			}

			if ($stime_prev != -1){
				if (($stime_prev != $stime_curr)){

					
					if (($stime_curr - $endtime_prev < 0.001)){
						push @intervals, {"xmin", $stime_prev, "xmax", $endtime_prev, "text", $text_prev};

						if ($verbose==1) {
							printf STDERR "PUSH: %.03f %.03f %s\n", $stime_prev, $stime_curr, $text_prev;
						}
					} else {
						push @intervals, {"xmin", $stime_prev, "xmax", $endtime_prev, "text", $text_prev};
						push @intervals, {"xmin", $endtime_prev, "xmax", $stime_curr, "text", $SILTEXT};
						
						if ($verbose==1) {
							printf STDERR "PUSH: %.03f %.03f %s\n", $stime_prev, $endtime_prev, $text_prev;
							printf STDERR "PUSH: %.03f %.03f %s\n", $endtime_prev, $stime_curr, $SILTEXT;
						}
					}

					
				} elsif (($stime_prev == $stime_curr)) {
					#buraya bi if ekle. eger text uzunlugu 2 charaterden kucukse sabit, degilse ortasini koysun
					#$stime_curr = $stime_prev + $SKIPPED_WORD_ASSIGNED_LENGTH;
					$stime_curr = ($stime_prev + $endtime_curr) / 2;
					push @intervals, {"xmin", $stime_prev, "xmax", $stime_curr, "text", $text_prev};
					if ($verbose==1) {
						printf STDERR "YUTUYODU PUSH: %.03f %.03f %s\n", $stime_prev, $stime_curr, $text_prev;
					}
				} else {
					printf STDERR "Somethings wrong";
				}

			} else{
				$stime_curr = "0.00";
			}
			if ($stime_curr == $sigdur){
				last;
			}
			$text_prev = $text_curr;
			$stime_prev = $stime_curr;
			$dur_prev = $dur_curr;
			$endtime_prev = $endtime_curr;
		}
	} elsif (($last_was_word == 1 )) {
		$last_was_word = 0;

		push @intervals, {"xmin", $stime_prev, "xmax", $endtime_prev, "text", $text_prev};

		if ($verbose==1) {
			printf STDERR "LAST PUSH: %.03f %.03f %s\n", $stime_prev, $endtime_prev, $text_prev;
		}
	}


}

my $buffer=sprintf("File type = \"ooTextFile\"
Object class = \"TextGrid\"

xmin = 0
xmax = %.03f
tiers? <exists>
size = 1
item []:
\titem [1]:
\t\tclass = \"IntervalTier\" 
\t\tname = \"words\" 
\t\txmin = 0 
\t\txmax = %.03f
\t\tintervals: size = %d
", $intervals[$#intervals]->{"xmax"},  $intervals[$#intervals]->{"xmax"}, scalar(@intervals));

if ($verbose==1) {
	printf STDERR "num interval: %d\n", scalar(@intervals);
}

for (my $i=0;$i<scalar(@intervals);++$i) {
	$buffer.=sprintf("\t\tintervals [%d]:
\t\t\txmin = %.03f
\t\t\txmax = %.03f
\t\t\ttext = \"%s\"
", $i+1, $intervals[$i]->{"xmin"}, $intervals[$i]->{"xmax"}, $intervals[$i]->{"text"});
}

print $buffer;
