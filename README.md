# PDF Toolbox

PDF Toolbox es una aplicación de escritorio desarrollada en Python que proporciona herramientas útiles para manipular archivos PDF. La aplicación ofrece una interfaz gráfica intuitiva construida con Tkinter para realizar operaciones comunes con archivos PDF.

## Autor

**José Emmanuel Quintana Torres**

## Licencia

Este proyecto es de uso libre. Puedes usar, modificar y distribuir este código como desees, sin restricciones.

## Características

- **Fusionar PDFs**: Combina múltiples archivos PDF en uno solo.
- **Dividir PDF**: Extrae páginas específicas de un PDF en archivos separados.
- **Comprimir PDF**: 
  - Modo sin pérdida: Optimiza el PDF manteniendo la calidad original
  - Modo con pérdida: Reduce el tamaño mediante rasterización con DPI ajustable
- **Convertir PDF a Imágenes**: Extrae las páginas de un PDF como imágenes PNG
- **Convertir Imágenes a PDF**: Crea un PDF a partir de una colección de imágenes

## Requisitos

- Python 3.x
- Dependencias principales:
  - `pypdf`: Para operaciones básicas con PDFs
  - `PyMuPDF` (fitz): Para compresión y conversión de PDFs
  - `Pillow`: Para procesamiento de imágenes
  - `tkinter`: Para la interfaz gráfica (generalmente viene con Python)

## Estructura del Proyecto

```
PDF/
├── app.py                  # Punto de entrada de la aplicación
├── controller/
│   └── pdf_controller.py   # Controlador principal
├── model/
│   └── pdf_ops.py         # Operaciones con PDFs
├── ui/
│   ├── main_view.py       # Vista principal
│   └── widgets.py         # Widgets personalizados
└── utils/
    └── theme.py           # Configuración de temas
```

## Uso

1. Ejecuta la aplicación:
```bash
python app.py
```

2. Utiliza la interfaz gráfica para:
   - Seleccionar archivos PDF para fusionar
   - Elegir un PDF para dividir y especificar rangos de páginas
   - Comprimir PDFs eligiendo el método deseado
   - Convertir PDFs a imágenes o viceversa

## Características Técnicas

- Arquitectura MVC (Modelo-Vista-Controlador)
- Manejo de errores robusto
- Interfaz gráfica moderna y fácil de usar
- Operaciones asíncronas para mantener la interfaz responsiva
- Soporte para arrastrar y soltar archivos
- Previsualización de archivos

## Notas de Implementación

- Utiliza `pypdf` para operaciones básicas de PDF
- Implementa `PyMuPDF` para operaciones avanzadas como compresión
- Usa `Pillow` para el manejo de imágenes
- Manejo de errores centralizado con mensajes de usuario amigables
- Configuración de DPI personalizable para conversiones

## Contribución

Si deseas contribuir a este proyecto, eres bienvenido a:
- Reportar problemas o bugs
- Sugerir nuevas características
- Enviar pull requests con mejoras

## Contacto

- **Autor**: José Emmanuel Quintana Torres
- Si tienes preguntas o sugerencias, no dudes en abrir un issue en el repositorio.