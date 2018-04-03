#
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
import zipfile

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

class MySftp(sublime_plugin.TextCommand):
	def run(self, edit):
		global mydir
		global diagonal
		global tmp_dir
		#sublime.message_dialog( str(datetime.datetime.now()) )
		mydir = sublime.packages_path() + "/User"

		zip_ref = zipfile.ZipFile(os.path.dirname(os.path.abspath(__file__)), 'r')
		if not os.path.exists(sublime.packages_path() + "/MySFTP/Monokai.tmTheme"):
			zip_ref.extract("Monokai.tmTheme",sublime.packages_path() + "/MySFTP")
		if not os.path.exists(sublime.packages_path() + "/MySFTP/MySFTP.tmLanguage"):
			zip_ref.extract("MySFTP.tmLanguage",sublime.packages_path() + "/MySFTP")

		for name in zip_ref.namelist():
			if name.startswith('bin/') and not os.path.exists(sublime.packages_path() + "/MySFTP/" + name):
				zip_ref.extract(name,sublime.packages_path() + "/MySFTP")
		zip_ref.close()
		
		if platform.system() == "Linux":
			diagonal = "/"
			tmp_dir = mydir + diagonal + "tmp_my_sftp"

		#Mostramos los servidores disponibles
		archivos = ""
		for arch in os.listdir(mydir):
			if os.path.isfile(os.path.join(mydir, arch)):
				filename, file_extension = os.path.splitext(arch)
				if file_extension == ".json":
					archivos = archivos + ( "," if len(archivos) > 0 else "")
					archivos = archivos + filename
		self.view.window().run_command("show_servers", {"args" : archivos});

class SyncFiles(sublime_plugin.WindowCommand):
	def run(self, comando):
		global currentPath
		global puerto
		global usuario
		global nick
		global password
		global host
		global tipo
		file = os.path.basename(self.window.active_view().file_name())

		if comando == "put_sftp":
			self.window.run_command("save");
			return
		json_config = open(tmp_dir + diagonal + os.path.splitext(file)[0] + ".config","r");
		json_file = json.loads(json_config.read())#leemos el archivo de configuración
		json_config.close()

		tipo = json_file[0]["type"]
		if tipo != "sftp" and tipo != "ftp":
			sublime.message_dialog("Tipo de conexión invalida.")
			return
		host = json_file[0]["host"]
		usuario = json_file[0]["user"]
		nick = json_file[0]["nick"]
		if nick == "":
			sublime.message_dialog("Es necesario que coloques un Nick.")
			return
		password = json_file[0]["password"]
		puerto = json_file[0]["port"]
		currentPath = json_file[0]["remote_path"]

		if usuario == None or usuario == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
			return
		if host == None or host == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
			return
		if password == None or password == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el password en el archivo de configuración"})
			return

		if createPanelOutput == False:
			self.window.run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
			self.window.run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
		#Aqui listamos mostramos la lista de elementos comando ls
		self.window.run_command("get_sftp",{"file" : file, "flag" : True})

	def is_visible(self, paths = []):
		if os.path.dirname(self.window.active_view().file_name()) != tmp_dir:
			return False
		else:
			return True


class showServers(sublime_plugin.WindowCommand):
	listServers = []
	def run(self,args):
		global listServers
		listServers = []
		if args != "":
			listServers = args.split(",")
		listServers.insert(0,"Nuevo servidor.")
		quick_list = [option for option in listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,self.on_done,0)

	def on_done(self,index):
		global mydir
		global currentPath
		global puerto
		global usuario
		global nick
		global password
		global host
		global tipo

		if index == 0:
			self.window.run_command('new_server')
		elif index > 0:
			json_config = open(mydir + diagonal + listServers[index] + ".json","r");
			json_file = json.loads(json_config.read())#leemos el archivo de configuración
			json_config.close()

			tipo = json_file[0]["type"]
			if tipo != "sftp" and tipo != "ftp":
				sublime.message_dialog("Tipo de conexión invalidaaaa.")
				return

			if (currentPath == "") or (host != "" and host != json_file[0]["host"] and usuario != "" and usuario != json_file[0]["user"]):
				currentPath = json_file[0]["remote_path"]

			host = json_file[0]["host"]
			usuario = json_file[0]["user"]
			nick = json_file[0]["nick"]
			if nick == "":
				sublime.message_dialog("Es necesario que coloques un Nick.")
				return
			password = json_file[0]["password"]
			puerto = json_file[0]["port"]

			if usuario == None or usuario == '':
				self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
				return
			if host == None or host == '':
				self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
				return
			if password == None or password == '':
				self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el password en el archivo de configuración"})
				return

			if createPanelOutput == False:
				self.window.run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
				self.window.run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
			#Aqui listamos mostramos la lista de elementos comando ls
			self.window.run_command("progress_bar", {"mensaje" : "\nListando el directorio: " + currentPath})
			salida = SFTP("cd " + currentPath + "\nls\n", tipo, "ls")
			if salida == False:
				self.window.run_command("progress_bar", {"mensaje" : "    error\nImposible conectar con el servidor por el momento."})
				return
			self.window.run_command("show_ls",{"args" : salida});



