import sys
import os
import subprocess
import json
import sublime
import sublime_plugin
import time
import re
import ftplib
import platform
#Libreria para sftp desde Linux(Ubuntu)
from .sshpass import ssh_exec_pass
import datetime

global Pref, s, Cache
Cache = {}

mydir = ""
currentPath = ""
tmp_dir = "C:\\tmp_my_sftp"

tipo = "sftp"
puerto = 21
usuario = ""
nick = ""
password = ""
host = "/home/"

optionsFiles = ["> Cambiar de Servidor", "> Regresar", "> Editar","> Renombrar","> Cambiar Permisos","> Eliminar"]
optionsFolders = ["> Cambiar de Servidor", "> Subir nivel","> Nuevo Archivo","> Nueva Carpeta","> Renombrar","> Cambiar Permisos","> Eliminar"]
contador_uso = 0

createPanelOutput = False
cntLine = 0

diagonal = "\\"

flag_config = True
str_json_config = ''

class MySftp(sublime_plugin.TextCommand):
	def run(self, edit):
		global mydir, diagonal, tmp_dir
		mydir = sublime.packages_path() + "/User"
		if platform.system() == "Linux":
			diagonal = "/"
			tmp_dir = mydir + diagonal + "tmp_my_sftp"

		archivos = get_list_servers()
		self.view.window().run_command("show_servers", {"args" : archivos});

class SyncFiles(sublime_plugin.WindowCommand):
	def run(self, comando):
		file = os.path.basename(self.window.active_view().file_name())

		if comando == "put_sftp":
			self.window.run_command("save");
			return

		self.window.run_command('set_config', {'file_json' : tmp_dir + diagonal + os.path.splitext(file)[0] + ".config"});
		if flag_config != True:
			return

		if createPanelOutput == False:
			self.window.run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
			self.window.run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
		self.window.run_command("get_sftp",{"file" : file, "flag" : True})

	def is_visible(self, paths = []):
		return False if os.path.dirname(self.window.active_view().file_name()) != tmp_dir else True

class showServers(sublime_plugin.WindowCommand):
	def run(self,args):
		global listServers
		listServers = args
		listServers.insert(0, "Nuevo servidor.")
		quick_list = [option for option in listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,self.on_done,0)

	def on_done(self,index):
		if index == 0:
			self.window.run_command('new_server')
		elif index > 0:
			self.window.run_command('set_config', {'file_json' : mydir + diagonal + listServers[index] + ".json"});
			if flag_config != True:
				return

			if createPanelOutput == False:
				self.window.run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
				self.window.run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})

			self.window.run_command("progress_bar", {"mensaje" : "\nListando el directorio: " + currentPath})
			salida = SFTP("cd " + currentPath + "\nls\nbye\n", tipo, "ls")

			if salida == False:
				self.window.run_command("progress_bar", {"mensaje" : "    error\nImposible conectar con el servidor por el momento."})
				return

			self.window.run_command("show_ls",{"args" : salida});

