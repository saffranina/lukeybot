# Genera el sitio de GitHub Pages en docs/ ---------------------------------
# Correr desde la raíz del proyecto después de cambiar la presentación o el
# reporte. Luego hacer commit y push de la carpeta docs/.
#
#   docs/index.html        = portada con los dos botones (se edita a mano)
#   docs/presentacion.html = presentación interactiva
#   docs/reporte.html = reporte Quarto con el código de R

dir.create("docs", showWarnings = FALSE)

# presentacion.html no trae <html>/<head> propios; aquí se le agregan
cuerpo <- readLines("presentacion.html", encoding = "UTF-8")
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
  "docs/presentacion.html", useBytes = TRUE
)

# Reporte: se renderiza a HTML autocontenido y se copia a docs/
system2("quarto", c("render", "reporte.qmd", "--to", "html"))
file.copy("reporte.html", "docs/reporte.html", overwrite = TRUE)

# Sin esto, GitHub Pages procesa la carpeta con Jekyll
file.create("docs/.nojekyll")
