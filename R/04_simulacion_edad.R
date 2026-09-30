# Parte 3. Simulación: ¿pudo la edad esconder un efecto del plomo? ----------
#
# IMPORTANTE: son DATOS SIMULADOS. El artículo publica plomo x edad (Cuadro 1)
# y Beery x edad (Cuadro 3), pero no la tabla cruzada plomo x edad x Beery,
# así que no se puede reanalizar con los datos individuales. La simulación
# usa los cuadros publicados para ilustrar cómo la edad PODRÍA sesgar la RP.

library(ggplot2)
library(sandwich)
library(lmtest)

# 1. DAG: la edad es causa común de la exposición y del desenlace ----------
nodos <- data.frame(
  nombre = c("Edad", "Plomo", "Beery inferior"),
  x = c(0.5, 0, 1), y = c(1, 0, 0)
)
flechas <- data.frame(
  x    = c(0.47, 0.53, 0.12),  y    = c(0.90, 0.90, 0),
  xend = c(0.06, 0.94, 0.80),  yend = c(0.10, 0.10, 0),
  tipo = c("confusión", "confusión", "¿efecto?")
)
grafico_dag <- ggplot() +
  geom_segment(data = flechas,
               aes(x, y, xend = xend, yend = yend, linetype = tipo),
               arrow = arrow(length = unit(0.25, "cm"), type = "closed"),
               colour = "grey30") +
  geom_label(data = nodos, aes(x, y, label = nombre), size = 5,
             label.padding = unit(0.4, "lines"), fill = "#e8eef5") +
  scale_linetype_manual(values = c("confusión" = "solid", "¿efecto?" = "dashed"),
                        name = NULL) +
  coord_cartesian(xlim = c(-0.2, 1.25), ylim = c(-0.2, 1.15)) +
  theme_void(base_size = 12) +
  theme(legend.position = "bottom")
grafico_dag

# 2. Parámetros tomados del artículo ----------------------------------------
# `por_edad` viene de 01_datos.R (Cuadros 1 y 3).
#
# SUPUESTO 1: dentro de cada grupo de edad, el Pb-S sigue una distribución
# normal con la media y la DE del Cuadro 1. De ahí sale la proporción de
# niños con Pb-S >= 10 en cada edad.
# SUPUESTO 2: el efecto del plomo (or_verdadero) es igual en todas las edades.
or_verdadero <- 2.5  # escenario: efecto REAL del plomo dentro de cada edad

# Proporción de Beery inferior en no expuestos de cada edad, elegida para que
# la prevalencia total por edad coincida con el Cuadro 3
beery_basal <- function(p_exp, prevalencia, or) {
  plogis(uniroot(function(q) (1 - p_exp) * plogis(q) +
                   p_exp * plogis(q + log(or)) - prevalencia,
                 c(-10, 10))$root)
}

armar_parametros <- function(or) {
  data.frame(
    edad          = por_edad$edad,
    n             = por_edad$n,
    p_expuesto    = 1 - pnorm(10, por_edad$pb_media, por_edad$pb_de),
    p_beery_noexp = mapply(beery_basal,
                           1 - pnorm(10, por_edad$pb_media, por_edad$pb_de),
                           por_edad$beery_inferior / por_edad$n,
                           MoreArgs = list(or = or))
  )
}
parametros <- armar_parametros(or_verdadero)
parametros

# Con estos supuestos se esperan ~33 expuestos (en el estudio hubo 37)
sum(parametros$n * parametros$p_expuesto)

simular_estudio <- function(par = parametros, or = or_verdadero) {
  edad <- rep(par$edad, par$n)
  i    <- match(edad, par$edad)
  plomo <- rbinom(length(edad), 1, par$p_expuesto[i])
  logit_p <- qlogis(par$p_beery_noexp[i]) + log(or) * plomo
  beery <- rbinom(length(edad), 1, plogis(logit_p))
  data.frame(edad = factor(edad, levels = par$edad), plomo, beery)
}

# RP cruda y RP de Mantel-Haenszel ajustada por edad
rp_cruda <- function(d) {
  mean(d$beery[d$plomo == 1]) / mean(d$beery[d$plomo == 0])
}
rp_mh <- function(d) {
  num <- 0; den <- 0
  for (g in split(d, d$edad)) {
    n_g <- nrow(g)
    a  <- as.numeric(sum(g$beery[g$plomo == 1])); n1 <- sum(g$plomo == 1)
    c_ <- as.numeric(sum(g$beery[g$plomo == 0])); n0 <- sum(g$plomo == 0)
    num <- num + a * n0 / n_g
    den <- den + c_ * n1 / n_g
  }
  num / den
}

# 3. Un estudio simulado de 60 niños, analizado paso a paso -----------------
set.seed(2005)
ejemplo <- simular_estudio()

