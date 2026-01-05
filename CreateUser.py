
import os
import django

from django.contrib.auth.hashers import make_password

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')
django.setup()

from app2.models import User_admin

def registrar_usuario():
    print("\n=== Registro de nuevo usuario ===")
    nombre = input("Nombre de usuario: ").strip()
    password = input("Contraseña: ").strip()
    email = input("Email (opcional): ").strip()
    telefono = input("Teléfono (opcional): ").strip()
    if not nombre or not password:
        print("[ERROR] Nombre y contraseña son obligatorios.")
        return
    if User_admin.objects.filter(nombre=nombre).exists():
        print(f"[ERROR] El nombre de usuario '{nombre}' ya existe.")
        return
    if email and User_admin.objects.filter(email=email).exists():
        print(f"[ERROR] El email '{email}' ya está registrado.")
        return
    hashed_password = make_password(password)
    user = User_admin(
        nombre=nombre,
        password=hashed_password,
        email=email if email else None,
        telefono=telefono if telefono else None
    )
    user.save()
    print(f"[OK] Usuario '{nombre}' registrado correctamente.\n")

def cambiar_password():
    print("\n=== Cambiar contraseña de usuario ===")
    usuarios = list(User_admin.objects.all())
    if not usuarios:
        print("[ERROR] No hay usuarios registrados.")
        return
    print("Usuarios disponibles:")
    for idx, u in enumerate(usuarios, 1):
        print(f"  {idx}. {u.nombre}")
    while True:
        try:
            sel = int(input("Seleccione el número de usuario: "))
            if 1 <= sel <= len(usuarios):
                break
            else:
                print("[ERROR] Selección fuera de rango.")
        except ValueError:
            print("[ERROR] Ingrese un número válido.")
    user = usuarios[sel-1]
    new_password = input(f"Nueva contraseña para '{user.nombre}': ").strip()
    if not new_password:
        print("[ERROR] La contraseña no puede estar vacía.")
        return
    user.password = make_password(new_password)
    user.save()
    print(f"[OK] Contraseña actualizada para '{user.nombre}'.\n")

def main():
    while True:
        print("\n=== Menú de administración de usuarios ===")
        print("1. Registrar nuevo usuario")
        print("2. Cambiar contraseña de usuario")
        print("3. Salir")
        op = input("Seleccione una opción: ").strip()
        if op == '1':
            registrar_usuario()
        elif op == '2':
            cambiar_password()
        elif op == '3':
            print("Saliendo...")
            break
        else:
            print("[ERROR] Opción no válida.")

if __name__ == "__main__":
    main()