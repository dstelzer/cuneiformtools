# This really has nothing to do with cuneiform, I just need a server to post it on temporarily
# This script removes watermarks from PDFs downloaded from Renegade Game Studios

from pathlib import Path
import subprocess as sp

def unwatermark_file(filename, temp_folder):
	filename = Path(filename)
	temp_folder = Path(temp_folder)
	tmp1 = temp_folder / '1.pdf'
	tmp2 = temp_folder / '2.pdf'
	tmp3 = temp_folder / '3.pdf'
	tmp4 = temp_folder / '4.pdf'
	
	Path(temp_folder).mkdir(exist_ok=True)
	sp.run(['pdftk', str(filename), 'output', str(tmp1), 'uncompress'])
	with tmp2.open('wb') as f1:
		sp.run(['sed', '-e', 's~\<446F776E6C6F6164656420627920[0-9A-F]*\>~\<20\>~', str(tmp1)], stdout=f)
	with tmp3.open('wb') as f2:
		sp.run(['sed', '-e', 's~\(Downloaded by[^)]*\)~ ~', str(tmp2)], stdout=f2)
	sp.run(['pdftk', str(tmp3), 'output', str(tmp4), 'compress'])
	tmp4.move(filename)