# ¿Se parece a lo publicado?
table(Plomo = ejemplo$plomo)
mean(ejemplo$beery)
tapply(ejemplo$beery, ejemplo$edad, mean)

# Tabla estratificada por edad y prevalencia de Beery inferior en cada celda
tabla_estratos <- table(
  Plomo = factor(ejemplo$plomo, levels = c(1, 0), labels = c(">=10", "<10")),
  Beery = factor(ejemplo$beery, levels = c(1, 0), labels = c("Inferior", "No inferior")),
  Edad  = ejemplo$edad
)
tabla_estratos
round(tapply(ejemplo$beery, list(Plomo = ejemplo$plomo, Edad = ejemplo$edad), mean), 2)

# RP cruda vs. RP de Mantel-Haenszel ajustada por edad
# (se calcula a mano porque con 60 niños algunos estratos tienen celdas en 0
# y epi.2by2() puede fallar al estratificar)
c(cruda = rp_cruda(ejemplo), ajustada_MH = rp_mh(ejemplo))

# Regresión de Poisson con varianza robusta: estima la RP ajustada por edad
modelo <- glm(beery ~ plomo + edad, family = poisson, data = ejemplo)
coef_robustos <- coeftest(modelo, vcov. = vcovHC(modelo, type = "HC0"))
ic_robustos   <- coefci(modelo, vcov. = vcovHC(modelo, type = "HC0"))
rp_poisson <- exp(c(est = coef_robustos["plomo", "Estimate"], ic_robustos["plomo", ]))
rp_poisson

# 4. Repetir el estudio 2000 veces -------------------------------------------
# Un solo estudio de 60 niños es muy ruidoso; repetirlo muestra el patrón.
n_rep <- 2000
repeticiones <- t(replicate(n_rep, {
  d <- simular_estudio()
  c(cruda = rp_cruda(d), ajustada = rp_mh(d))
}))
repeticiones <- repeticiones[is.finite(rowSums(repeticiones)), ]

# Valor esperado de la RP cruda y ajustada (sin azar) para distintos efectos
# verdaderos del plomo. Con OR = 1 el plomo no hace nada: todo lo que se
# aleje de 1 en la RP cruda es sesgo por edad.
rp_esperadas <- function(or) {
  par <- armar_parametros(or)
  p1  <- plogis(qlogis(par$p_beery_noexp) + log(or))
  a   <- par$n * par$p_expuesto * p1                  # expuestos con Beery inferior
  c_  <- par$n * (1 - par$p_expuesto) * par$p_beery_noexp
  n1  <- par$n * par$p_expuesto; n0 <- par$n * (1 - par$p_expuesto)
  c(or_verdadero = or,
    cruda    = (sum(a) / sum(n1)) / (sum(c_) / sum(n0)),
    ajustada = sum(a * n0 / par$n) / sum(c_ * n1 / par$n))
}
sesgo_edad <- as.data.frame(t(sapply(c(1, 1.5, 2.5, 4), rp_esperadas)))
sesgo_edad

esperado <- rp_esperadas(or_verdadero)

resumen_rep <- data.frame(
  analisis = c("Cruda", "Ajustada por edad (M-H)"),
  mediana  = apply(repeticiones, 2, median),
  pct_menor_1 = colMeans(repeticiones < 1)
)
resumen_rep

datos_rep <- data.frame(
  rp = c(repeticiones[, "cruda"], repeticiones[, "ajustada"]),
  analisis = factor(rep(c("Cruda", "Ajustada por edad (M-H)"), each = nrow(repeticiones)),
                    levels = c("Cruda", "Ajustada por edad (M-H)"))
)
grafico_simulacion <- ggplot(datos_rep, aes(rp, fill = analisis)) +
  geom_density(alpha = 0.5, colour = NA) +
  geom_vline(xintercept = 1, linetype = "dashed") +
  geom_vline(xintercept = sesgo_edad$cruda[1], colour = "grey35", linetype = "dotted") +
  geom_vline(xintercept = 0.95, colour = "firebrick") +
  annotate("text", x = 0.95, y = Inf, label = "RP del artículo = 0,95",
           colour = "firebrick", hjust = 1.05, vjust = 1.5, size = 3.5) +
  scale_x_log10(breaks = c(0.6, 0.7, 0.8, 0.9, 1, 1.25, 1.5, 2),
                labels = function(x) format(x, decimal.mark = ",")) +
  scale_fill_manual(values = c("#b0b0b0", "#6a8caf"), name = NULL) +
  labs(x = "Razón de prevalencias estimada (escala log)", y = "Densidad",
       title = sprintf("%d estudios simulados: el plomo SÍ tiene efecto (OR = %s)",
                       n_rep, format(or_verdadero, decimal.mark = ",")),
       subtitle = "Datos simulados. Punteada: RP cruda esperada si el plomo no tuviera efecto") +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom")
grafico_simulacion
