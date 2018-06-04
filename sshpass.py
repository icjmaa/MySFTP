
import os
import sys

_b = sys.version_info[0] < 3 and (lambda x:x) or (lambda x:x.encode('utf-8'))

def ssh_exec_pass(password, args, capture_output=False):
	import pty, select
	log = ['init']
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
		
		os.execvp(args[0], args)
	
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

	aux = False
	try:
		while rd_fds:

			rd_ready, _, _ = select.select(rd_fds, [], [], 1)
			
			log.append("1. Status rd_ready:" + str(rd_ready))
			if rd_ready == [] and args[2].find("ls -lrt") != -1:
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
						os.write(pty_fd, _b(password + '\n'))
						log.append("Se escribio la contraseña")
					elif b're you sure you want to continue connecting' in data:
						os.write(pty_fd, b'yes\n')
						log.append("Se dijo que si se queria continuar")

				
				# Deal with stdout
				data = _read(stdout_fd)
				if data is not None:
					if capture_output:
						output.extend(data)
						log.append("Data is not none y se agrega a la salida")
					else:
						log.append("Queee")
						sys.stdout.write(data.decode('utf-8', 'ignore'))
						
				
				data = _read(stderr_fd)
				if data is not None:
					if rd_ready[0] == stderr_fd:
						if b'onnected to' in data:
							os.write(pty_fd, _b(args[2] + '\n'))
							log.append("Se logro la conexion")
					else:
						sys.stderr.write(data.decode('utf-8', 'ignore'))
						log.append("No se que pedorron")
					if b'Could not resolve hostname' in data:
						log.append("No se resolvio el nombre de dominio")
						output.extend(data)
			else:
				log.append("Se hizo un break")
				break
	finally:
		log.append("Crasheo")
		os.close(pty_fd)
		
	pid, retval = os.waitpid(pid, 0)
	return retval, output, log