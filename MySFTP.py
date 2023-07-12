import sys
import os
import subprocess
from threading import Thread
import json
import sublime
import sublime_plugin
import time
import re
import ftplib
import platform
#Libreria para sftp desde Linux(Ubuntu)
from .src.Configuration import Configuration
from .src.Connection import Connection
from .src.ProgressBar import ProgressBarCommand as ProgressBar, ShowProgressBarCommand
from .src.extras import get_list_servers, sortFiles, createFile, readFile, Debug, getTmpName, getPath
import datetime
import shutil

def plugin_loaded():
	# Se crea el directorio del plugin
	user_path = os.path.join(sublime.packages_path(), 'User')
	Configuration.mysftp_path = os.path.join(user_path, 'MySFTP')
	if not os.path.exists(Configuration.mysftp_path): os.makedirs(Configuration.mysftp_path)

	# Se crea el directorio para los archivos temporales
	Configuration.tmp_path = os.path.join(Configuration.mysftp_path, 'tmp')
	if os.path.exists(Configuration.tmp_path):
		shutil.rmtree(Configuration.tmp_path)

	if not os.path.exists(Configuration.tmp_path): os.makedirs(Configuration.tmp_path)

	# Se crea directorio para los archivos de configuración de servidores
	Configuration.servers_path = os.path.join(Configuration.mysftp_path, 'servers')
	if not os.path.exists(Configuration.servers_path): os.makedirs(Configuration.servers_path)

	# Se crea directorio para psftp 
	Configuration.psftp_path = os.path.join(Configuration.mysftp_path, 'psftp')
	if not os.path.exists(Configuration.psftp_path): os.makedirs(Configuration.psftp_path)

	Configuration.package_path = os.path.join(sublime.packages_path(), 'MySFTP')

	Debug.debug_file = os.path.join(Configuration.mysftp_path, '.debug')

	MySftp.settings = sublime.load_settings("MySFTP.sublime-settings")
	Debug.settings = MySftp.settings
	# create custome file settings
	if not os.path.exists(os.path.join(user_path, 'MySFTP.sublime-settings')):
		json_settings = {
			'debug_mode': MySftp.settings.get('debug_mode') or False,
			'debug_console': MySftp.settings.get('debug_console') or False,
			'check_if_write': MySftp.settings.get('check_if_write') or False
		}
		createFile(os.path.join(user_path, 'MySFTP.sublime-settings'), json.dumps(json_settings, indent='\t'))
	Debug.print("DEBUG_MODE: ", str(MySftp.settings.get('debug_mode')))
	Debug.print("DEBUG_CONSOLE: ", str(MySftp.settings.get('debug_console')))
	Debug.print("CHECK_IF_WRITE: ", str(MySftp.settings.get('check_if_write')))

	# Movemos los archivos de configuración servidores de la versión anterior al directorio servers
	for file in os.listdir( user_path ):
		full_name_file = os.path.join(user_path, file)
		if os.path.isfile(full_name_file):
			filename, file_extension = os.path.splitext(file)
			if file_extension != ".json":
				continue
			file_content = readFile( full_name_file )
			obj_match = re.findall(r"nick|type|host|remote_path|password|port|user", file_content)
			if obj_match != None and len(obj_match) == 7:
				shutil.move( full_name_file, os.path.join(Configuration.servers_path, file) )

	createFile(os.path.join(Configuration.mysftp_path, '.debug'))

