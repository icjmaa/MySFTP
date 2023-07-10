import os
import re
import platform

PATTERN_INFO_TO_LIST_FILES = re.compile(r"[l|d|r|w|x|\*|-]+(?:\.?)\s+\d+\s+[a-z|0-9|_\-]*\s+[a-z||0-9|_\-]*\s+[\d.]+\w*\s+\w+\s+\d+\s+[\d\:]+\s+")
PATTERN_TO_LIST_FILES = re.compile(r"[l|d|r|w|x|\*|-]+(?:\.?)\s+\d+\s+[a-z|0-9|_|-]*\s+[a-z|0-9|_|-]*\s+[\d.]+\w*\s+\w+\s+\d+\s+[\d\:]+\s+.+")
PATTERN_TO_SYMLINK = re.compile(r"\s+\-\>\s+.*")

class Debug():

	settings = None

	debug_file = ''

	@staticmethod
	def print( *args ):
		content = ' '.join(args)
		if Debug.settings.get('debug_mode'):
			file = open(Debug.debug_file, 'a')
			file.write( content + "\n")
			file.close()
		if Debug.settings.get('debug_console'):
			print(content)

def get_list_servers(servers_path):
	archivos = []
	for file in os.listdir( servers_path ):
		if os.path.isfile(os.path.join(servers_path, file)):
			filename, file_extension = os.path.splitext(file)
			if file_extension == '.json':
				archivos.append(filename)
	return archivos

def sortFiles(lista):
	list_files = []
	files_hiddens = []
	cntAux = 0

	lista = [ file for file in lista if PATTERN_TO_LIST_FILES.match(file) ]

	for file in lista:
		is_folder = False
		is_symlink = False
		list_files.sort()

		if file[-1] == '/' or file[0] == 'd':
			is_folder = True

		if file[0] == 'l':
			is_symlink = True

		name_file = PATTERN_INFO_TO_LIST_FILES.sub('', file).rstrip("*")

		if name_file == '.' or name_file == '..':
			continue

		if is_folder and name_file[-1] != '/':
			name_file = name_file + '/'


		if platform.system() == "Linux" or platform.system() == 'Darwin':
			real_name = PATTERN_TO_SYMLINK.sub('', name_file) + ('/' if is_folder and name_file.find('->') != -1 else '')
		elif platform.system() == "Windows" or platform.system() == 'win32' or platform.system() == 'win64':
			real_name = PATTERN_TO_SYMLINK.sub('', name_file) + ('->' if is_symlink else '')


		if is_folder and real_name.find('.mysftp') == -1:
			list_files.insert(cntAux, real_name)
			cntAux = cntAux + 1
		elif not is_folder and real_name.find('.mysftp') == -1:
			list_files.append(real_name)
		elif not is_folder and real_name.find('.mysftp') != -1:
			files_hiddens.append(real_name)

		list_files.sort()

	return list_files, files_hiddens

def createFile(phat, content = ''):
	file = open(phat, 'w')
	file.write(content)
	file.close()

def readFile(phat):
	file = open(phat, 'r')
	content = file.read()
	file.close()
	return content

def getTmpName(file_name):
	return '.' +  os.path.basename(file_name) + '.mysftp'

def getPath(path, *paths):
	return '/' + (os.path.normpath(os.path.join(path, *paths)).replace('\\', '/').rstrip("/").lstrip('/'))