class showLs(sublime_plugin.WindowCommand):
	def run(self, args):
		global list_files, optionsFolders, currentPath
		list_files = []
		lista = args.split("\n")

		start = 1 if (platform.system() == "Linux" ) else 3

		cntAux = 0;
		for item in range(start,len(lista) - 1):
			list_files.sort()
			file = lista[item]
			cadena_limpia = self.limpiarCadena(file)
			condicion = len(cadena_limpia.split(" ")) == 9
			if condicion:
				name_file = cadena_limpia.split(" ")[8] + ( '/' if cadena_limpia[0] == 'd' else '' )

				if name_file[0] != '.' and name_file[0][-1:] == '/' and name_file.find('.sftp') == -1:
					list_files.insert(cntAux, name_file)
					cntAux = cntAux + 1
				elif name_file[0] != '.' and name_file[0][-1:] != '/' and name_file.find('.sftp') == -1:
					list_files.append(name_file)

			list_files.sort()

		self.Options = ["Directorio: " + currentPath] + optionsFolders + list_files
		quick_list = [option for option in self.Options]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,lambda id : self.on_done(id, args),0)

	def on_done(self,index, args):
		global currentPath
		salida = ''
		if index > 7:
			if list_files[index - 8][-1:] == "/":
				currentPath = currentPath + list_files[index - 8]
				self.window.run_command("progress_bar", {"mensaje" : "\nListando el directorio: " + currentPath})
				salida = SFTP("cd " + currentPath + "\nls\n", tipo, "ls")
				self.window.run_command("show_ls",{"args" : salida});
			else:
				self.Options = [ "Archivo: " + list_files[index - 8] ] + optionsFiles
				quick_list = [option for option in self.Options]
				self.quick_list = quick_list
				self.window.show_quick_panel(quick_list,lambda id : self.file_selected(id,index - 8, args),0)

		elif index == 2: # Up Level
			upLevel = os.path.normpath(os.path.join(currentPath,"../")).replace("\\", "/") + "/"
			self.window.run_command("progress_bar", {"mensaje" : "\nListando el directorio: " + upLevel})
			currentPath = upLevel
			salida = SFTP("cd " + upLevel + "\nls\n", tipo, "ls")
			if salida == False:
				self.window.run_command("progress_bar", {"mensaje" : "    error\nImposible conectar con el servidor por el momento."})
				return
			currentPath = upLevel
		else:
			commams_folders = [['my_sftp', {}], ['show_ls', {"args" : salida}], ['new_file_sftp', {}], ['new_dir_sftp', {}],
								['rename_sftp', {"archivo" : currentPath}], ['chmod_sftp', {"filename" : currentPath}],
								['remove_sftp', {"file" : currentPath, "is_file" : False}]]

			if index > 0:
				self.window.run_command( commams_folders[index - 1][0], commams_folders[index - 1][1] )

	def file_selected(self, index, index_file, args):
		commams_files = [['my_sftp',{}], ['show_ls', {'args' : args}], ['get_sftp', {"file" : list_files[index_file], "lista" : list_files}],
						['rename_sftp', {"archivo" : list_files[index_file]}], ['chmod_sftp', {"filename" : list_files[index_file]}],
						['remove_sftp', {"file" : list_files[index_file], "is_file" : True}]]
		if index > 0:
			self.window.run_command( commams_files[index - 1][0], commams_files[index - 1][1] )

	def limpiarCadena(self, texto):
		ant = None
		limpio = ""
		for i in range(0, len(texto)):
			if texto[i] == ant and texto[i] == ' ':
				pass
			else:
				if texto[i] != '\r':
					limpio = limpio + texto[i]
			ant = texto[i]
		return limpio


class chmod_sftp(sublime_plugin.WindowCommand):
	def run(self, filename):
		self.window.show_input_panel("Permisos:", "", lambda permisos: self.chmod(permisos,filename), None, None)
	def chmod(self, permisos, filename):
		if re.match("[1-7]{3}", permisos) != None:
			self.window.run_command("progress_bar", {"mensaje" : "\nCambiando permisos al archivo: " + currentPath + filename})
			salida = SFTP("cd " + currentPath + "\nchmod " + permisos + " " + filename, tipo, "chmod")
			if salida == "permission denied":
				self.window.run_command("progress_bar", {"mensaje" : "    error\nNo tiene los permisos necesarios."})
		else:
			sublime.message_dialog("Permisos invalidos")

class removeSftp(sublime_plugin.TextCommand):
	def run(self, edit, file, is_file):
		global currentPath
		if is_file == False:
			currentPath = os.path.dirname(currentPath.rstrip(""))
			sublime.message_dialog(currentPath)

		if file.find(".sftp") == -1:
			self.view.window().run_command("progress_bar", {"mensaje" : "\nEliminando: " + file.rstrip("/")})

		salida = SFTP("cd " + currentPath + "\n" + ("del" if is_file == True else "rmdir") + " " + file.rstrip("/"), tipo, ("del" if is_file == True else "rmdir"))
		if not is_file:
			upLevel = os.path.normpath(os.path.join(currentPath,"../")).replace("\\", "/")
			sublime.message_dialog(currentPath + "\n" + upLevel)
			currentPath = upLevel
		if salida == "permission denied":
			self.view.window().run_command("progress_bar", {"mensaje" : "    error\nNo tienes los permisos necesarios."})

