#!/bin/bash

# Beginning Cover, 2, 3, 4, 5, 1
# 6: off by -1
# 114: off by -1
# 115-116: DROP
# 117: off by 1
# 150: off by 1
# 151-152: DROP
# 153: off by 3
# 188: off by 3
# 189-190: DROP
# 191: off by 5
# 194: off by 5
# SCAN1 2-7
# 195: off by -1
# 236: off by -1
# 237-238: DROP
# 239: off by 1
# 248: off by 1
# 249-250: DROP
# 251: off by 3
# 272: off by 3
# 273-274: DROP
# 275: off by 5
# 278: off by 5
# 279-280: DROP
# 281: off by 7
# 288: off by 7
# 289-290: DROP
# 291: off by 9
# 316: off by 9
# 317-318: DROP
# 319: off by 11
# 358: off by 11
# 359-360: DROP
# 361: off by 13
# 362: off by 13
# 363-364: DROP
# 365: off by 15
# 370: off by 15
# SCAN1 10-13
# 371: off by 11
# 372: off by 11
# 373-374: DROP
# 375: off by 13
# 400: off by 13
# 401-402: DROP
# SCAN1 14

pdftk A=Paginated.pdf S=ResizeSupplement.pdf M=Missing.pdf \
	X=ResizeScan1.pdf Y=ResizeScan2.pdf Z=ResizeCover.pdf \
	cat Z1 A2-5 A1 A6-114 A117-150 A153-188 A191-194 X2-7 A195-236 \
	A239-248 A251-272 A275-278 A281-288 A291-316 A319-358 A361-362 \
	A365-370 X10-13 A371-372 A375-400 X14 output Organized.pdf

gs -o Zeichenlexikon.pdf -sDEVICE=pdfwrite Bookmarks.ps -f Organized.pdf
