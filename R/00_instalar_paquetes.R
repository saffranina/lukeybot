# Correr una sola vez para instalar los paquetes que usa el proyecto.
paquetes <- c("epiR", "pwr", "ggplot2", "sandwich", "lmtest", "knitr", "rmarkdown")
faltan <- setdiff(paquetes, rownames(installed.packages()))
if (length(faltan) > 0) install.packages(faltan)