class MySftp(sublime_plugin.TextCommand):
	listServers = []
	optionsFiles = ["> Cambiar de Servidor", "> Regresar", "> Editar","> Renombrar","> Cambiar Permisos","> Eliminar"]
	optionsFolders = ["> Cambiar de Servidor", "> Subir nivel","> Nuevo Archivo","> Nueva Carpeta","> Renombrar","> Cambiar Permisos","> Eliminar"]

	settings = None

	def run(self, edit):
		archivos = get_list_servers(Configuration.servers_path)
		self.view.window().run_command("show_servers", {"args" : archivos});

	@staticmethod
	def isWorking():
		try:
			is_alive = ShowProgressBarCommand.t != None and ShowProgressBarCommand.t.isAlive()
			if is_alive:
				raise Exception("threading isAlive")
		except Exception as e:
			sublime.message_dialog("Hay una operación en proceso, espere a que esta termine para continuar.")
			raise e

	@staticmethod
	def checkResponse(self, response, show_status = True):
		if not show_status:
			return True
		if response.find('Could not resolve hostname') != -1 or response.find('No route to host') != -1 or response.find('Network is unreachable') != -1 or response.find('Connection refused') != -1:
			ProgressBar.showError(self)
			ProgressBar.showMessage(self, 'Imposible conectar con el servidor, no se pudo resolver: {}.\n'.format(Configuration.host))
			return False
		elif response.find('Permission denied') != -1 or response.find('Could not create file') != -1:
			ProgressBar.showErrorPermissions(self)
			return False
		elif response.find('Usuario o password incorrectos') != -1 or response.find('Login incorrect') != -1:
			ProgressBar.showErrorCredentials(self)
			return False
		elif response.find('TimeOutExpired') != -1:
			ProgressBar.showErrorTimeOutExpired(self)
		elif response.find('o such file or directory') != -1:
			ProgressBar.showErrorNoSuchFileOrDirectory(self)
		elif response.find('PermissionError: [WinError 32]') != -1:
			ProgressBar.showError(self)
		elif response.find('No se puede establecer una conexión ya que el equipo de destino denegó expresamente') != -1:
			ProgressBar.showConnectionRefuse(self)
			return False
		else:
			ProgressBar.showSuccess(self)
		return True

class SyncFiles(sublime_plugin.WindowCommand):
	def run(self, comando):
		file = os.path.basename(self.window.active_view().file_name())

		if comando == "put_sftp":
			self.window.run_command("save");
			return

		Configuration.setConfig(os.path.join(Configuration.tmp_path, os.path.splitext(file)[0] + ".config"))
		if Configuration.flag_config != True:
			return

		if ProgressBar.createPanelOutput == False:
			ProgressBar.initConnection(self)
		self.window.run_command("get_sftp",{"file" : file, "flag" : True})

	def is_visible(self):
		return False if os.path.dirname(self.window.active_view().file_name()) != Configuration.tmp_path else True

class showServers(sublime_plugin.WindowCommand):
	def run(self, args):
		MySftp.isWorking();
		MySftp.listServers = args
		MySftp.listServers.insert(0, "Nuevo servidor.")
		quick_list = [option for option in MySftp.listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,self.on_done,0)

	def on_done(self, index):
		if index == 0:
			self.window.run_command('new_server')
		elif index > 0:
			previous_config = Configuration( json.loads(Configuration.getJsonConfig()) )
			Configuration.setConfig(os.path.join(Configuration.servers_path, MySftp.listServers[index] + ".json"))
			if not Configuration.flag_config:
				return
			if previous_config.host == '' or previous_config.usuario == '' or previous_config.host != Configuration.host or previous_config.usuario != Configuration.usuario or previous_config.puerto != Configuration.puerto:
				ProgressBar.initConnection(self)

			t1 = Thread(target=self.listado)
			t1.start()

	def listado(self):
		self.window.run_command("show_ls");