class getSftp(sublime_plugin.TextCommand):
	def run(self,edit,file, flag = False, lista = []):
		global createPanelOutput
		#flag_edit = True
		now = datetime.datetime.now()
		self.view.window().run_command("progress_bar", {"mensaje" : "\n" + now.strftime("%H:%M:%S") + "->Descargando: " + currentPath + file + " en " + tmp_dir + diagonal + file, "change" : False, "loading" : True})

		if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)#Cramos la carpeta temporal
		##############################################################################
		if "\n".join(lista).find(file + ".sftp") > 0:#Validamos que exista el archivo
			salida = SFTP("cd " + currentPath + "\nget " + file + ".sftp" + " " + tmp_dir + diagonal + file + ".sftp", tipo, "get")
			if os.path.exists(tmp_dir + diagonal + file + ".sftp"):
				nick_current_use =  readFile(tmp_dir + diagonal + file + '.sftp')
				os.remove(tmp_dir + diagonal + file + ".sftp")

				if nick_current_use != nick:
					if not sublime.ok_cancel_dialog("El usuario " + nick_current_use + " esta usando actualmente el archivo, Deseas continuar con la descarga?."):
						self.view.window().run_command("progress_bar", {"mensaje" : "    Cancel."})
						return
				#flag_edit = False

		##############################################################################
		if os.path.exists(tmp_dir + diagonal + file) and self.view.window().find_open_file(tmp_dir + diagonal + file) and flag == False:
			sublime.message_dialog("Ya existe un archivo con el mismo nombre, cierre primero para poder continuar editando otro archivo con el mismo nombre.")
			return
		else:
			createFile(tmp_dir + diagonal + file + ".sftp", nick)
			#---------------------------------HAY EVITAR UNA PETICIÓN DE MAS AQUÍ----------------------------------
			salida = SFTP("cd " + currentPath + "\nput " + tmp_dir + diagonal + file + ".sftp" + " " + os.path.basename(file) + ".sftp" + "\nget " + file + " " + tmp_dir + diagonal + file, tipo, "get")
			if os.path.exists(tmp_dir + diagonal + file + ".sftp"):
				os.remove(tmp_dir + diagonal + file + ".sftp")
			#---------------------------------HAY EVITAR UNA PETICIÓN DE MAS AQUÍ----------------------------------
			if salida == "permission denied":
				self.view.window().run_command("progress_bar", {"mensaje" : "    error\nNo tiene los permisos necesarios."})
				return

		createFile(tmp_dir + diagonal + os.path.splitext(file)[0] + ".path", currentPath)
		createFile(tmp_dir + diagonal + os.path.splitext(file)[0] + ".config", str_json_config)

		#------------------------------------------------------
		if createPanelOutput == False:
			self.view.window().create_output_panel("progess_bar")
			createPanelOutput = True
		self.view.window().run_command("show_panel", {"panel": "output.progess_bar"})

		def show_progress_bar():
			show_progress_bar.message = " "
			show_progress_bar.change = True
			vista = self.view.window().open_file(tmp_dir + diagonal + file)
			while vista.is_loading():
				view = self.view.window().find_output_panel("progess_bar")
				view.run_command("my_insert_progress_bar", {"message" : show_progress_bar.message, "change" : show_progress_bar.change})
		sublime.set_timeout_async(show_progress_bar, 1)

class MySftpEvent(sublime_plugin.EventListener):
	def on_load(self,view):
		if os.path.dirname(view.file_name()) == tmp_dir:
			view.window().run_command("progress_bar", {"mensaje" : "success", "change" : True, "loading" : False})

	def on_post_save(self,view):
		view.run_command("put_sftp", {"file" : view.file_name(), "flag" : False })

	def on_close(self,view):
		ruta = view.file_name()
		if ruta != None and os.path.dirname(ruta) == tmp_dir and view.is_dirty() == False:
			view.run_command("remove_sftp", {"file" : os.path.basename(ruta) + ".sftp", "is_file" : True})
			os.remove(ruta)
			os.remove(os.path.splitext(ruta)[0] + ".path")
			os.remove(os.path.splitext(ruta)[0] + ".config")

