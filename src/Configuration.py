import json
from .extras import readFile, Debug, getPath

class Configuration():
	flag_config = False

	package_path = ''
	mysftp_path = ''
	tmp_path = ''
	servers_path = ''
	psftp_path = ''

	tipo = 'ftp'
	usuario = 'root'
	host = '127.0.0.1'
	puerto = 21
	password = ''
	nick = ''
	currentPath = ''

	snippet = [{
		'nick': '${1:root}',
		'type': '${2:[sftp|ftp]}',
		'host': '${3:[ip_host|server_host_name|domain]}',
		'user': '${4:usuario}',
		'password': '${5:contraseña}',
		'port': '${6:puerto}',
		'remote_path': '${7:/var/www/html/}'
	}]

	def __init__(self, config):
		self.tipo = config[0]['type']
		self.host = config[0]['host']
		self.usuario = config[0]['user']
		self.puerto = config[0]['port']
		self.nick = config[0]['nick']
		self.password = config[0]['password']
		self.currentPath = config[0]['remote_path']

	@staticmethod
	def setConfig(json_config_file):
		json_file = json.loads( readFile(json_config_file) )
		Configuration.tipo = json_file[0]['type']
		if Configuration.tipo != 'sftp' and Configuration.tipo != 'ftp':
			sublime.message_dialog('Tipo de conexión invalida.')
			Configuration.flag_config = False
			return

		if Configuration.currentPath == '':
			Debug.print("Esta vació.")
			Configuration.currentPath = getPath(json_file[0]['remote_path'])
		if Configuration.host != "" and Configuration.host != json_file[0]["host"] and Configuration.usuario != "" and Configuration.usuario != json_file[0]["user"]:
			Configuration.currentPath = getPath(json_file[0]['remote_path'])

		Configuration.host = json_file[0]['host']
		Configuration.usuario = json_file[0]['user']
		Configuration.nick = json_file[0]['nick']

		if Configuration.nick == "":
			sublime.message_dialog('Es necesario que coloques un Nick.')
			Configuration.flag_config = False
			return

		Configuration.password = json_file[0]['password']
		Configuration.puerto = json_file[0]['port']

		if Configuration.usuario == None or Configuration.usuario == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
		if Configuration.host == None or Configuration.host == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el servidor host en el archivo de configuración"})
		if Configuration.password == None or Configuration.password == '':
			self.window.run_command("progress_bar", {"mensaje" : "No se ha definido el password en el archivo de configuración"})
		if Configuration.usuario == None or Configuration.usuario == '' or Configuration.host == None or Configuration.host == '' or Configuration.password == None or Configuration.password == '': 
			Configuration.flag_config = False
			return
		Configuration.flag_config = True

	@staticmethod
	def getJsonConfig():
		return json.dumps([{
				'nick': Configuration.nick,
				'type': Configuration.tipo,
				'host': Configuration.host,
				'user': Configuration.usuario,
				'password': Configuration.password,
				'port': Configuration.puerto,
				'remote_path': Configuration.currentPath
			}],
			indent='\t'
		)