class showLs(sublime_plugin.WindowCommand):

	list_files = None
	files_hiddens = None

	def run(self):
		MySftp.isWorking();
		ProgressBar.showList(self)
		t1 = Thread(target=self.requestListFiles)
		t1.start()

	def requestListFiles(self):
		response = showLs.getListFiles(self, True)
		if showLs.list_files != None and response != False:
			self.Options = ["Directorio: " + Configuration.currentPath] + MySftp.optionsFolders + showLs.list_files
			quick_list = [option for option in self.Options]
			self.quick_list = quick_list
			self.window.show_quick_panel(quick_list, lambda id : self.on_done(id), 0)

	def on_done(self, index):
		if index > 7:
			if showLs.list_files[index - 8][-1:] == '/':
				Configuration.currentPath = getPath(Configuration.currentPath, showLs.list_files[index - 8])
				self.window.run_command("show_ls");
			elif showLs.list_files[index - 8][-2:] == '->':
				# no such file or directory
				tmp_current_path = Configuration.currentPath
				Configuration.currentPath = getPath(Configuration.currentPath, showLs.list_files[index - 8][:-2])
				list_files_old = showLs.list_files
				salida = showLs.getListFiles(self)
				showLs.list_files = list_files_old
				if salida != False and salida.find("no such file or directory") != -1:
					Configuration.currentPath = tmp_current_path;
					self.Options = [ "Archivo: " + showLs.list_files[index - 8][:-2] ] + MySftp.optionsFiles
					quick_list = [option for option in self.Options]
					self.quick_list = quick_list
					self.window.show_quick_panel(quick_list, lambda id : self.file_selected(id, showLs.list_files[index - 8][:-2]), 0)
				else:
					Configuration.currentPath = tmp_current_pathn;
					Configuration.currentPath = getPath(Configuration.currentPath, showLs.list_files[index - 8][:-2])
					self.window.run_command("show_ls");
			else:
				self.Options = [ "Archivo: " + showLs.list_files[index - 8] ] + MySftp.optionsFiles
				quick_list = [option for option in self.Options]
				self.quick_list = quick_list
				self.window.show_quick_panel(quick_list, lambda id : self.file_selected(id, showLs.list_files[index - 8]), 0)
		elif index == 2: # Up Level
			Configuration.currentPath = getPath(Configuration.currentPath, '../')
			self.window.run_command("show_ls");
		else:
			commams_folders = [['my_sftp', {}], ['show_ls', {}], ['new_file_sftp', {}], ['new_dir_sftp', {}],
								['rename_sftp', {"path" : os.path.basename(Configuration.currentPath), 'is_folder': True}], ['chmod_sftp', {"path" : os.path.basename(Configuration.currentPath), 'is_file': False}],
								['remove_sftp', {"path" : os.path.basename(Configuration.currentPath), "is_file" : False}]]
			if index > 0:
				self.window.run_command( commams_folders[index - 1][0], commams_folders[index - 1][1] )

	def file_selected(self, index, file):
		commams_files = [['my_sftp', {}], ['show_ls', {}], ['get_sftp', {"file" : file}],
						['rename_sftp', {"path" : file}], ['chmod_sftp', {"path" : file}],
						['remove_sftp', {"path" : file, "is_file" : True}]]
		if index == 2:
			self.Options = ["Directorio: " + Configuration.currentPath] + MySftp.optionsFolders + showLs.list_files
			quick_list = [option for option in self.Options]
			self.quick_list = quick_list
			self.window.show_quick_panel(quick_list, lambda id : self.on_done(id), 0)
		if index != 2 and index > 0:
			self.window.run_command( commams_files[index - 1][0], commams_files[index - 1][1] )

	@staticmethod
	def getListFiles(self, show_status_connection = False):
		salida = Connection.ls()
		if show_status_connection:
			if MySftp.checkResponse(self, salida, show_status_connection) != True: return False
		lista = salida.strip("\n").split("\n")
		listas = sortFiles(lista)
		showLs.list_files = listas[0]
		showLs.files_hiddens = listas[1]
		return salida

class ChmodSftp(sublime_plugin.WindowCommand):

	def run(self, path, is_file = True):
		self.window.show_input_panel("Permisos:", "", lambda permisos: self.chmod(permisos, path, is_file), None, None)

	def chmod(self, permisos, path, is_file = True):
		if re.match("[1-7]{3}", permisos) != None:
			burbuja = Configuration.currentPath
			if not is_file:
				Configuration.currentPath = os.path.dirname(Configuration.currentPath)

			ProgressBar.showChmod(self, getPath(Configuration.currentPath, path))
			t1 = Thread(target=self.hilo, args=[permisos, path, burbuja])
			t1.start()
		else:
			sublime.message_dialog("La sintaxis para definir permisos no es valida.")

	def hilo(self, permisos, path, burbuja):
		salida = Connection.chmod(path, permisos)
		Configuration.currentPath = burbuja
		if MySftp.checkResponse(self, salida) != True: 
			return

class removeSftp(sublime_plugin.TextCommand):

	def run(self, edit, path, is_file = True):
		burbuja = Configuration.currentPath
		if is_file == False:
			Configuration.currentPath = os.path.dirname(Configuration.currentPath)

		if path.find('.mysftp') == -1: # No lo encuentra
			ProgressBar.showDelete(self, getPath(Configuration.currentPath, path))

		t1 = Thread(target=self.hilo, args=[edit, path, is_file, burbuja])
		t1.start()

	def hilo(self, edit, path, is_file, burbuja):
		salida = Connection.rm(path, is_file)
		if path.find('.mysftp') == -1 and MySftp.checkResponse(self, salida) != True:
			Configuration.currentPath = burbuja
			return

