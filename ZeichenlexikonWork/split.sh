#!/bin/bash

pdftk Raw.pdf burst

pw=$(grep PageMediaDimensions <doc_data.txt | head -1 | awk '{print $2}') # Raw page width and height
ph=$(grep PageMediaDimensions <doc_data.txt | head -1 | awk '{print $3}')
w2=$(bc <<< "scale=2; $pw / 2") # New width
w2px=$(bc <<< "($w2 * 10)/1") # Convert to pixels
hpx=$(bc <<< "($ph * 10)/1") # (These should be integers)
echo $pw $ph $w2 $w2px $hpx

#gs -o SuppResize.pdf -sDEVICE=pdfwrite -dDEVICEWIDTH=$w2px -dDEVICEHEIGHT=$hpx -dFIXEDMEDIA -dPDFFitPage Supplement.pdf

for f in  pg_[0-9]*.pdf ; do # Now use ghostscript to break each page in half
	lf=left_$f
	rf=right_$f
#	echo "-g${w2px}x${hpx}"
	gs -o ${lf} -sDEVICE=pdfwrite -g${w2px}x${hpx} -c "<</PageOffset [0 0]>> setpagedevice" -f ${f}
	gs -o ${rf} -sDEVICE=pdfwrite -g${w2px}x${hpx} -c "<</PageOffset [-${w2} 0]>> setpagedevice" -f ${f}
done

ls -1 [lr]*_[0-9]*pdf | sort -n -k3 -t_ > fl
pdftk `cat fl`  cat output Paginated.pdf
