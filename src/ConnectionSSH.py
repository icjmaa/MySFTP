import os
import sys
from .Configuration import Configuration
try:
	import pty, select
except Exception as e:
	print(e)


_b = sys.version_info[0] < 3 and (lambda x:x) or (lambda x:x.encode('utf-8'))

class ConnectionSSH():

	@staticmethod
	def ssh_exec(args, capture_output=False):
		log = []
		# [
		#	0. "sftp",
		#	***. Connection.usuario + "@" + Connection.host, Antes se mandaba este parametro
		#	1. "cd " + currentPath + " && ls -lrt | sed '/ \.$/d' | sed '/ \.\.$/d'"
		#]
		#args = [arguments[0], "-p " + Configuration.puerto, Configuration.usuario + "@" + Configuration.host, arguments[1]]
		program = args[0] # sftp or ssh
		port = '-P ' + Configuration.puerto
		user_host = Configuration.usuario + "@" + Configuration.host
		command_remote = "cd '{}'".format(Configuration.currentPath) + args[1]
		log.append("\n".join(args))
		# create pipe for stdout
		stdout_fd, w1_fd = os.pipe()
		stderr_fd, w2_fd = os.pipe()
		
		pid, pty_fd = pty.fork()
		if not pid:
			log.append("if Not pid")
			os.close(stdout_fd)
			os.close(stderr_fd)
			os.dup2(w1_fd, 1)
			os.dup2(w2_fd, 2)
			os.close(w1_fd)
			os.close(w2_fd)
			
			if program == 'sftp':
				os.execvp(program, [program, port, user_host])
			elif program == 'ssh':
				os.execvp(program, [program, user_host, command_remote])
		
		os.close(w1_fd)
		os.close(w2_fd)
		
		output = bytearray()
		rd_fds = [stdout_fd, stderr_fd, pty_fd]

		def _read(fd):
			if fd not in rd_ready:
				return 

			try:
				data = os.read(fd, 128*1024)
			except (OSError, IOError, Exception):
				data = None

			if not data:
				rd_fds.remove(fd)

			return data

		try:
			time_out = 1.76
			log.append(str(rd_fds))
			while rd_fds:

				rd_ready, _, _ = select.select(rd_fds, [], [], time_out)
				
				log.append("1. Status rd_ready:" + str(rd_ready))
				if rd_ready == [] and command_remote.find("ls -lrt") != -1:
					limit = 0
					while limit <= 10 and rd_ready == []:
						rd_ready, _, _ = select.select(rd_fds, [], [], 1)
						limit = limit + 1
					log.append("2. Status rd_ready:" + str(rd_ready))
				
				if rd_ready:
					# Deal with prompts from pty
					data = _read(pty_fd)
					if data is not None:
						if b'assword:' in data:
							os.write(pty_fd, _b(Configuration.password + '\n'))
							log.append("Se escribio la contraseña")
						elif b're you sure you want to continue connecting' in data:
							os.write(pty_fd, b'yes\n')
							log.append("Se dijo que si se quería continuar")

					# Deal with stdout
					data = _read(stdout_fd)
					if data is not None:
						if capture_output:
							output.extend(data)
							log.append("Data is not none y se agrega a la salida")
							time_out = 1.28
						else:
							log.append("Data is not none no se agrega a la salida")
							sys.stdout.write(data.decode('utf-8', 'ignore'))

					# Mensajes del promp
					data = _read(stderr_fd)
					if data is not None:
						if rd_ready[0] == stderr_fd and b'onnected to' in data:
							os.write(pty_fd, _b(command_remote + '\n'))
							log.append("Se logro la conexion")
						elif rd_ready[0] == stderr_fd and b'Permission denied, please try again.' in data:
							log.append("Error al ingresar la contraseña")
							output.extend(b'Usuario o password incorrectos')
							break
						elif rd_ready[0] == stderr_fd and (
								b'Could not resolve hostname' in data
							or b'No route to host' in data
							or b'Network is unreachable' in data
							or b': Permission denied' in data
							or b'No such file or directory' in data
							or b'not found.' in data
							or b'Couldn\'t delete file: Failure' in data):
							log.append("La terminal regresa error.")
							output.extend(data)
						else:
							sys.stderr.write(data.decode('utf-8', 'ignore'))
							log.append("Error no identificado, se describe data a continuación")
							log.append( str( data.decode('utf-8', 'ignore') ) )
							log.append(str(stderr_fd))
							log.append(str(rd_ready[0]))
				else:
					log.append("Se hizo un break")
					break
		finally:
			log.append("Crasheo")
			os.close(pty_fd)
			
		pid, retval = os.waitpid(pid, 0)
		return retval, output, log
