import sys
import os
import subprocess
import ftplib
import platform
import time
from datetime import datetime

from .Configuration import Configuration
from .ConnectionSSH import ConnectionSSH
from .extras import Debug
from .extras import createFile, readFile

class Connection():

	@staticmethod
	def start(file_local = '', file_server = '', path = '', permissions = '', command = ''):
		Debug.print("=========================================================================")
		Debug.print("COMMAND: command = {} - file_local = {} - file_server = {} - path = {} - permissions = {}".format(command, file_local, file_server, path, permissions))
		Debug.print("DATE: ", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
		Debug.print("=========================================================================")
		salida = ""
		if Configuration.tipo == "sftp":
			if platform.system() == "Linux" or platform.system() == 'Darwin':
				salida = Connection._sftpLinux(file_local=file_local, file_server=file_server, path=path, permissions=permissions, command=command)
			elif platform.system() == "Windows" or platform.system() == 'win32' or platform.system() == 'win64':
				salida = Connection._sftpWindows(file_local=file_local, file_server=file_server, path=path, permissions=permissions, command=command)
		else:
			salida = Connection._ftp(file_local=file_local, file_server=file_server, path=path, permissions=permissions, command=command)
		Debug.print("\nSALIDA: ", str(salida))
		Debug.print("**************** END COMMAND - DATE: " + datetime.now().strftime("%d-%m-%Y %H:%M:%S") + " ****************\n")
		return salida

	@staticmethod
	def ls():
		return Connection.start(command='ls')

	@staticmethod
	def get(file_server, file_local):
		return Connection.start(file_server='"{}"'.format(file_server), file_local='"{}"'.format(file_local), command='get')

	@staticmethod
	def put(file_local, file_server):
		return Connection.start(file_local='"{}"'.format(file_local), file_server='"{}"'.format(file_server), command='put')

	@staticmethod
	def mkdir(path):
		return Connection.start(path='"{}"'.format(path), command='mkdir')

	@staticmethod
	def rm(path, is_file):
		return Connection.start(path='"{}"'.format(path), command=('del' if is_file else 'rmdir'))

	@staticmethod
	def mv(file_local, file_server):
		return Connection.start(file_local='"{}"'.format(file_local), file_server='"{}"'.format(file_server), command='mv')

	@staticmethod
	def chmod(path, permissions):
		return Connection.start(path='"{}"'.format(path), permissions=permissions, command='chmod')


	@staticmethod
	def _sftpLinux(file_local = '', file_server = '', path = '', permissions = '', command = ''):
		if command == "ls":
			retorno = ConnectionSSH.ssh_exec(["ssh"," && ls -lrtahF | sed '/\.\//d' | sed '/\.\.\//d'"], True)
		elif command == "get":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nget " + file_server + " " + file_local], True)
		elif command == "put":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nput " + file_local + " " + file_server], True)
		elif command == "chmod":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nchmod " + permissions + " " + path], True)
		elif command == "mv":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nrename " + file_local + " " + file_server], True)
		elif command == "rmdir":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nrmdir " + path], True)
		elif command == "del":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nrm " + path], True)
		elif command == "mkdir":
			retorno = ConnectionSSH.ssh_exec(["sftp", "\nmkdir " + path], True)
		else:
			Debug.print("Comando incorrecto")

		Debug.print("\n".join(retorno[2]))
		salida = str( retorno[1].decode('utf-8', 'ignore') )

		return salida.strip(" \r\n")

	@staticmethod
	def _sftpWindows(file_local = '', file_server = '', path = '', permissions = '', command = ''):
		salida = None
		command_line = ''
		if command == 'ls':
			command_line = 'ls\n'
		elif command == 'get':
			command_line = 'get {} {}'.format(file_server, file_local)
		elif command == 'put':
			command_line = 'put {} {}'.format(file_local, file_server)
		elif command == 'mkdir':
			command_line = 'mkdir {}'.format(path)
		elif command == 'rmdir' or command == 'del':
			command_line = "{} {}".format(command, path)
		elif command == 'mv':
			command_line = 'mv {} {}'.format(file_local, file_server)
		elif command == 'chmod':
			command_line = 'chmod {} {}'.format(permissions, path)

		if command_line != '':
			command_line = "cd \"{}\"\n{}".format(Configuration.currentPath, command_line)

		try:
			createFile( os.path.join(Configuration.psftp_path, "script.bat"), command_line)
			unix_time = str(time.time())
			unix_time = unix_time.replace('.', '')
			dataout_name = 'data_' + unix_time + '.out'
			f = open(os.path.join(Configuration.psftp_path, dataout_name), "w")
			executable = 'psftp64.exe' if platform.architecture()[0] == '64bit' else 'psftp32.exe'
			proceso = subprocess.Popen(['echo', 'n', '|', os.path.join(Configuration.package_path, 'bin', executable), "-P", Configuration.puerto, "-pw", Configuration.password, "-b" , os.path.join(Configuration.psftp_path, 'script.bat'), Configuration.usuario + "@" + Configuration.host], stdout=f, stderr=subprocess.PIPE, shell=True)
			proceso.wait(8)
			f.close()
			errores = proceso.stderr.read()
			if proceso.stdout == None:
				with open(os.path.join(Configuration.psftp_path, dataout_name), "r") as content_file:
					content = content_file.read()
				salida = content
				time.sleep(1)
				try:
					os.remove(os.path.join(Configuration.psftp_path, dataout_name))
				except Exception as e:
					Debug.print(str(e))
					raise e
			else:
				salida = proceso.stdout.read()
				proceso.stdout.close()
				salida = salida.decode(sys.getdefaultencoding())

			proceso.stderr.close()
			errores = errores.decode(sys.getdefaultencoding())
			Debug.print("Errores: ", errores);
		except Exception as e:
			if str(e).find('TimeOutExpired') != -1:
				salida = "TimeOutExpired."
			elif str(e).find('PermissionError: [WinError 32]') != -1:
				salida = 'PermissionError: [WinError 32]'
			elif str(e).find('timed out after 8 seconds') != -1:
				return "TimeOutExpired."
			raise e

		if salida.find('Network error: Connection timed out') != -1:
			return 'Network error: Connection timed out'
		if salida.find('permission denied') != -1:
			return 'permission denied'
		if salida.find('no such file or directory') != -1:
			return 'no such file or directory'
		if errores.find('Fatal: Network error: Connection refused') != -1:
			return 'Fatal: Network error: Connection refused'
		if errores.find('Access denied') != -1:
			return 'Usuario o password incorrectos.'
		return salida if salida != '' else errores

	@staticmethod
	def _ftp(file_local = '', file_server = '', path = '', permissions = '', command = ''):
		file_local = file_local.strip('\"')
		file_server = file_server.strip('\"')
		path = path.strip('\"')
		permissions = permissions.strip('\"')
		command = command.strip('\"')
		salida = ''
		ftp = ftplib.FTP();
		try:
			ftp.connect(Configuration.host, int(Configuration.puerto))
			ftp.login(Configuration.usuario, Configuration.password)
			ftp.cwd(Configuration.currentPath)
			data = []
			if command == "ls":
				ftp.dir(data.append)
			elif command == "get":
				fhandle = open(file_local, 'wb')
				ftp.retrbinary("RETR " + file_server, fhandle.write)
				fhandle.close()
			elif command == "put":
				with open(file_local, "rb") as f:
					ftp.storlines("STOR " + file_server, f)
			elif command == "chmod":
				salida = ftp.sendcmd("SITE CHMOD " + permissions + " " + path)
			elif command == "mv":
				salida = ftp.rename(file_local, file_server)
			elif command == "rmdir":
				Connection._rm_tree(ftp, path)
			elif command == "del":
				ftp.delete(path)
			elif command == "mkdir":
				ftp.mkd(path)
				ftp.cwd(path)
				ftp.dir(data.append)
			else:
				Debug.print("Comando incorrecto")
			ftp.quit()
		except Exception as e:
			if str(e).find('Login incorrect') != -1:
				ftp.quit()
			return str(e)
			raise e

		if command == 'ls' or command == 'mkdir':
			salida = ''
			for file in data:
				salida = salida + file + "\n"
		return salida

	@staticmethod
	def _rm_tree(ftp, path):
		wd = ftp.pwd()
		try:
			names = ftp.nlst(path)
		except ftplib.all_errors as e:
			Debug.print('_rm_tree: No se puede borrar {0}: {1}'.format(path, e))
			return
		for name in names:
			if os.path.split(name)[1] in ('.', '..'): continue
			Debug.print('_rm_tree: Checking {0}'.format(name))
			try:
				ftp.cwd(name)
				ftp.cwd(wd)
				Connection._rm_tree(ftp, name)
			except ftplib.all_errors:
				ftp.delete(name)
		try:
			ftp.rmd(path)
		except ftplib.all_errors as e:
			Debug.print('_rm_tree: No se puede borrar {0}: {1}'.format(path, e))