class getSftp(sublime_plugin.TextCommand):

	def run(self, edit, file, flag = False):
		MySftp.isWorking();
		t1 = Thread(target=self.hilo, args=[edit, file, flag])
		t1.start()

	def hilo(self, edit, file, flag = False):
		ProgressBar.showDownload(self, getPath(Configuration.currentPath, file), file)

		if MySftp.settings.get('check_if_write') and "\n".join(showLs.files_hiddens).find( getTmpName(file) ) != -1: # Validamos que exista el archivo
			salida = Connection.get(getTmpName(file), os.path.join(Configuration.tmp_path, getTmpName(file)))
			if os.path.exists(os.path.join(Configuration.tmp_path, getTmpName(file))):
				nick_current_use = readFile(os.path.join(Configuration.tmp_path, getTmpName(file))).strip()
				os.remove(os.path.join(Configuration.tmp_path, getTmpName(file)))
				if nick_current_use != Configuration.nick:
					if not sublime.ok_cancel_dialog("El usuario " + nick_current_use + " esta usando actualmente el archivo, Deseas continuar con la descarga?."):
						Debug.print('Se manda a cancelar.')
						ProgressBar.showCancel(self)
						return

		if os.path.exists(os.path.join(Configuration.tmp_path, file)) and self.view.window().find_open_file(os.path.join(Configuration.tmp_path, file)) and flag == False:
			sublime.message_dialog("Ya existe un archivo con el mismo nombre, cierre primero para poder continuar editando otro archivo con el mismo nombre.")
			return
		
		salida = Connection.get(file, os.path.join(Configuration.tmp_path, file))
		time.sleep(0.02) # Esperamos que se termine de descargar el contenido
		if MySftp.checkResponse(self, salida) != True: return

		# Hay que poner los stops en los progressbar
		if os.path.exists(os.path.join(Configuration.tmp_path, file)):
			#ProgressBar.showSuccess(self)
			createFile(os.path.join(Configuration.tmp_path, os.path.splitext(file)[0] + ".path"), Configuration.currentPath)
			createFile(os.path.join(Configuration.tmp_path, os.path.splitext(file)[0] + ".config"), Configuration.getJsonConfig())
			vista = self.view.window().open_file(os.path.join(Configuration.tmp_path, file))
			t2 = Thread(target=self.hilo2, args=[file])
			t2.start()
		else:
			pass
			#ProgressBar.showError(self)

	def hilo2(self, file):
		createFile(os.path.join(Configuration.tmp_path, getTmpName(file)), Configuration.nick)
		salida = Connection.put(os.path.join(Configuration.tmp_path, getTmpName(file)), getTmpName(os.path.basename(file)))
		time.sleep(0.02)
		if os.path.exists(os.path.join(Configuration.tmp_path, getTmpName(file))):
			os.remove(os.path.join(Configuration.tmp_path, getTmpName(file)))

class MySftpEvent(sublime_plugin.EventListener):
	def on_post_save(self, view):
		ruta = view.file_name()
		if ruta != None and os.path.dirname(ruta) == Configuration.tmp_path:
			view.run_command("put_sftp", {"file" : view.file_name(), "flag" : False })
		else:
			Debug.print("este archivo no es valido para el package.")

	def on_close(self, view):
		ruta = view.file_name()
		if ruta != None and os.path.dirname(ruta) == Configuration.tmp_path and view.is_dirty() == False:
			view.run_command("remove_sftp", {"path" : getTmpName( os.path.basename(ruta) ), "is_file" : True})
			t1 = Thread(target=self.closeFile, args=[view, ruta])
			t1.start()

	def closeFile(self, view, ruta):
		if os.path.exists(ruta):
			os.remove(ruta)
		if os.path.exists( getTmpName(os.path.splitext(ruta)[0]) ):
			os.remove( getTmpName(os.path.splitext(ruta)[0]) )
		os.remove(os.path.splitext(ruta)[0] + ".path")
		os.remove(os.path.splitext(ruta)[0] + ".config")