class showLs(sublime_plugin.WindowCommand):
	list_files = []
	def run(self,args):
		global list_files
		global optionsFolders
		global currentPath
		list_files = []
		lista = args.split("\n")

		for item in range(3,len(lista) - 1):
			file = lista[item]
			if self.limpiarCadena(file)[0] == 'd':
				if len(self.limpiarCadena(file).split(" ")) == 9:
					name_file = self.limpiarCadena(file).split(" ")[8] + "/"
			else:
				if len(self.limpiarCadena(file).split(" ")) == 9:
					name_file = self.limpiarCadena(file).split(" ")[8]
					
			if len(self.limpiarCadena(file).split(" ")) == 9:
				if name_file[0] != '.':
					list_files.append(name_file)

		list_files.sort()
		orden_dir = []
		cntAux = 0;
		for item in list_files:
			if item[-1:] == "/":
				orden_dir.insert(cntAux,item)
				cntAux = cntAux + 1
			else:
				orden_dir.append(item)
		list_files = orden_dir

		self.Options = ["Directorio: " + currentPath] + optionsFolders + list_files
		quick_list = [option for option in self.Options]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,lambda id : self.on_done(id, args),0)

	def on_done(self,index, args):
		global currentPath
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
		if index == 1: #change server
			self.window.run_command("my_sftp");
		elif index == 2:# Up Level
			upLevel = os.path.normpath(os.path.join(currentPath,"../")).replace("\\", "/") + "/"
			self.window.run_command("progress_bar", {"mensaje" : "\nListando el directorio: " + upLevel})
			currentPath = upLevel
			salida = SFTP("cd " + upLevel + "\nls\n", tipo, "ls")
			if salida == False:
				self.window.run_command("progress_bar", {"mensaje" : "    error\nImposible conectar con el servidor por el momento."})
				return
			currentPath = upLevel
			self.window.run_command("show_ls",{"args" : salida});
		elif index == 3:# Nuevo Archivo
			self.window.run_command("new_file_sftp")
		elif index == 4:# Nuevo directorio
			self.window.run_command("new_dir_sftp")
		elif index == 5:# Renombrar
			self.window.run_command("rename_sftp", {"archivo" : currentPath})
		elif index == 6:# Cambiar Permisos
			self.window.run_command("chmod_sftp", {"filename" : currentPath})
		elif index == 7:# Eliminar
			self.window.run_command("remove_sftp", {"file" : currentPath, "is_file" : False})

	def file_selected(self, index, index_file, args):
		if index == 1: # Change server
			self.window.run_command("my_sftp");
		elif index == 2: #"Back to List"
			self.window.run_command("show_ls",{"args" : args});
		elif index == 3:#"Editar"
			self.window.run_command("get_sftp",{"file" : list_files[index_file]})
		elif index == 4:#"Renombrar"
			self.window.run_command("rename_sftp", {"archivo" : list_files[index_file]})
		elif index == 5:#"Cambiar Permisos"
			self.window.run_command("chmod_sftp", {"filename" : list_files[index_file]})
		elif index == 6:#"> Eliminar"
			self.window.run_command("remove_sftp", {"file" : list_files[index_file], "is_file" : True})

	def limpiarCadena(self,texto):
		ant = None
		limpio = ""
		for i in range(0,len(texto)):
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
	def run(self,edit,file, flag = False):
		global createPanelOutput
		#flag_edit = True
		self.view.window().run_command("progress_bar", {"mensaje" : "\nDescargando: " + currentPath + file + " en " + tmp_dir + diagonal + file, "change" : False, "loading" : True})
		
		if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)#Cramos la carpeta temporal
		##############################################################################

		salida = SFTP("cd " + currentPath + "\nls\n", tipo, "ls")
		if salida.find(file + ".sftp") > 0:#Validamos que exista el archivo
			salida = SFTP("cd " + currentPath + "\nget " + file + ".sftp" + " " + tmp_dir + diagonal + file + ".sftp", tipo, "get")
			nick_use = open(tmp_dir + diagonal + file + ".sftp","r")
			nick_current_use = nick_use.read() 
			nick_use.close()
			if os.path.exists(tmp_dir + diagonal + file + ".sftp"):
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
			nick_use = open(tmp_dir + diagonal + file + ".sftp","w")
			nick_use.write(nick) 
			nick_use.close()
			self.view.window().run_command("put_sftp",{"file" : tmp_dir + diagonal + file + ".sftp", "flag" : True})
			if os.path.exists(tmp_dir + diagonal + file + ".sftp"):
				os.remove(tmp_dir + diagonal + file + ".sftp")

			#Aqui listamos mostramos la lista de elementos comando ls
			salida = SFTP("cd " + currentPath + "\nget " + file + " " + tmp_dir + diagonal + file, tipo, "get")
			if salida == "permission denied":
				self.view.window().run_command("progress_bar", {"mensaje" : "    error\nNo tiene los permisos necesarios."})
				return
		aux_path = open(tmp_dir + diagonal + os.path.splitext(file)[0] + ".path","w")
		aux_path.write(currentPath) 
		aux_path.close()

		aux_config = open(tmp_dir + diagonal + os.path.splitext(file)[0] + ".config","w")
		aux_config.write("[{\n\t\"nick\" : \"" + nick + "\",\n\t\"type\" : \"" + tipo + "\",\n\t\"host\" : \"" + host + "\",\n\t\"user\" : \"" + usuario + "\",\n\t\"password\" : \"" + password + "\",\n\t\"port\" : \"" + puerto + "\",\n\t\"remote_path\" : \"" + currentPath + "\"\n}]")
		aux_config.close()

		#------------------------------------------------------
		if createPanelOutput == False:
			self.window.create_output_panel("progess_bar")
			createPanelOutput = True
		self.view.window().run_command("show_panel", {"panel": "output.progess_bar"})

		def show_progress_bar():
			show_progress_bar.message = "    "
			show_progress_bar.change = True
			vista = self.view.window().open_file(tmp_dir + diagonal + file)
			while vista.is_loading():
				view = self.view.window().find_output_panel("progess_bar")
				view.run_command("my_insert_progress_bar", {"message" : show_progress_bar.message, "change" : show_progress_bar.change})
		sublime.set_timeout_async(show_progress_bar, 1)

