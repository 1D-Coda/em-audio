EM-Audio — validación independiente en Windows
==============================================

Gracias por hacer esto. Son unos 25 a 40 minutos de máquina y casi nada de tu
tiempo.


QUÉ NECESITAS
-------------

Docker Desktop, de docker.com. Ábrelo una vez y espera a que diga "Running".

Nada más. No necesitas Python, ni Git, ni FFmpeg, ni Node. Todo eso va dentro
del contenedor, en versiones fijas, y el código que se va a correr viene dentro
de este mismo ZIP.


QUÉ HACER
---------

1. Extrae este ZIP donde quieras.
2. Doble clic en   CHECK_ONLY.cmd
   Revisa tu máquina y no corre nada. Tarda segundos.
3. Si sale bien, doble clic en   RUN_EM_AUDIO_VALIDATION.cmd
4. Cuando termine, mándame   SEND_THIS_BACK.zip


CÓMO LEER EL RESULTADO
----------------------

Dos de los códigos son éxito. Esto importa:

   0   todo pasó y las declaraciones se sostuvieron en tu máquina
   3   todo pasó, y una declaración de footprint NO se sostiene en tu FFmpeg
   1   falló otra cosa, y eso sí es un defecto que quiero ver
  10   falta Docker o no está corriendo; no se intentó nada científico

EL 3 NO ES UN FALLO TUYO. Es el resultado central del paper medido otra vez.

El paper sostiene que esos números dependen del build de FFmpeg y que hay que
recalibrarlos para cada uno. Una reproducción independiente en FFmpeg 8.0.1 ya
midió el codificador MP3 alcanzando 4,317 muestras contra 2,304 declaradas, y
eso está publicado como hallazgo, sin ensanchar la declaración para que pasara.

Si tu máquina da 3, confirma esa tesis. Si da 0, también es información.


QUÉ MANDARME
------------

Solo   SEND_THIS_BACK.zip

Trae tus resultados, el reporte de tu máquina y los dos logs. Se arma solo.

Mándalo salga como salga. Una corrida que falla y se reporta vale más que una
que se acomodó para pasar: la reproducción anterior salió con error y encontró
dos defectos reales que ahora están publicados.


SI ALGO SE ATORA
----------------

"Docker no está corriendo": abre Docker Desktop y espera al icono de la ballena.

Si Windows pide activar virtualización o el backend WSL2, el script te lo dice
antes de empezar, no a los treinta minutos.

Si PowerShell se queja de scripts, los .cmd ya lo resuelven solos; no tienes que
escribir ningún comando.

Cualquier otra cosa: mándame la ventana tal cual, sin arreglarla. Un error
reportado me sirve más que uno rodeado.


UNA ADVERTENCIA HONESTA
-----------------------

Estos scripts de Windows nunca se han ejecutado en una máquina Windows real con
Docker Desktop. La lógica que corre dentro del contenedor sí está probada, y el
paquete se verifica en integración continua, pero el envoltorio de Windows no.

Si truena, es culpa del envoltorio y no tuya. Avísame.