class putSftp(sublime_plugin.TextCommand):

	def run(self, edit, file , flag):
		MySftp.isWorking();

		ruta = file.replace('.mysftp', "") if flag == True else file

		if os.path.dirname(ruta) != Configuration.tmp_path:
			return

		path_put = Configuration.currentPath
		old_path = Configuration.currentPath

		if flag == False:
			path_put = readFile(os.path.splitext(ruta)[0] + ".path")
			json_file = json.loads( readFile(os.path.splitext(ruta)[0] + ".config") )
			if Configuration.host == '' or Configuration.usuario == '' or Configuration.password == '' or Configuration.host != json_file[0]["host"] or Configuration.usuario != json_file[0]["user"] or Configuration.password != json_file[0]["password"]:
				Configuration.setConfig(os.path.splitext(ruta)[0] + ".config")
				if Configuration.flag_config != True:
					return
				ProgressBar.initConnection(self)
		Configuration.currentPath = path_put
		t1 = Thread(target=self.hilo1, args=[edit, ruta, flag, old_path])
		t1.start()

	def hilo1(self, edit, ruta, flag, old_path):
		if flag == False:
			ProgressBar.showUpload(self, os.path.basename(ruta), getPath(Configuration.currentPath, os.path.basename(ruta)))

		if MySftp.settings.get('check_if_write'):
			salida = Connection.get(getTmpName(ruta), os.path.join(Configuration.tmp_path, getTmpName(ruta)))
			if os.path.exists( os.path.join(Configuration.tmp_path, getTmpName(ruta)) ):#Validamos que exista el archivo
				nick_current_use = readFile(os.path.join(Configuration.tmp_path, getTmpName(ruta))).strip()
				if Configuration.nick != nick_current_use and flag == False:
					if not sublime.ok_cancel_dialog("El usuario " + nick_current_use + " esta usando actualmente el archivo, Deseas subir tus cambios?."):
						ProgressBar.showCancel(self)
						return

		createFile(os.path.join(Configuration.tmp_path, getTmpName(ruta)), Configuration.nick)

		if flag == False:
			t2 = Thread(target=self.hilo2, args=[edit, ruta, flag, old_path])
			t2.start()

	def hilo2(self, edit, ruta, flag, old_path):
		salida = Connection.put(ruta, os.path.basename(ruta))
		if 'nick_current_use' in locals():
			if Configuration.nick != nick_current_use:
				os.remove(os.path.join(Configuration.tmp_path, getTmpName(ruta)))
		if not flag:
			if MySftp.checkResponse(self, salida) != True: return

		t3 = Thread(target=self.hilo3, args=[edit, ruta, old_path])
		t3.start()

	def hilo3(self, edit, ruta, old_path):
		salida = Connection.put(os.path.join(Configuration.tmp_path, getTmpName(ruta)), getTmpName(ruta))
		Configuration.currentPath = old_path
		time.sleep(0.02)
		if os.path.exists(os.path.join(Configuration.tmp_path, getTmpName(ruta))):
			os.remove(os.path.join(Configuration.tmp_path, getTmpName(ruta)))

class newFileSftp(sublime_plugin.WindowCommand):
	def run(self):
		t1 = Thread(target=self.getListFiles)
		t1.start()
		time.sleep(0.16)
		self.window.show_input_panel("Nombre del archivo:", "", self.createFile, None, None)

	def createFile(self,name_file):
		# Validamos el nombre de archivo
		name_file = name_file.strip();
		if re.match("^[\w\-. ]+$", name_file):
			# Revisamos que no exista el archivo en remoto
			if name_file in showLs.list_files:
				sublime.message_dialog("Ya existe un archivo con el nombre: " + name_file + " en: " + Configuration.currentPath)
				return
			if os.path.isfile(os.path.join(Configuration.tmp_path, name_file)):
				sublime.message_dialog("Se encuentra editando un archivo con el mismo nombre, se recomienda cerrarlo primero.")
			else:
				local_file = os.path.join(Configuration.tmp_path, name_file)
				createFile(local_file)
				createFile(os.path.join(Configuration.tmp_path, os.path.splitext(name_file)[0] + ".path"), Configuration.currentPath)
				createFile(os.path.join(Configuration.tmp_path, os.path.splitext(name_file)[0] + ".config"), Configuration.getJsonConfig())
				ProgressBar.showMakeFile(self, getPath(Configuration.currentPath, name_file))
				t2 = Thread(target=self.hilo, args=[local_file])
				t2.start()
		else:
			sublime.message_dialog("Nombre de archivo no valido")

	def hilo(self, local_file):
		salida = Connection.put(local_file, os.path.basename(local_file))
		tmp_name = os.path.join(Configuration.tmp_path, getTmpName(os.path.basename(local_file)))
		createFile(tmp_name, Configuration.nick)
		Connection.put(tmp_name, os.path.basename(tmp_name))
		time.sleep(0.08)
		os.remove(tmp_name)
		if MySftp.checkResponse(self, salida) == True:
			self.window.open_file(local_file)

	def getListFiles(self):
		showLs.getListFiles(self)

