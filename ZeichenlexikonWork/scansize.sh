#!/bin/bash

wg=$(pdftk Paginated.pdf dump_data | grep PageMediaDimensions | head -1 | awk '{print $2}') # Goal width
wpx=$(bc <<< "($wg * 10)/1")
echo $wg $wpx

for main in Scan*.pdf Supplement.pdf Cover.pdf ; do
	echo $main
	rm pg_[0-9]*.pdf
	pdftk $main burst
	for f in pg_[0-9]*.pdf ; do
		pw=$(pdftk $f dump_data | grep PageMediaDimensions | tail -1 | awk '{print $2}')
		ph=$(pdftk $f dump_data | grep PageMediaDimensions | tail -1 | awk '{print $3}')
		tmp=$(bc <<< "scale=2; $ph * ($wpx/$pw)")
		hpx=$(bc <<< "$tmp/1") # Round
		gs -o scale_$f -sDEVICE=pdfwrite -dDEVICEWIDTH=$wpx -dDEVICEHEIGHT=$hpx -dFIXEDMEDIA -dPDFFitPage $f
	done
	pdftk scale_*.pdf cat output Resize$main
done