class putSftp(sublime_plugin.TextCommand):
	def run(self, edit, file , flag):
		global mydir, createPanelOutput, tmp_dir, diagonal
		mydir = sublime.packages_path() + "/User"

		if platform.system() == "Linux":
			diagonal = "/"
			tmp_dir = mydir + diagonal + "tmp_my_sftp"

		ruta = file.replace(".sftp", "") if flag == True else file

		if os.path.dirname(ruta) == tmp_dir:
			path_put = currentPath
			if flag == False:
				path_put = readFile(os.path.splitext(ruta)[0] + ".path")
				json_file = json.loads( readFile(os.path.splitext(ruta)[0] + ".config") )#leemos el archivo de configuración
				if host == '' or usuario == '' or password == '' or host != json_file[0]["host"] or usuario != json_file[0]["user"] or password != json_file[0]["password"]:
					self.view.window().run_command('set_config', {'file_json' : os.path.splitext(ruta)[0] + ".config"});
					if flag_config != True:
						return

					if createPanelOutput == False:
						self.view.window().run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
					else:
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectando con el servidor"})
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})

			salida = SFTP("cd " + currentPath + "\nget " + os.path.basename(ruta) + ".sftp" + " " + tmp_dir + diagonal + os.path.basename(ruta) + ".sftp", tipo, "get")
			if os.path.exists( tmp_dir + diagonal + os.path.basename(ruta) + ".sftp" ):#Validamos que exista el archivo
				nick_current_use = readFile(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp")

				if nick != nick_current_use and flag == False:
					if not sublime.ok_cancel_dialog("El usuario " + nick_current_use + " esta usando actualmente el archivo, Deseas subir tus cambios?."):
						self.view.window().run_command("progress_bar", {"mensaje" : "    Cancel."})
						return

			createFile(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp", nick)

			if flag == False:
				now = datetime.datetime.now()
				self.view.window().run_command("progress_bar", {"mensaje" : "\n" + now.strftime("%H:%M:%S") + "->Subiendo: " + ruta + " en " + path_put + os.path.basename(ruta), "change" : False, "loading" : True})
				salida = SFTP("cd " + currentPath + "\n" + "put " + tmp_dir + diagonal + os.path.basename(ruta) + ".sftp" + " " + os.path.basename(ruta) + ".sftp" + "\nput " + ruta + " " + path_put + os.path.basename(ruta), tipo, "put")
			else:
				salida = SFTP("cd " + currentPath + "\n" + "put " + tmp_dir + diagonal + os.path.basename(ruta) + ".sftp" + " " + currentPath + os.path.basename(ruta) + ".sftp", tipo, "put")

			if 'nick_current_use' in locals():
				if nick != nick_current_use:
					os.remove(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp")

			if salida == "permission denied":
				self.view.window().run_command("progress_bar", {"mensaje" : "    error\nNo tienes los permisos necesarios para escribir sobre el archivo", "change" : False, "loading" : True})
				return
			if createPanelOutput == False:
				self.window.create_output_panel("progess_bar")
				createPanelOutput = True
			self.view.window().run_command("show_panel", {"panel": "output.progess_bar"})

			def show_progress_bar():
				show_progress_bar.message = "    success"
				show_progress_bar.change = True
				view = self.view.window().find_output_panel("progess_bar")
				if not flag:
					view.run_command("my_insert_progress_bar", {"message" : show_progress_bar.message, "change" : show_progress_bar.change})
			sublime.set_timeout_async(show_progress_bar, 1)


class newFileSftp(sublime_plugin.WindowCommand):
	def run(self):
		self.window.show_input_panel("Nombre del archivo:", "", self.createFile, None, None)

	def createFile(self,name_file):
		if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
		if os.path.isfile(tmp_dir + diagonal + name_file):
			sublime.message_dialog("Ya existe el archivo")
		else:
			createFile(tmp_dir + diagonal + name_file, '')
			createFile(tmp_dir + diagonal + os.path.splitext(name_file)[0] + ".path", currentPath)
			createFile(tmp_dir + diagonal + os.path.splitext(name_file)[0] + ".config", str_json_config)

			def esperando():
				vista = self.window.open_file(tmp_dir + diagonal + name_file)
				while vista.is_loading():
					pass
				self.window.run_command("put_sftp", {"file" : "", "flag" : False });
			sublime.set_timeout_async(esperando, 0)

class newDirSftp(sublime_plugin.WindowCommand):
	def run(self):
		self.window.show_input_panel("Nombre del directorio:", "", self.createDir, None, None)
	def createDir(self,name_dir):
		global currentPath
		name_dir = re.sub(' +', ' ',name_dir)
		name_dir = name_dir.strip()
		if name_dir == '' :
			sublime.message_dialog("Nombre invalido :(")
		else:
			self.window.run_command("progress_bar", {"mensaje" : "\nCreando directorio: " + currentPath + name_dir})
			salida = SFTP("cd " + currentPath + "\n" + "mkdir " + name_dir + "\ncd " + name_dir + "/" + "\nls", tipo, "mkdir")
			if salida == "permission denied":
				self.window.run_command("progress_bar", {"mensaje" : "    error\nNo tienes los permisos necesarios"})
				return
			currentPath = currentPath + "/" + name_dir
			self.window.run_command("show_ls",{"args" : salida});

class ServerManager(sublime_plugin.WindowCommand):
	listServers = []
	def run(self, action):
		global mydir, listServers
		mydir = sublime.packages_path() + "/User"
		listServers = get_list_servers()
		quick_list = [option for option in listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,lambda id : self.on_done(id, action),0)

	def on_done(self, index, action):
		if index > 0:
			if action == 'edit':
				self.window.open_file(mydir + diagonal + listServers[index] + ".json")
			elif action == 'remove':
				os.remove(mydir + diagonal + listServers[index] + ".json")

class NewServer(sublime_plugin.WindowCommand):
	def run(self):
		vista = self.window.new_file()
		self.window.run_command('insert_snippet',{"contents": "[{\n\t\"nick\" : \"" + nick + "\",\n\t\"type\" : \"" + tipo + "\",\n\t\"host\" : \"${1:[ip_host:host_name]}\",\n\t\"user\" : \"${2:usuario}\",\n\t\"password\" : \"${3:contraseña}\",\n\t\"port\" : \"${4:puerto}\",\n\t\"remote_path\" : \"${5:/var/www/html/}\"\n}]"})
		vista.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")
		vista.settings().set('default_dir', sublime.packages_path() + '/User')

class renameSftp(sublime_plugin.WindowCommand):
	def run(self,archivo):
		self.window.show_input_panel("Nombre Nuevo:", archivo.rstrip("/"), lambda name:self.newName(archivo.rstrip("/"),name), None, None)
	def newName(self, name_current, new_name):
		self.window.run_command("progress_bar", {"mensaje" : "\nRenombrando: " + name_current + " a " + new_name})
		salida = SFTP("cd " + currentPath + "\nmv " + name_current + " " + new_name, tipo, "mv")
		if salida == "permission denied":
			self.window.run_command("progress_bar", {"mensaje" : "    error\nNo tienes los permisos necesarios."})

class MyInsertProgressBarCommand(sublime_plugin.TextCommand):
	def run(self, edit, message, change):
		global cntLine
		view = self.view
		view.set_read_only(False)
		# view.settings().set("color_scheme", "Packages/MySFTP/Monokai.tmTheme")
		view.set_syntax_file("MySFTP.tmLanguage")
		point = self.view.text_point(cntLine, 0)
		view.insert(edit, point, message)
		view.set_read_only(True)
		view.show(point)
		cntLine += 1

class ProgressBarCommand(sublime_plugin.WindowCommand):
	def run(self, mensaje, change = False, loading = False):
		global createPanelOutput
		if createPanelOutput == False:
			self.window.create_output_panel("progess_bar")
			createPanelOutput = True
		self.window.run_command("show_panel", {"panel": "output.progess_bar"})

		def test_progress_bar():
			test_progress_bar.message = mensaje
			test_progress_bar.change = change
			self.show_progress(test_progress_bar.message, test_progress_bar.change)

		sublime.set_timeout_async(test_progress_bar, 1)

	def show_progress(self,message, change):
		view = self.window.find_output_panel("progess_bar")
		view.run_command("my_insert_progress_bar", {"message" : message, "change" : change})

	def finish_progress(self, message):
		self.show_progress(100,message)

	def _destroy(self):
		self.window.destroy_output_panel("progess_bar")

def SFTP(comando, type = "sftp", cmd = ""):
	global puerto, usuario, password, host, contador_uso, tipo
	salida = ""

	array_comando = comando.split("\n")[1]
	if array_comando != "ls":
		print(cmd, array_comando.split(' '))
		try:
			file_server = array_comando.split(' ')[1 if cmd == "get" and cmd != "put" else 2]
			file_local = array_comando.split(' ')[2 if cmd == "get" and cmd != "put" else 1]
		except IndexError:
			file_name = array_comando.split(' ')[2 if cmd =="chmod" and cmd != "del" else 1]
			print("Oops! Algun indice incorrecto")
		if cmd == "chmod":
			permisos = array_comando.split(' ')[1]
		elif cmd == "mv":
			current_name = array_comando.split(' ')[1]
			last_name = array_comando.split(' ')[2]
		elif cmd == "rmdir" or cmd == "mkdir":
			dir_name = array_comando.split(' ')[1]

	if (cmd == 'get' or cmd == 'put') and len(comando.split("\n")) == 3 and platform.system() == "Linux" and tipo == "sftp":
		print("Se combio el modus " + 'putandget' if cmd == 'get' else 'putandput')
		file_put_local = file_one_local = comando.split("\n")[1].split(' ')[1]
		file_put_server = file_one_server = comando.split("\n")[1].split(' ')[2]

		file_get_server = file_two_local = comando.split("\n")[2].split(' ')[1]
		file_get_local = file_two_server = comando.split("\n")[2].split(' ')[2]
		cmd = 'putandget'if cmd == 'get' else 'putandput'

	if tipo == "sftp":
		if platform.system() == "Linux":
			#sublime.message_dialog( platform.system() )
			if cmd == "ls":
				retorno = ssh_exec_pass(password, ["ssh", usuario + "@" + host, "cd " + currentPath + " && ls -lrt | sed '/ \.$/d' | sed '/ \.\.$/d'"], True)
			elif cmd == "get":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nget " + file_server + " " + file_local], True)
			elif cmd == "putandget":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nput " + file_put_local + " " + file_put_server + "\nget " + file_get_server + " " + file_get_local], True)
			elif cmd == "put":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nput " + file_local + " " + file_server], True)
			elif cmd == 'putandput':
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\n" + "put " + file_one_local + " " + file_one_server + "\nput " + file_two_local + " " + file_two_server], True)
			elif cmd == "chmod":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nchmod " + permisos + " " + file_name], True)
			elif cmd == "mv":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrename " + current_name + " " + last_name], True)
			elif cmd == "rmdir":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrmdir " + dir_name], True)
			elif cmd == "del":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrm " + file_name], True)
			elif cmd == "mkdir":
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nmkdir " + dir_name], True)
				retorno = ssh_exec_pass(password, ["ssh", usuario + "@" + host, "cd " + currentPath + dir_name + " && ls -lrt  | sed '/ \.$/d' | sed '/ \.\.$/d'"], True)
			else:
				sublime.message_dialog("Comando incorrecto")

			print(retorno[2])
			salida = str( retorno[1].decode('utf-8', 'ignore') )

			if salida.find("Could not resolve hostname") != -1:
				return False
			elif salida.find("total") == -1:
				return False
		else:
			try:
				createFile(sublime.packages_path() + "\\User\\script.bat", comando)

				f = open(sublime.packages_path() + "\\MySFTP\\data.out","w")
				proceso = subprocess.Popen([sublime.packages_path() + "\\MySFTP\\bin\\psftp.exe" ,"-P" , puerto, "-pw", password, "-b" , sublime.packages_path() + "\\User\\script.bat", usuario + "@" + host], stdout=f, stderr=subprocess.PIPE, shell=True)
				proceso.wait(10)
				f.close()
				errores = proceso.stderr.read()
				if proceso.stdout == None:
					with open(sublime.packages_path() + "\\MySFTP\\data.out","r") as content_file:
						content = content_file.read()
					salida = content
					os.remove( sublime.packages_path() + "\\MySFTP\\data.out" )
				else:
					salida = proceso.stdout.read()
					proceso.stdout.close()
					salida = salida.decode(sys.getdefaultencoding()) #Salida del comando

				proceso.stderr.close()
				errores = errores.decode(sys.getdefaultencoding())
				if errores.find("Using username") == -1:
					print("Errores: " + errores)
			except subprocess.TimeoutExpired as e:
				salida = "Usuario o password incorrectos."
				print("Ocurrio esto")
				return False
				raise e

			if salida.find("Network error: Connection timed out") != -1:
				print("fue esto")
				print(salida)
				return False
			if salida.find("permission denied") != -1:
				print(salida)
				return "permission denied"
	else:
		ftp = ftplib.FTP();
		ftp.connect(host, int(puerto))
		ftp.login(usuario, password)
		ftp.cwd(currentPath)
		data = []
		array_comando = comando.split("\n")[1]

		if cmd == "ls":
			ftp.dir(data.append)
			for item in data:
				salida = salida + item + "\n"
		elif cmd == "get":
			fhandle = open(file_local, 'wb')
			ftp.retrbinary('RETR ' + file_server , fhandle.write)
			fhandle.close()
		elif cmd == "put":
			with open(file_local, "rb") as f:
				ftp.storlines("STOR " + file_server, f)
		elif cmd == "chmod":
			salida = ftp.sendcmd("SITE CHMOD " + permisos + " " + file_name)
		elif cmd == "mv":
			salida = ftp.rename(current_name, last_name)
		elif cmd == "rmdir":
			ftp.rmd(dir_name)
		elif cmd == "del":
			ftp.delete(file_name)
		elif cmd == "mkdir":
			ftp.mkd(dir_name)
			ftp.cwd(dir_name)
			ftp.dir(data.append)
			for item in data:
				salida = salida + item + "\n"
		else:
			sublime.message_dialog("Comando incorrecto")
		ftp.quit()

	# if contador_uso > 9:
	# 	if sublime.message_dialog("Ni verga tienes que pagarme"):
	# 		print ("Pagar")
	# 	else:
	# 		print ("Jajaja")
	# else:
	# 	print(str(contador_uso) + "")
	# 	contador_uso = contador_uso + 1
	return salida

class SideBar(sublime_plugin.WindowCommand):
	def run(self, paths = []):
		pass

	def is_visible(self, paths = []):
		print(paths)
		return True

	def is_enabled(self, paths = []):
		return False

def get_list_servers():
	archivos = []
	for arch in os.listdir( sublime.packages_path() + "/User" ):
		if os.path.isfile(os.path.join(mydir, arch)):
			filename, file_extension = os.path.splitext(arch)
			if file_extension == ".json":
				archivos.append(filename)
	return archivos

def createFile(phat, content):
	file = open(phat, 'w')
	file.write(content)
	file.close()

def readFile(phat):
	file = open(phat, 'r')
	content = file.read()
	file.close()
	return content


class SetConfig(sublime_plugin.TextCommand):
	def run(self, edit, file_json):
		global mydir, currentPath, puerto, usuario, nick, password, host, tipo, str_json_config

		json_file = json.loads( readFile(file_json) )

		tipo = json_file[0]["type"]

		if tipo != "sftp" and tipo != "ftp":
			sublime.message_dialog("Tipo de conexión invalida.")
			flag_config = False
			return

		host = json_file[0]["host"]
		usuario = json_file[0]["user"]
		nick = json_file[0]["nick"]

		if nick == "":
			sublime.message_dialog("Es necesario que coloques un Nick.")
			flag_config = False
			return

		password = json_file[0]["password"]
		puerto = json_file[0]["port"]
		if currentPath == '':
			currentPath = json_file[0]["remote_path"]
		if host != "" and host != json_file[0]["host"] and usuario != "" and usuario != json_file[0]["user"]:
			currentPath = json_file[0]["remote_path"]

		str_json_config = "[{\n\t\"nick\" : \"" + nick + "\",\n\t\"type\" : \"" + tipo + "\",\n\t\"host\" : \"" + host + "\",\n\t\"user\" : \"" + usuario + "\",\n\t\"password\" : \"" + password + "\",\n\t\"port\" : \"" + puerto + "\",\n\t\"remote_path\" : \"" + currentPath + "\"\n}]"
		if usuario == None or usuario == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
		if host == None or host == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
		if password == None or password == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el password en el archivo de configuración"})
		if usuario == None or usuario == '' or host == None or host == '' or password == None or password == '': 
			flag_config = False
			return