class MySftpLoad(sublime_plugin.EventListener):
	def on_load(self,view):
		ruta = view.file_name()
		if os.path.dirname(ruta) == tmp_dir:
			view.window().run_command("progress_bar", {"mensaje" : "success", "change" : True, "loading" : False})

class MySftpSave(sublime_plugin.EventListener):
	def on_post_save(self,view):
		view.run_command("put_sftp", {"file" : "", "flag" : False })
	def on_close(self,view):
		ruta = view.file_name()
		if os.path.dirname(ruta) == tmp_dir and view.is_dirty() == False:
			view.run_command("remove_sftp", {"file" : os.path.basename(ruta) + ".sftp", "is_file" : True})
			os.remove(ruta)
			os.remove(os.path.splitext(ruta)[0] + ".path")
			os.remove(os.path.splitext(ruta)[0] + ".config")

class putSftp(sublime_plugin.TextCommand):
	def run(self, edit, file , flag):
		global mydir
		global currentPath
		global createPanelOutput
		global host
		global password
		global usuario
		global nick
		global puerto
		global tipo
		global tmp_dir
		global diagonal
		mydir = sublime.packages_path() + "/User"
		
		if platform.system() == "Linux":
			diagonal = "/"
			tmp_dir = mydir + diagonal + "tmp_my_sftp"

		#flag sabemos si hay nombre de archivo o no
		
		if flag == True:
			ruta = file.replace(".sftp", "")
		else:
			ruta = self.view.window().active_view().file_name()

		if os.path.dirname(ruta) == tmp_dir:
			#Es un archivo de la carpeta de temporales
			path_put = currentPath
			if flag == False:
				#mydir = os.path.dirname(os.path.abspath(__file__))
				file_path = open( os.path.splitext(ruta)[0] + ".path" , "r")
				path_put = file_path.read()
				file_path.close()

				json_config = open( os.path.splitext(ruta)[0] + ".config" , "r")
				json_file = json.loads(json_config.read())#leemos el archivo de configuración
				json_config.close()
				if host == '' or usuario == '' or password == '' or host != json_file[0]["host"] or usuario != json_file[0]["user"] or password != json_file[0]["password"]:
					tipo = json_file[0]["type"]

					if tipo != "sftp" and tipo != "ftp":
						sublime.message_dialog("Tipo de conexión invalida.")
						return
					host = json_file[0]["host"]
					usuario = json_file[0]["user"]
					nick = json_file[0]["nick"]
					password = json_file[0]["password"]
					puerto = json_file[0]["port"]
					currentPath = json_file[0]["remote_path"]

					if usuario == None or usuario == '':
						self.view.window().run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
						return
					if host == None or host == '':
						self.view.window().run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
						return
					if password == None or password == '':
						self.view.window().run_command("progress_bar", {"mensaje" : "No se ha definido el password en el archivo de configuración"})
						return

					if createPanelOutput == False:
						self.view.window().run_command("progress_bar", {"mensaje" : "Conectando con el servidor"})
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
					else:
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectando con el servidor"})
						self.view.window().run_command("progress_bar", {"mensaje" : "\nConectado en: " + host + " como: " + usuario})
					#Aqui listamos mostramos la lista de elementos comando ls

			#Es un archivo de la carpeta de temporales
			##############################################################################
			salida = SFTP("cd " + currentPath + "\nls\n", tipo, "ls")
			if salida.find(os.path.basename(ruta) + ".sftp") > 0:#Validamos que exista el archivo
				salida = SFTP("cd " + currentPath + "\nget " + os.path.basename(ruta) + ".sftp" + " " + tmp_dir + diagonal + os.path.basename(ruta) + ".sftp", tipo, "get")
				nick_use = open(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp" ,"r")
				nick_current_use = nick_use.read() 
				nick_use.close()
				if nick != nick_current_use and flag == False:
					if not sublime.ok_cancel_dialog("El usuario " + nick_current_use + " esta usando actualmente el archivo, Deseas subir tus cambios?."):
						self.view.window().run_command("progress_bar", {"mensaje" : "    Cancel."})
						return
			nick_use = open(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp", "w")
			nick_use.write(nick) 
			nick_use.close()
			salida = SFTP("cd " + "\n" +  "put " + tmp_dir + diagonal + os.path.basename(ruta) + ".sftp" + " " + currentPath + os.path.basename(ruta) + ".sftp", tipo, "put")

			if 'nick_current_use' in locals():
				if nick != nick_current_use:
					os.remove(tmp_dir + diagonal + os.path.basename(ruta) + ".sftp")
			##############################################################################
			if flag == False:
				self.view.window().run_command("progress_bar", {"mensaje" : "\nSubiendo: " + ruta + " en " + path_put + os.path.basename(ruta), "change" : False, "loading" : True})
				salida = SFTP("cd " + "\n" +  "put " + ruta + " " + path_put + os.path.basename(ruta), tipo, "put")
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
			new_file = open(tmp_dir + diagonal + name_file ,"w")
			new_file.close()
			aux_path = open(tmp_dir + diagonal + os.path.splitext(name_file)[0] + ".path","w")
			aux_path.write(currentPath) 
			aux_path.close()

			aux_config = open(tmp_dir + diagonal + os.path.splitext(name_file)[0] + ".config","w")
			aux_config.write("[{\n\t\"nick\" : \"" + nick + "\",\n\t\"type\" : \"" + tipo + "\",\n\t\"host\" : \"" + host + "\",\n\t\"user\" : \"" + usuario + "\",\n\t\"password\" : \"" + password + "\",\n\t\"port\" : \"" + puerto + "\",\n\t\"remote_path\" : \"" + currentPath + "\"\n}]")
			aux_config.close()

			def esperando():
				vista = self.window.open_file(tmp_dir + diagonal + name_file)
				while vista.is_loading():
					print("Hola")
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

class EditServer(sublime_plugin.WindowCommand):
	listServers = []
	def run(self):
		global mydir
		global listServers
		mydir = sublime.packages_path() + "/User"
		#Mostramos los servidores disponibles
		archivos = ""
		for arch in os.listdir(mydir):
			if os.path.isfile(os.path.join(mydir, arch)):
				filename, file_extension = os.path.splitext(arch)
				if file_extension == ".json":
					archivos = archivos + ( "," if len(archivos) > 0 else "")
					archivos = archivos + filename

		listServers = archivos.split(",")
		quick_list = [option for option in listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,self.on_done,0)

	def on_done(self,index):
		if index == -1:
			print("Presionaste ESC :D")
		else:
			self.window.open_file(mydir + diagonal + listServers[index] + ".json")

class DeleteServer(sublime_plugin.WindowCommand):
	listServers = []
	def run(self):
		global mydir
		global listServers
		mydir = sublime.packages_path() + "/User"
		#Mostramos los servidores disponibles
		archivos = ""
		for arch in os.listdir(mydir):
			if os.path.isfile(os.path.join(mydir, arch)):
				filename, file_extension = os.path.splitext(arch)
				# print(arch + "," + filename + "," + file_extension)
				if file_extension == ".json":
					archivos = archivos + ( "," if len(archivos) > 0 else "")
					archivos = archivos + filename

		listServers = archivos.split(",")
		# self.Options = lista
		quick_list = [option for option in listServers]
		self.quick_list = quick_list
		self.window.show_quick_panel(quick_list,self.on_done,0)

	def on_done(self,index):
		if index != -1:
			os.remove(mydir + diagonal + listServers[index] + ".json")

class NewServer(sublime_plugin.WindowCommand):
	def run(self):
		global contador_uso
		vista = self.window.new_file()
		self.window.run_command('insert_snippet',{"contents": "[{\n\t\"nick\" : \"" + nick + "\",\n\t\"type\" : \"" + tipo + "\",\n\t\"host\" : \"${1:[ip_host:host_name]}\",\n\t\"user\" : \"${2:usuario}\",\n\t\"password\" : \"${3:contraseña}\",\n\t\"port\" : \"${4:puerto}\",\n\t\"remote_path\" : \"${5:/var/www/html/}\"\n}]"})
		vista.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")

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
		view.settings().set("color_scheme","Packages/MySFTP/Monokai.tmTheme")
		view.set_syntax_file("Packages/MySFTP/MySFTP.tmLanguage")
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

#Función global SFTP
def SFTP(comando, type = "sftp", cmd = ""):
	global puerto
	global usuario
	global password
	global host
	global contador_uso
	global tipo
	salida = ""

	if tipo == "sftp":
		if platform.system() == "Linux":
			#sublime.message_dialog( platform.system() )
			if cmd == "ls":
				retorno = ssh_exec_pass(password, ["ssh", usuario + "@" + host, "cd " + currentPath + " && ls -lrt"], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') )
			elif cmd == "get":
				array_comando = comando.split("\n")[1]
				file_server = array_comando.split(' ')[1]
				file_local = array_comando.split(' ')[2]
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nget " + file_server + " " + file_local], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 
			elif cmd == "put":
				array_comando = comando.split("\n")[1]
				file_local = array_comando.split(' ')[1]
				file_server = array_comando.split(' ')[2]
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nput " + file_local + " " + file_server], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 
			elif cmd == "chmod":
				array_comando = comando.split("\n")[1]
				permisos = array_comando.split(' ')[1]
				file_name = array_comando.split(' ')[2]
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nchmod " + permisos + " " + file_name], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 
			elif cmd == "mv":
				array_comando = comando.split("\n")[1]
				current_name = array_comando.split(' ')[1]
				last_name = array_comando.split(' ')[2]

				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrename " + current_name + " " + last_name], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 

			elif cmd == "rmdir":
				array_comando = comando.split("\n")
				dir_name = array_comando[1].split(' ')[1]
				
				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrmdir " + dir_name], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') )
			elif cmd == "del":
				array_comando = comando.split("\n")
				file_name = array_comando[1].split(' ')[1]

				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nrm " + file_name], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 

			elif cmd == "mkdir":
				array_comando = comando.split("\n")
				dir_name = array_comando[1].split(' ')[1]

				retorno = ssh_exec_pass(password, ["sftp", usuario + "@" + host, "cd " + currentPath + "\nmkdir " + dir_name], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 

				retorno = ssh_exec_pass(password, ["ssh", usuario + "@" + host, "cd " + currentPath + dir_name + " && ls -lrt"], True)
				salida = str( retorno[1].decode('utf-8', 'ignore') ) 
			else:
				sublime.message_dialog("Comando incorrecto")

			if salida.find("Could not resolve hostname") != -1:
				print(salida)
				return False
			elif salida.find("total") == -1:
				print(salida)
				return False
		else:
			try:
				scrip_file = open(sublime.packages_path() + "\\User\\script.bat","w")
				scrip_file.write(comando)
				scrip_file.close()

				proceso = subprocess.Popen([sublime.packages_path() + "\\MySFTP\\bin\\psftp.exe" ,"-P" , puerto, "-pw", password, "-b" , sublime.packages_path() + "\\User\\script.bat", usuario + "@" + host], stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				proceso.wait( 5 )
				errores = proceso.stderr.read()
				salida = proceso.stdout.read()
				proceso.stderr.close()
				proceso.stdout.close()
				errores = errores.decode(sys.getdefaultencoding())
				print("Errores: " + errores)
				salida = salida.decode(sys.getdefaultencoding()) #Salida del comando
			except subprocess.TimeoutExpired as e:
				salida = "Usuario o password incorrectos."
				return False
				raise e

			if salida.find("Network error: Connection timed out") != -1:
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
		if cmd == "ls":
			ftp.dir(data.append)
			ftp.quit()
			for item in data:
				salida = salida + item + "\n"
		elif cmd == "get":
			array_comando = comando.split("\n")[1]
			file_server = array_comando.split(' ')[1]
			file_local = array_comando.split(' ')[2]
			fhandle = open(file_local, 'wb')
			ftp.retrbinary('RETR ' + file_server , fhandle.write)
			fhandle.close()

			ftp.quit()
		elif cmd == "put":
			array_comando = comando.split("\n")[1]
			file_local = array_comando.split(' ')[1]
			file_server = array_comando.split(' ')[2]
			with open(file_local, "rb") as f:
				ftp.storlines("STOR " + file_server, f)

			ftp.quit()
		elif cmd == "chmod":
			array_comando = comando.split("\n")[1]
			permisos = array_comando.split(' ')[1]
			file_name = array_comando.split(' ')[2]
			salida = ftp.sendcmd("SITE CHMOD " + permisos + " " + file_name)

			ftp.quit()
		elif cmd == "mv":
			array_comando = comando.split("\n")[1]
			current_name = array_comando.split(' ')[1]
			last_name = array_comando.split(' ')[2]
			salida = ftp.rename(current_name, last_name)

			ftp.quit()
		elif cmd == "rmdir":
			array_comando = comando.split("\n")
			dir_name = array_comando[1].split(' ')[1]
			ftp.rmd(dir_name)
			ftp.quit()
		elif cmd == "del":
			array_comando = comando.split("\n")
			file_name = array_comando[1].split(' ')[1]
			ftp.delete(file_name)
			ftp.quit()
		elif cmd == "mkdir":
			array_comando = comando.split("\n")
			dir_name = array_comando[1].split(' ')[1]
			ftp.mkd(dir_name)
			ftp.cwd(dir_name)
			ftp.dir(data.append)
			ftp.quit()
			for item in data:
				salida = salida + item + "\n"
		else:
			sublime.message_dialog("Comando incorrecto")

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