class newDirSftp(sublime_plugin.WindowCommand):
	def run(self):
		t1 = Thread(target=self.getListFiles)
		t1.start()
		time.sleep(0.16)
		self.window.show_input_panel("Nombre del directorio:", "", self.createDir, None, None)

	def createDir(self, name_dir):
		name_dir = name_dir.strip();
		if re.match("^[\w\-. ]+$", name_dir):
			# Revisamos que no exista el archivo en remoto
			if (name_dir + '/') in showLs.list_files:
				sublime.message_dialog("Ya existe un directorio con el nombre: " + name_dir + " en: " + Configuration.currentPath)
				return
			t2 = Thread(target=self.hilo, args=[name_dir])
			t2.start()

	def hilo(self, name_dir):
		ProgressBar.showMakeDir(self, getPath(Configuration.currentPath, name_dir ))
		salida = Connection.mkdir(name_dir)
		if MySftp.checkResponse(self, salida) != True: return
		Configuration.currentPath = getPath(Configuration.currentPath, name_dir)
		self.window.run_command("show_ls");

	def getListFiles(self):
		showLs.getListFiles(self)

class ServerManager(sublime_plugin.WindowCommand):
	def run(self, action):
		MySftp.listServers = get_list_servers(Configuration.servers_path)
		quick_list = [option for option in MySftp.listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,lambda id : self.on_done(id, action),0)

	def on_done(self, index, action):
		if index >= 0:
			if action == 'edit':
				self.window.open_file(os.path.join(Configuration.servers_path, MySftp.listServers[index] + ".json"))
			elif action == 'remove':
				os.remove(os.path.join(Configuration.servers_path, MySftp.listServers[index] + ".json"))

class NewServer(sublime_plugin.WindowCommand):
	def run(self):
		vista = self.window.new_file()
		vista.run_command('insert_snippet', {"name": "Packages/MySFTP/server.sublime-snippet" })
		vista.set_syntax_file("JSON.sublime-syntax")
		vista.set_name('server.json')
		vista.settings().set('default_dir', Configuration.servers_path)

class renameSftp(sublime_plugin.WindowCommand):
	def run(self, path, is_folder = False):
		self.window.show_input_panel("Nombre Nuevo:", path, lambda name:self.rename(path, name, is_folder), None, None)

	def rename(self, current_name, new_name, is_folder = False):
		ProgressBar.showRename(self, current_name, new_name)
		t1 = Thread(target=self.hilo, args=[current_name, new_name, is_folder])
		t1.start()

	def hilo(self, current_name, new_name, is_folder = False):
		burbuja = Configuration.currentPath
		if is_folder:
			Configuration.currentPath = os.path.dirname(Configuration.currentPath)

		salida = Connection.mv(current_name, new_name)
	
		if MySftp.checkResponse(self, salida) != True:
			if is_folder:
				Configuration.currentPath = burbuja
			return
		else:
			if is_folder:
				Configuration.currentPath = getPath(Configuration.currentPath, new_name)

class SideBar(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		###self.window.run_command("progress_bar", {"msg" : "\nCargando "})
		ProgressBar.showDownload(self)
		t1 = Thread(target=self.testLoad)
		t1.start()

	def testLoad(self):
		# self.window.run_command("progress_bar", {"msg" : "", "start_loading": True, "stop_loading": False})
		time.sleep(2)
		# self.window.run_command("progress_bar", {"msg" : "success", "start_loading": False, "stop_loading": True})
		ProgressBar.showSuccess(self)

	def is_visible(self, paths = ''):
		return True

	def is_enabled(self, paths = ''):
		Debug.print("$path", paths)
		return True