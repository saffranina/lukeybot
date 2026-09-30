# Parte 2. Tamaño muestral y potencia ---------------------------------------

library(epiR)
library(pwr)
library(ggplot2)

z_alfa <- qnorm(1 - 0.05 / 2)  # 1,96
z_beta <- qnorm(0.80)          # 0,84

# Lo que hicieron los autores: fórmula para ESTIMAR una proporción
p <- 0.5; d <- 0.10; N <- 156
n0_autores <- z_alfa^2 * p * (1 - p) / d^2         # ~96
n_autores  <- ceiling(n0_autores / (1 + (n0_autores - 1) / N))  # corrección por población finita
c(n0 = n0_autores, n_corregido = n_autores)

# Comprobación con epiR (error relativo 20 % de p = 0,5 equivale a d = 10 %)
epi.sssimpleestb(N = N, Py = p, epsilon = d / p, error = "relative",
                 se = 1, sp = 1, nfractional = FALSE, conf.level = 0.95)

# Lo que correspondía: fórmula para COMPARAR dos proporciones
# p1 = Beery inferior esperado en expuestos, p0 = en no expuestos.
# Diferencia mínima que interesa detectar: 80 % vs. 60 % (RP = 1,33).
p1 <- 0.80; p0 <- 0.60
p_barra <- (p1 + p0) / 2
n_grupo <- (z_alfa * sqrt(2 * p_barra * (1 - p_barra)) +
            z_beta * sqrt(p1 * (1 - p1) + p0 * (1 - p0)))^2 / (p1 - p0)^2
n_grupo <- ceiling(n_grupo)  # ~82 por grupo
c(por_grupo = n_grupo, total = 2 * n_grupo)

# Comprobación con R base (n = número por grupo)
power.prop.test(p1 = p1, p2 = p0, sig.level = 0.05, power = 0.80)

# Grupos desiguales: k = no expuestos por cada expuesto (en el estudio, 23/37).
# p_barra pasa a ser el promedio ponderado por el tamaño de cada grupo.
k <- 23 / 37
p_barra_k <- (p1 + k * p0) / (1 + k)
n_exp_k <- (z_alfa * sqrt((1 + 1 / k) * p_barra_k * (1 - p_barra_k)) +
            z_beta * sqrt(p1 * (1 - p1) + p0 * (1 - p0) / k))^2 / (p1 - p0)^2
n_exp_k   <- ceiling(n_exp_k)
n_noexp_k <- ceiling(k * n_exp_k)
c(expuestos = n_exp_k, no_expuestos = n_noexp_k, total = n_exp_k + n_noexp_k)

# Si se hubiera usado el puntaje continuo del Beery (edad equivalente) en vez
# de dicotomizarlo: fórmula de diferencia de medias. El artículo no reporta la
# DE del puntaje, así que se expresa en unidades de DE (d de Cohen = Δ / σ).
d_cohen <- 0.5   # diferencia "moderada" entre expuestos y no expuestos
n_grupo_continuo <- ceiling(2 * (z_alfa + z_beta)^2 / d_cohen^2)  # ~63 por grupo
c(por_grupo = n_grupo_continuo, total = 2 * n_grupo_continuo)
power.t.test(delta = d_cohen, sd = 1, sig.level = 0.05, power = 0.80)

# Potencia real del estudio con los grupos que tuvo (37 expuestos, 23 no)
n_exp <- 37; n_noexp <- 23
p_noexp <- 19 / 23   # prevalencia observada en no expuestos

potencia_escenario <- pwr.2p2n.test(h = ES.h(p1, p0), n1 = n_exp, n2 = n_noexp,
                                    sig.level = 0.05)$power
potencia_observada <- pwr.2p2n.test(h = ES.h(29 / 37, p_noexp), n1 = n_exp,
                                    n2 = n_noexp, sig.level = 0.05)$power
c(escenario_80_vs_60 = potencia_escenario, diferencia_observada = potencia_observada)

# Curva de potencia: probabilidad de detectar cada RP verdadera
curva <- data.frame(rp = seq(0.40, 1.20, by = 0.01))
curva$p_exp <- pmin(curva$rp * p_noexp, 0.999)
curva$potencia <- sapply(curva$p_exp, function(pe)
  pwr.2p2n.test(h = ES.h(pe, p_noexp), n1 = n_exp, n2 = n_noexp,
                sig.level = 0.05)$power)
curva <- curva[curva$rp * p_noexp < 1, ]

grafico_potencia <- ggplot(curva, aes(rp, potencia)) +
  geom_hline(yintercept = 0.80, linetype = "dashed", colour = "grey40") +
  geom_vline(xintercept = 1, colour = "grey70") +
  geom_line(linewidth = 1, colour = "#6a8caf") +
  annotate("text", x = 0.42, y = 0.83, label = "80 %", hjust = 0, colour = "grey40") +
  scale_y_continuous(labels = function(x) paste0(100 * x, " %"), limits = c(0, 1)) +
  scale_x_continuous(labels = function(x) format(x, decimal.mark = ",")) +
  labs(x = "Razón de prevalencias verdadera", y = "Potencia",
       title = "¿Qué podía detectar un estudio con 37 vs. 23 niños?",
       subtitle = sprintf("Prevalencia en no expuestos fija en %.0f %%, alfa = 0,05 bilateral",
                          100 * p_noexp)) +
  theme_minimal(base_size = 12)
grafico_potencia

# RP detectables con 80 % de potencia (por debajo y por encima de 1)
rp_detectable_menor <- max(curva$rp[curva$rp < 1 & curva$potencia >= 0.80])
potencia_max_mayor  <- max(curva$potencia[curva$rp > 1])
c(rp_detectable_menor = rp_detectable_menor, potencia_max_si_rp_mayor_1 = potencia_max_mayor)
