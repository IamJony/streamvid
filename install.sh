#!/bin/bash

# Variables
SOURCE_DIR="./streamvid/"
DEST_DIR="/opt/streamvid/"
LINK_PATH="/usr/local/bin/streamvid"


if [ "$EUID" -ne 0 ]; then
 echo 'Run the script as root user or with sudo.'
  exit 0
fi

# Función para la instalación
install() {
    # Comprobar si el directorio de origen existe
    if [ ! -d "$SOURCE_DIR" ]; then
        echo "El directorio de origen $SOURCE_DIR no existe."
        exit 1
    fi

    # Copiar el contenido del directorio de origen al directorio de destino
    echo "Copiando $SOURCE_DIR a $DEST_DIR..."
    sudo cp -dfr "$SOURCE_DIR" "$DEST_DIR"
    sudo chmod 777 "$DEST_DIR"*

    # Verificar si la copia fue exitosa
    if [ $? -ne 0 ]; then
        echo "Error al copiar los archivos."
        exit 1
    fi

    # Dar permisos de ejecución a todos los archivos en el directorio de destino
    echo "Otorgando permisos de ejecución a los archivos en $DEST_DIR..."
    sudo find "$DEST_DIR" -type f -exec chmod +x {} \;

    # Verificar si la asignación de permisos fue exitosa
    if [ $? -ne 0 ]; then
        echo "Error al otorgar permisos de ejecución."
        exit 1
    fi

    # Crear un enlace simbólico
    sudo ln -sf "$DEST_DIR/streamvid" "$LINK_PATH"
    echo "Instalación completada exitosamente."
}

# Función para la desinstalación
uninstall() {
    # Eliminar el enlace simbólico
    if [ -L "$LINK_PATH" ]; then
        echo "Eliminando enlace simbólico $LINK_PATH..."
        sudo rm "$LINK_PATH"
    fi

    # Eliminar el directorio de destino
    if [ -d "$DEST_DIR" ]; then
        echo "Eliminando directorio $DEST_DIR..."
        sudo rm -rf "$DEST_DIR"
    fi

    echo "Desinstalación completada exitosamente."
}

# Función para reinstalar
reinstall() {
    uninstall
    install
}

# Comprobar el argumento proporcionado
case "$1" in
    --install)
        install
        ;;
    --uninstall)
        uninstall
        ;;
    --reinstall)
        reinstall
        ;;
    *)
        echo "Uso: $0 {--install|--uninstall|--reinstall}"
        exit 1
        ;;
esac
