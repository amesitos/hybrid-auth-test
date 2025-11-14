import mysql.connector
from pymongo import MongoClient
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime
import getpass

load_dotenv()

class SistemaAutenticacion:
    
    def __init__(self):
        self.mysql_conn = None
        self.cursor = None
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_users = None
        self.mongo_logs = None
        self.usuario_actual = None  

        # CONEXIÓN MYSQL
        try:
            self.mysql_conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                port=int(os.getenv("DB_PORT", 3306))
            )
            self.cursor = self.mysql_conn.cursor(dictionary=True)
            print("\nConexión a MySQL exitosa.")
        except Exception as e:
            print(f"Error de conexión a MySQL: {e}")  # [cite: 29]

        # CONEXIÓN MONGODB
        try:
            self.mongo_client = MongoClient(os.getenv("MONGO_URI"))
            self.mongo_db = self.mongo_client["auth_system"]
            self.mongo_users = self.mongo_db["usuarios"]
            self.mongo_logs = self.mongo_db["logs"]
            print("Conexión a MongoDB exitosa.")
        except Exception as e:
            print(f"Error de conexión a MongoDB: {e}") 


    # HASHING CON BCRYPT
    def hash_password(self, password):   
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    # VERIFICAR CONTRASEÑA HASHEADA
    def verificar_password(self, password, password_hash):
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), password_hash)

    # REGISTRAR LOG EN MONGODB
    def registrar_log(self, accion):   
            if self.usuario_actual:
                user_id = self.usuario_actual['id'] 
                username = self.usuario_actual['username']
            else:
                user_id = None 
                username = "Desconocido"

            log_entry = {
                "usuario_id": user_id,       
                "username": username,       
                "accion": accion,            
                "fecha": datetime.now(),     
                "ip": "127.0.0.1"            
            }       
            try:
                self.mongo_logs.insert_one(log_entry)
                print(f"\nLog registrado en MongoDB: {accion}")
            except Exception as e:
                print(f"Error al registrar log en MongoDB: {e}")


    # MÉTODOS DE USUARIO
    
    # REGISTRO
    def registrar_usuario(self):
        print("\n" + "="*30)
        print("REGISTRO DE USUARIO")
        print("="*30)
        
        username = input("Usuario: ")
        email = input("Email: ")
        password = getpass.getpass("Contraseña: ") # <--- POR ESTA
        role = input("Rol (admin/usuario): ").lower() 
        hashed = self.hash_password(password)

        try:
            # INSERT EN MYSQL
            query = "INSERT INTO usuarios (username, email, password_hash, rol) VALUES (%s, %s, %s, %s)"
            self.cursor.execute(query, (username, email, hashed, role))
            self.mysql_conn.commit()
            mysql_id = self.cursor.lastrowid

            # REGISTRO EN MONGODB
            user_doc = {
                "mysql_id": mysql_id,
                "username": username,
                "email": email,
                "rol": role,
                "fecha_registro": datetime.now()
            }
            self.mongo_users.insert_one(user_doc)
            print(f"Usuario {username} registrado exitosamente en MySQL y MongoDB.")
            print(f"Contraseña hasheada: {hashed}")
            
            self.registrar_log("nuevo_registro")
        
        except mysql.connector.Error as err:
            print(f"Error MySQL: {err}")
            
    # INICIO SESIÓN
    def login(self):
        print("\n" + "="*20)
        print("INICIAR SESIÓN")
        print("="*20)

        username = input("Usuario: ")
        password = getpass.getpass("Contraseña: ")

        # Buscar usuario en MySQL
        query = "SELECT * FROM usuarios WHERE username = %s AND activo = 1"
        self.cursor.execute(query, (username,))
        user = self.cursor.fetchone()

        if user and self.verificar_password(password, user['password_hash']):
            self.usuario_actual = user
            print(f"\nBienvenido, {user['username']} ({user['rol']})")
            self.registrar_log("login_exitoso") # [cite: 70]
            self.menu_sesion()
        else:
            print("Credenciales inválidas.")
      
    # MENÚ DE INICIO DE SESIÓN
    def menu_sesion(self):
        while self.usuario_actual:
            print("\n" + "="*30)
            print(f"MENÚ DE USUARIO: {self.usuario_actual['username']} ---")
            print("="*30)
            print("1. Ver mis datos") 
            print("2. Editar perfil") 
            print("3. Eliminar cuenta")
            print("4. Cerrar sesión") 
            
            if self.usuario_actual['rol'] == 'admin':
                print("5. Ver logs del sistema (Solo Admin)")

            opcion = input("Seleccione: ")

            if opcion == '1':
                print("\n===== MIS DATOS =====")
                for k, v in self.usuario_actual.items():
                    print(f"{k}: {v}")
            elif opcion == '2':
                self.editar_perfil()
            elif opcion == '3':
                self.eliminar_cuenta()
            elif opcion == '4':
                self.registrar_log("logout")
                self.usuario_actual = None
                print("Sesión cerrada.")
            elif opcion == '5' and self.usuario_actual['rol'] == 'admin':
                print("\n===== Últimos 5 Logs =====\n")  
                logs = self.mongo_logs.find().sort("fecha", -1).limit(5)
                
                for i, log in enumerate(logs, start=1):
                    print(f"--- Log #{i} ---")
                    print(f"Usuario: {log.get('username', 'N/A')}")
                    print(f"Acción:  {log.get('accion', 'N/A')}")
                    print(f"Fecha:   {log.get('fecha', 'N/A')}")
                    print(f"Detalle: {log.get('detalle', 'N/A')}")
                    print("-------------------------\n")
            else:
                print("Opción no válida")

    # EDITAR PERFIL (username, email y contraseña)
    def editar_perfil(self):
        if not self.usuario_actual:
            print("No hay un usuario con sesión iniciada.")
            return

        while True:
            print("\n" + "="*20)
            print("EDITAR PERFIL")
            print("="*20)
            print("\nSeleccione qué desea editar:")
            print("1. Usuario")
            print("2. Email")
            print("3. Contraseña")
            print("4. Volver")
            opcion = input("Opción: ").strip()

            if opcion == '1':
                new_username = input("Nuevo Usuario: ").strip()
                if not new_username:
                    print("Usuario vacío, no se realiza cambio.")
                    continue
                try:
                    uid = self.usuario_actual['id']
                    self.cursor.execute(
                        "SELECT id FROM usuarios WHERE username = %s AND id != %s AND activo = 1",
                        (new_username, uid)
                    )
                    exists = self.cursor.fetchone()
                    if exists:
                        print("El usuario ya está en uso por otro usuario. Elija otro.")
                        continue

                    # Actualizar MySQL
                    self.cursor.execute("UPDATE usuarios SET username = %s WHERE id = %s", (new_username, uid))
                    self.mysql_conn.commit()

                    # Actualizar MongoDB
                    self.mongo_users.update_one({"mysql_id": uid}, {"$set": {"username": new_username}})

                    # Actualizar sesión
                    self.usuario_actual['username'] = new_username
                    print("Usuario actualizado.")
                    self.registrar_log("edicion_usuario")
                except Exception as e:
                    print(f"Error al actualizar usuario: {e}")

            elif opcion == '2':
                new_email = input("Nuevo email: ").strip()
                if not new_email:
                    print("Email vacío, no se realiza cambio.")
                    continue
                try:
                    uid = self.usuario_actual['id']
                    self.cursor.execute("UPDATE usuarios SET email = %s WHERE id = %s", (new_email, uid))
                    self.mysql_conn.commit()
                    self.mongo_users.update_one({"mysql_id": uid}, {"$set": {"email": new_email}})
                    self.usuario_actual['email'] = new_email
                    print("Email actualizado.")
                    self.registrar_log("edicion_email")
                except Exception as e:
                    print(f"Error al actualizar email: {e}")

            elif opcion == '3':
                new_password = getpass.getpass("Nueva Contraseña: ")
                if not new_password:
                    print("Contraseña vacía, no se realiza cambio.")
                    continue
                try:
                    uid = self.usuario_actual['id']
                    hashed = self.hash_password(new_password)
                    self.cursor.execute("UPDATE usuarios SET password_hash = %s WHERE id = %s", (hashed, uid))
                    self.mysql_conn.commit()
                    
                    # No almacenamos password en Mongo, solo el espejo si fuera necesario
                    try:
                        self.usuario_actual['password_hash'] = hashed
                    except Exception:
                        pass
                    print("Contraseña actualizada.")
                    self.registrar_log("edicion_contraseña")
                except Exception as e:
                    print(f"Error al actualizar password: {e}")

            elif opcion == '4':
                print("Volviendo al menú de sesión.")
                break
            else:
                print("Opción no válida. Elija 1, 2, 3 o 4.")

    # ELIMINAR CUENTA
    def eliminar_cuenta(self):
        print("\n" + "="*30)
        print("ELIMINAR CUENTA")
        print("Esta acción es irreversible.")
        print("="*30)
        confirm = input("¿Está seguro? (s/n): ").lower()
        
        if confirm == 's':
            try:
                uid = self.usuario_actual['id']
                
                # Desactivar en MySQL
                self.cursor.execute("UPDATE usuarios SET activo = 0 WHERE id = %s", (uid,))
                self.mysql_conn.commit()
                
                # Eliminar de MongoDB
                self.mongo_users.delete_one({"mysql_id": uid})
                
                print("Cuenta eliminada.")
                self.registrar_log("eliminacion_cuenta")
                self.usuario_actual = None
            except Exception as e:
                print(f"Error al eliminar cuenta: {e}")
    
    # CERRAR SESIÓN    
    def logout(self):
        if self.usuario_actual:
            self.registrar_log("logout")
            self.usuario_actual = None
            print("Sesión cerrada.")
        else:
            print("No hay un usuario con sesión iniciada.")
            
    # RECUPERAR CONTRASEÑA (simulada)
    def recuperar_contrasena(self):
        print("\n" + "="*30)
        print("RECUPERAR CONTRASEÑA (simulada)")
        identifier = input("Ingrese su username o email: ").strip()
        if not identifier:
            print("Entrada vacía. Cancelando recuperación.")
            return

        try:
            # Buscar usuario por username o email
            query = "SELECT * FROM usuarios WHERE (username = %s OR email = %s) AND activo = 1"
            self.cursor.execute(query, (identifier, identifier))
            user = self.cursor.fetchone()

            if not user:
                print("No se encontró un usuario activo con esa información.")
                return

            # Generar contraseña temporal (simulada)
            import uuid
            temp_password = uuid.uuid4().hex[:10]
            hashed = self.hash_password(temp_password)

            # Actualizar contraseña en MySQL
            self.cursor.execute("UPDATE usuarios SET password_hash = %s WHERE id = %s", (hashed, user['id']))
            self.mysql_conn.commit()

            # (Opcional) actualizar espejo en MongoDB si guarda alguna referencia
            try:
                self.mongo_users.update_one({"mysql_id": user['id']}, {"$set": {"password_reset_at": datetime.now()}})
            except Exception:
                pass

            # Simular envío por email mostrando la contraseña temporal (en un sistema real se enviaría por correo)
            print("Se generó una contraseña temporal. (Simulación)")
            print(f"Contraseña temporal para {user.get('username', 'usuario')}: {temp_password}")
            self.registrar_log("recuperacion_contrasena_generada")

        except Exception as e:
            print(f"Error en recuperación de contraseña: {e}")


    # MENÚ PRINCIPAL
    def main(self):
        while True:
            print("\n" + "="*20)
            print("MENÚ PRINCIPAL")
            print("="*20)
            print("1. Registrarse")
            print("2. Login")
            print("3. Recuperar contraseña")
            print("4. Salir")
            
            opcion = input("Seleccione: ")
            
            if opcion == '1':
                self.registrar_usuario()
            elif opcion == '2':
                self.login()
            elif opcion == '3':
                self.recuperar_contrasena()
            elif opcion == '4':
                print("Saliendo...")
                break
            else:
                print("Opción no válida")


if __name__ == "__main__":
    sistema = SistemaAutenticacion()
    sistema.main()