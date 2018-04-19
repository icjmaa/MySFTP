MySFTP
================

Plugin de Sublime Text para manejo de archivos mediante conexión SFTP/FTP [Develope for Juan Manuel](https://github.com/icjmaa)
    
    # Uso totalmente gratuito. 
:muscle: :sunglasses: :punch:
<p align="center"><img src ="https://upload.wikimedia.org/wikipedia/en/d/d2/Sublime_Text_3_logo.png" width="128px"/></p>

Modo de uso.
-------------------

- Desde el menu de Sublime Text: Archivo > MySftp
    - **Nuevo Servidor :** Creamos un archivo de configuración para la conexion SFTP/FTP con nuestro servidor.
        - **Nick :** Nombre de usuario que ocupara los archivo.
        - **type :** Tipo de conexion con el servidor (SFTP o FTP).
        - **host :** IP(v4) o Nombre de dominio del servidor al que se desea conectar.
        - **user :** Nombre de usuario con el que va a logearse para realizar la conexion.
        - **password :** Contraseña con la que va a logearse el usuario antes asignado para el logeo.
        - **port :** Puerto que se va utilizar para la conexion por defecto 22 para SFTP y 21 para FTP.
        - **remote_path :** Ruta principal del servidor que va a listarse.

    - **Listar Servidor :** Lista los servidores previamente configurados. 
    - **Editar Servidor :** Nos permite realizar cambios en la configuracion de los servidores existentes.
    - **Eliminar Servidor :** Elimina las configuraciones de los servidores.

- Conbinacion de Teclas
    - Utilize la conbinación de teclas <kbd>Ctrl+Alt+L</kbd> , <kbd>Ctrl+Alt+S</kbd>, para listar los servidores configurados.

## Navegación

1. Pulse la tecla **Enter** sobre el servidor que desea trabajar, inmediatamente se listara el directorio asignado como prncipal en el archio de configuración.
2. Puede escoger entre las siguientes opciones:
    - Cambiar de servidor.
    - Subir de nivel el directorio actual.
    - Crear un archivo nuevo en el directorio actual.
    - Crear una nueva carpeta en el directorio actual.
    - Renombrar el directorio actual.
    - Cambiar permisos al directorio actual.
    - Eliminar eliminar el directorio actual.
    
    \( Las ultimas 6 opciones requieren permisos en servidores linux \)
3. Si selecciona un archivo de la lista podra realizar las siguientes acciones:
    - Cambiar de servidor.
    - Regresar a la lista anterior.
    - Editar, se abrira en una pestaña nueva, cuando se guarde automaticamente este se actualizara en el servidor.
    - Renombrar el archivo en el servidor.
    - Cambiar permisos para el archivo seleccionado.
    - Eliminar archivo seleccionado en el servidor.
    
    \( Las ultimas 4 opciones requieren permisos en servidores linux \)
4. Si selecciona un directorio se desplegara el mismo menu del paso 2.

Estado
-------------------

En Desarrollo :computer: :coffee:

[![Build Status](https://img.shields.io/travis/SublimeLinter/SublimeLinter/master.svg)](https://github.com/icjmaa/MySFTP)
