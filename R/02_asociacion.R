# Parte 1. El análisis que correspondía -------------------------------------
# Comparar el desenlace (Beery inferior) según la exposición (plomo),
# con una medida de asociación y su intervalo de confianza.

library(epiR)
library(ggplot2)

# Lo que hicieron los autores: t de Student con las medias del Cuadro 2 ------
# Se puede reproducir con los resúmenes publicados (media, DE, n).
t_resumen <- function(d) {
  sp <- sqrt(((d$n[1] - 1) * d$de[1]^2 + (d$n[2] - 1) * d$de[2]^2) / (sum(d$n) - 2))
  t  <- (d$media[1] - d$media[2]) / (sp * sqrt(1 / d$n[1] + 1 / d$n[2]))
  c(t = t, gl = sum(d$n) - 2, p = 2 * pt(-abs(t), sum(d$n) - 2))
}

# Pb-S según Beery (reportan P = 0,834): la exposición tratada como desenlace
t_beery <- t_resumen(pb_segun_beery)
t_beery

# Pb-S según Pb-S >= 10 vs. < 10 (reportan P = 0,001): los grupos se definen
# por el propio plomo, así que la diferencia es obligatoria y no informa nada
t_circular <- t_resumen(pb_segun_exposicion)
t_circular

# Pb-S según sexo (reportan P = 0,042)
t_sexo <- t_resumen(setNames(por_sexo[, c("sexo", "n", "pb_media", "pb_de")],
                             c("grupo", "n", "media", "de")))
t_sexo

# Razón de prevalencias (RP) y razón de odds (OR) con IC 95 %
res_2x2 <- epi.2by2(tabla, method = "cross.sectional", conf.level = 0.95)
res_2x2

medidas <- res_2x2$massoc.summary
rp <- medidas[medidas$var %in% c("Prev risk ratio", "Prev ratio"), c("est", "lower", "upper")]
or <- medidas[medidas$var %in% c("Prev odds ratio", "Odds ratio"), c("est", "lower", "upper")]

# Prueba de hipótesis. Una frecuencia esperada es < 5 (celda <10 / no inferior),
# por eso se prefiere la exacta de Fisher sobre chi-cuadrado.
chisq.test(tabla)$expected
prueba_fisher <- fisher.test(tabla)
prueba_fisher

# Gráfico: proporción de Beery inferior por grupo de plomo, con IC 95 % (Wilson)
prop_grupo <- data.frame(
  plomo = factor(rownames(tabla), levels = rownames(tabla)),
  casos = tabla[, "Inferior"],
  n     = rowSums(tabla)
)
ic <- t(mapply(function(x, n) prop.test(x, n, correct = FALSE)$conf.int,
               prop_grupo$casos, prop_grupo$n))
prop_grupo$p     <- prop_grupo$casos / prop_grupo$n
prop_grupo$lower <- ic[, 1]
prop_grupo$upper <- ic[, 2]

grafico_proporciones <- ggplot(prop_grupo, aes(plomo, p)) +
  geom_col(fill = "#6a8caf", width = 0.55) +
  geom_errorbar(aes(ymin = lower, ymax = upper), width = 0.15) +
  geom_text(aes(label = sprintf("%d/%d\n(%.0f %%)", casos, n, 100 * p)),
            y = 0.08, colour = "white", fontface = "bold") +
  scale_y_continuous(labels = function(x) paste0(100 * x, " %"),
                     limits = c(0, 1)) +
  labs(x = "Plomo en sangre (µg/dL)", y = "Beery inferior",
       title = "Prevalencia de Beery inferior según exposición al plomo",
       subtitle = "Barras de error: IC 95 % (Wilson)") +
  theme_minimal(base_size = 12)
grafico_proporciones

# Sexo: la discusión dice que los varones tienen más Beery inferior porque
# son 27 vs. 21 niñas. Pero hay más varones (35 vs. 25): hay que comparar
# proporciones, no conteos.
tabla_sexo <- matrix(
  c(por_sexo$beery_inferior, por_sexo$n - por_sexo$beery_inferior),
  nrow = 2, dimnames = list(Sexo = por_sexo$sexo, Beery = c("Inferior", "No inferior"))
)
tabla_sexo
prop_sexo <- por_sexo$beery_inferior / por_sexo$n
names(prop_sexo) <- por_sexo$sexo
round(100 * prop_sexo, 1)
rp_sexo <- unname(prop_sexo[1] / prop_sexo[2])
rp_sexo
fisher_sexo <- fisher.test(tabla_sexo)
fisher_sexo$p.value
