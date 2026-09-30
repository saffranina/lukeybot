# Genera el sitio de GitHub Pages en la raíz del repo -----------------------
# Correr desde la raíz del proyecto después de cambiar la presentación o el
# reporte. Luego hacer commit y push de index.html, presentacion.html y
# reporte.html.
#
#   index.html        = portada con los dos botones (se edita a mano)
#   presentacion.html = presentación interactiva (se genera desde
#                       fuente/presentacion.html, que no trae <head>)
#   reporte.html      = reporte Quarto con el código de R

# fuente/presentacion.html no trae <html>/<head> propios; aquí se le agregan
cuerpo <- readLines("fuente/presentacion.html", encoding = "UTF-8")
writeLines(
  c("<!doctype html>",
    "<html lang=\"es\">",
    "<head>",
    "<meta charset=\"utf-8\">",
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">",
    "<style>body { margin: 0; } [hidden] { display: none !important; }</style>",
    "</head>",
    "<body>",
    cuerpo,
    "</body>",
    "</html>"),
  "presentacion.html", useBytes = TRUE
)

# Reporte: se renderiza a reporte.html, autocontenido
system2("quarto", c("render", "reporte.qmd", "--to", "html"))

# Sin esto, GitHub Pages procesa el repo con Jekyll y muestra el README
file.create(".nojekyll")
