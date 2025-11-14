# 🚀 Sistema de Autenticación Híbrido

Se implementa un sistema de autenticación de usuarios en Python. El sistema utiliza una arquitectura de base de datos híbrida 100% en la nube, conectándose a **MySQL en Clever Cloud** y **MongoDB en Atlas**.

El sistema soporta el registro de usuarios, login seguro, gestión de perfiles (editar/eliminar), recuperación simulada de contraseña y diferenciación de roles (admin/usuario), con un enfoque en la seguridad y el manejo robusto de conexiones en la nube.

---

## 🛠️ 1. Instrucciones de Instalación y Configuración

Sigue estos pasos para ejecutar el proyecto en tu máquina local.

### Prerrequisitos
* Python 3.8 o superior.
* Una cuenta de **Clever Cloud** con un Add-on de MySQL activado.
* Una cuenta de **MongoDB Atlas** con un Cluster gratuito (M0) desplegado.

### Pasos de Instalación

1.  **Clonar el Repositorio (Opcional)**
    ```bash
    git clone https://github.com/amesitos/hybrid-auth-test
    cd bdd_examen
    ```

2.  **Crear un Entorno Virtual (Recomendado)**
    ```bash
    # En Windows
    python -m venv venv
    venv\Scripts\activate
    
    # En macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar Dependencias**
    Crea un archivo `requirements.txt` con el siguiente contenido:
    ```txt
    mysql-connector-python
    pymongo[srv]
    bcrypt
    python-dotenv
    ```
    Y luego instálalo:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno (.env)**
    Crea un archivo `.env` en la raíz del proyecto. **Este archivo es crucial.** Llénalo con tus credenciales de Clever Cloud y Atlas.
    ```env
    # --- CONFIGURACIÓN MYSQL (Clever Cloud) ---
    DB_HOST=tu-host-de-clever-cloud.mysql.services.clever-cloud.com
    DB_USER=tu_usuario_clever
    DB_PASSWORD=tu_password_clever
    DB_NAME=tu_nombre_base_datos_clever
    DB_PORT=3306 
    
    # --- CONFIGURACIÓN MONGODB (Atlas) ---
    MONGO_URI=mongodb+srv://tu_usuario_atlas:tu_password_atlas@cluster0.xyz.mongodb.net/
    ```

5.  **Configurar Acceso a Bases de Datos en la Nube**
    * **MySQL (Clever Cloud):** La base de datos está lista para recibir conexiones.
    * **MongoDB (Atlas):** Ve a `Security` > `Network Access` y **añade tu dirección IP actual** a la lista de acceso (o usa `0.0.0.0/0` para permitir el acceso desde cualquier lugar, ideal para pruebas).

6.  **Inicializar la Base de Datos MySQL**
    Conéctate a tu base de datos de Clever Cloud usando **MySQL Workbench** (usando las credenciales del `.env`) y ejecuta el script `setup_mysql.sql` para crear la tabla `usuarios`.

7.  **Ejecutar el Sistema**
    ```bash
    python sistema_auth_facil.py
    ```

---

## 🏛️ 2. Explicación de la Estructura de la Base de Datos

Este proyecto utiliza un **diseño de base de datos híbrido** para aprovechar las fortalezas de SQL y NoSQL, separando las responsabilidades.

### MySQL (en Clever Cloud)
Funciona como la **"Bóveda de Autenticación"**. Almacena los datos estructurados y críticos para la seguridad.

* **Tabla: `usuarios`**
    * `id`: (INT) Llave primaria única.
    * `username`: (VARCHAR) Único, usado para el login[cite: 8].
    * `email`: (VARCHAR) Único, usado para recuperación[cite: 9].
    * `password_hash`: (VARCHAR) Almacena el hash de `bcrypt`[cite: 11].
    * `rol`: (VARCHAR) Diferencia entre 'admin' y 'usuario'[cite: 65].
    * `activo`: (BOOLEAN) Permite el "borrado lógico" de cuentas[cite: 13].

### MongoDB (en Atlas)
Funciona como la **"Plataforma de Perfil y Auditoría"**. Almacena datos flexibles, no estructurados y de alto volumen.

* **Colección: `usuarios`**
    * Actúa como un "espejo" de la tabla MySQL para datos de perfil[cite: 14]. **No almacena el `password_hash`** por razones de seguridad.
    * `mysql_id`: (INT) Actúa como "llave foránea" vinculando este documento al `id` en MySQL.
    * `username`, `email`, `rol`: Campos flexibles que se pueden editar.
    * `fecha_registro`: (ISODate) Timestamp de creación.

* **Colección: `logs`** [cite: 64, 66-73]
    * Registra cada acción importante que ocurre en el sistema[cite: 64].
    * `usuario_id`: (INT) El `id` de MySQL del usuario que realizó la acción[cite: 69].
    * `accion`: (String) Ej: "login_exitoso", "logout", "edicion_perfil"[cite: 70].
    * `fecha`: (ISODate) Timestamp exacto del evento[cite: 71].
    * `ip`: (String) IP simulada del cliente[cite: 72].

---

## 🧠 3. Decisiones de Diseño Tomadas

1.  **Arquitectura Híbrida (SQL + NoSQL):** Se decidió usar MySQL para la autenticación debido a su rigidez (reglas `UNIQUE`, `NOT NULL`) y transacciones seguras. Se eligió MongoDB para los logs y perfiles por su flexibilidad y escalabilidad; es fácil añadir nuevos campos a un perfil o registrar nuevos tipos de logs sin alterar un esquema.

2.  **Seguridad de Contraseñas (`bcrypt` + `getpass`):**
    * `bcrypt` fue elegido sobre `MD5` o `SHA` porque es un algoritmo de hashing lento y adaptativo que incluye un "salt" automáticamente, haciéndolo resistente a ataques de fuerza bruta y tablas arcoíris.
    * `getpass` se implementó para ocultar la contraseña mientras se escribe en la terminal, previniendo que quede expuesta en la pantalla.

3.  **Separación de Datos Sensibles:** La decisión más importante fue **no almacenar el `password_hash` en MongoDB**. Si la base de datos de perfiles (Mongo) fuera comprometida, los atacantes no obtendrían los hashes de las contraseñas, que permanecen seguros en la base de datos de autenticación (MySQL).

4.  **Manejo de Conexiones en la Nube:** El código fue diseñado para ser robusto en un entorno de nube.
    * `python-dotenv` se usa para cargar credenciales, evitando escribirlas en el código (`hardcoding`).
    * Se implementó `mysql_conn.ping(reconnect=True)` para manejar los `timeouts` de inactividad de los planes gratuitos en la nube.
    * Se usa un bloque `try...finally` global para asegurar que las conexiones (`.close()`) se cierren siempre al finalizar el script, previniendo la saturación (`max_user_connections`).

---

## 😥 4. Dificultades Encontradas y Soluciones

1.  **Dificultad: `Error 2013: Lost connection to MySQL server during query` o `TimeoutError`**
    * **Causa:** El servidor de Clever Cloud (MySQL) cierra las conexiones inactivas después de ~60 segundos. El script abría la conexión al inicio y, si el usuario tardaba en seleccionar una opción, la conexión moría.
    * **Solución:** Se implementó `self.mysql_conn.ping(reconnect=True, attempts=3, delay=1)` justo antes de cada ejecución de consulta (`self.cursor.execute(...)`) en todas las funciones que interactúan con MySQL (`login`, `registrar_usuario`, `editar_perfil`, etc.).

2.  **Dificultad: `User '...' has exceeded the 'max_user_connections' resource (current value: 5)`**
    * **Causa:** Los scripts que fallaban por errores (`AttributeError`, `TimeoutError`) no cerraban sus conexiones, dejando conexiones "fantasma" abiertas en el servidor hasta alcanzar el límite del plan gratuito.
    * **Solución:** Se implementó un bloque `try...finally` en el `if __name__ == "__main__":` para asegurar que `mysql_conn.close()` y `mongo_client.close()` se ejecuten siempre al terminar el programa, sin importar si falló o no.

3.  **Dificultad: `AttributeError` al registrar logs (ej: `'logs'` vs `'mongo_logs'`)**
    * **Causa:** Confusión entre un sistema de log local (basado en `self.logs = []`) y el sistema de log de MongoDB (`self.mongo_logs`).
    * **Solución:** Se eliminó el sistema de log incorrecto y se refactorizó todo el código para usar una única función, `self.registrar_log()`, que escribe consistentemente en `self.mongo_logs`.

4.  **Dificultad: Los logs de admin mostraban `Usuario: N/A`**
    * **Causa:** Inconsistencia de claves. La función `registrar_log` guardaba el nombre de usuario bajo la clave `"username"`, pero la función `menu_sesion` intentaba leerlo usando la clave `"usuario"`.
    * **Solución:** Se modificó la línea de lectura en `menu_sesion` de `log.get('usuario', 'N/A')` a `log.get('username', 'N/A')` para que coincidiera con la base de datos.
