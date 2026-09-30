# Datos publicados en el artículo ------------------------------------------
# Squillante G, Rojas M, Medina E, et al. Gac Méd Caracas. 2005;113(1):50-57
# Texto completo: https://ve.scielo.org/scielo.php?script=sci_arttext&pid=S0367-47622005000100005

# Cuadro 2: plomo en sangre (Pb-S) según resultado del test de Beery.
# Filas = exposición (expuestos primero), columnas = desenlace (casos primero).
# Este orden es el que espera epiR::epi.2by2().
tabla <- matrix(
  c(29, 8,    # Pb-S >= 10 µg/dL: 29 con Beery inferior de 37
    19, 4),   # Pb-S <  10 µg/dL: 19 con Beery inferior de 23
  nrow = 2, byrow = TRUE,
  dimnames = list(
    Plomo = c("Pb-S >= 10", "Pb-S < 10"),
    Beery = c("Inferior", "No inferior")
  )
)
tabla
addmargins(tabla)

# Cuadro 2 (medias de Pb-S en µg/dL): lo que compararon los autores con t de Student
pb_segun_beery <- data.frame(
  grupo = c("Inferior", "Normal"),
  n     = c(48, 12),
  media = c(10.54, 10.3),
  de    = c(3, 2.9)
)
pb_segun_exposicion <- data.frame(
  grupo = c("Pb-S >= 10", "Pb-S < 10"),
  n     = c(37, 23),
  media = c(12.3, 7.5),
  de    = c(2.2, 1.3)
)

# Cuadros 1 y 4: Pb-S y Beery según sexo
por_sexo <- data.frame(
  sexo           = c("Masculino", "Femenino"),
  n              = c(35, 25),
  pb_media       = c(11.1, 9.5),
  pb_de          = c(3.1, 2.7),
  beery_inferior = c(27, 21)
)

# Cuadros 1 y 3: Pb-S y Beery según edad
por_edad <- data.frame(
  edad           = c("4-5,9", "6-7,9", "8-9"),
  n              = c(7, 21, 32),
  pb_media       = c(11.1, 11.2, 9.8),
  pb_de          = c(2.4, 3.5, 2.6),  # el Cuadro 1 dice "22,6" para 8-9: errata, se asume 2,6
  beery_inferior = c(2, 15, 31)
)
por_edad
