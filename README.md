# File Transfer Application
Este proyecto es el Trabajo Práctico N°1 de la materia Redes de la Facultad de Ingeniería, Universidad de Buenos Aires. Su objetivo principal es la implementación de una aplicación cliente-servidor para la transferencia de archivos.

## Integrantes

| Nombre                        | Legajo  |
|-------------------------------|---------|
| SANCHEZ, Garcia Julian        | 104590  |
| BUBULI, Pedro                 | 103452  |
| PERALTA, Federico             | 101947  |
| ZIMBIMBAKIS, Manuel Francisco | 103295  |
| PICO, Carolina                | 105098  |


## Tabla de Contenidos

- [Descripción](#descripción)
- [Requisitos](#requisitos)
- [Ejecucion Cliente](#ejecucion-cliente)
- [Ejecucion Servidor](#ejecucion-servidor)


## Descripción

El propósito de esta aplicación es implementar un protocolo de **Reliable Data Transfer(RDT)** utilizando **UDP** como protocolo de transporte. Se desarrollaron dos versiones del protocolo:

1. **Stop & Wait**
2. **Selective Repeat**


Además, la aplicación permite:

- **Transferencia de archivos binarios** de hasta 5 MB.
- **Operaciones soportadas**:
  - `UPLOAD`: Envío de archivos del cliente al servidor.
  - `DOWNLOAD`: Descarga de archivos del servidor al cliente.
- La entrega de paquetes con una pérdida de hasta **10%** en los enlaces.
- Manejo concurrente de múltiples clientes.

## Ejecucion Cliente
### Upload
```bash
python upload [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - s FILEPATH ] [ - n FILENAME ] [ - r protocol ]
```

Opciones:

| Opción         | Descripción                                  |
|----------------|----------------------------------------------|
| `-h`, `--help` | show this help message and exit              |
| `-v`, `--verbose` | increase output verbosity                 |
| `-q`, `--quiet` | decrease output verbosity                   |
| `-H`, `--host` | server IP address                            |
| `-P`, `--port` | server port                                  |
| `-s`, `--src` | source file path                              |
| `-n`, `--name` | file name                                    |
| `-a`, `--algorithm` | error recovery protocol                 |

#### Ejemplo de uso
```bash
python3 upload -v -s /ruta/al/storage_client. -n montana.jpg -r sr
```

### Download
```bash
python download [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - d FILEPATH ] [ - n FILENAME ] [ - r protocol ]
```

| Opción              | Descripción                                   |
|---------------------|-----------------------------------------------|
| `-h`, `--help`      | show this help message and exit               |
| `-v`, `--verbose`   | increase output verbosity                     |
| `-q`, `--quiet`     | decrease output verbosity                     |
| `-H`, `--host`      | server IP address                             |
| `-p`, `--port`      | server port                                   |
| `-d`, `--dst`       | destination file path                         |
| `-n`, `--name`      | file name                                     |
| `-a`, `--algorithm` | error recovery protocol                       |


#### Ejemplo de uso
```bash
python3 download -v -d /ruta/al/storage_client -n montana.jpg -r sr
```


En caso de no especificarse puerto o IP, se tomara por default: localhost:8080

## Ejecucion Servidor

```bash
python start - server [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - s DIRPATH ] [ - r protocol ]
```
Opciones:

| Opción              | Descripción                                   |
|---------------------|-----------------------------------------------|
| `-h`, `--help`      | show this help message and exit               |
| `-v`, `--verbose`   | increase output verbosity                     |
| `-q`, `--quiet`     | decrease output verbosity                     |
| `-H`, `--host`      | service IP address                            |
| `-p`, `--port`      | service port                                  |
| `-s`, `--storage`   | storage dir path                              |
| `-a`, `--algorithm` | error recovery protocol                       |

#### Ejemplo de uso
```bash
python3 start-server -v -s /ruta/al/storage_server -r sw
```

En caso de no especificarse puerto o IP, se tomara por default: localhost:8080
