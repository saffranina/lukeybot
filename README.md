# PlomoBot

Reanálisis en R de un artículo sobre plomo en sangre y coordinación visomanual en niños.

Proyecto de R para la lectura crítica del artículo:

> Squillante G, Rojas M, Medina E, et al. Plomo en sangre y coordinación
> visomanual en niños. *Gac Méd Caracas*. 2005;113(1):50-57.

## Qué contiene

| Archivo | Qué hace |
|---|---|
| `R/00_instalar_paquetes.R` | Instala los paquetes necesarios (correr una sola vez) |
| `R/01_datos.R` | Datos de los Cuadros 1 a 4 del artículo |
| `R/02_asociacion.R` | **Parte 1:** reproduce las t de Student de los autores; RP y OR con IC 95 %, Fisher, gráfico de proporciones y análisis por sexo |
| `R/03_tamano_muestral.R` | **Parte 2:** tamaño muestral (el de los autores vs. el correcto), potencia real y curva de potencia |
| `R/04_simulacion_edad.R` | **Parte 3:** DAG y simulación de la confusión por edad (datos **simulados**) |
| `reporte.qmd` | **Parte 4:** reporte Quarto que junta todo con texto, código y gráficos |
| `presentacion.html` | Presentación interactiva para la clase (se abre en el navegador; ← → para avanzar) |

## Cómo usarlo

1. Abre `plomobot.Rproj` en RStudio.
2. Corre `R/00_instalar_paquetes.R` una vez.
3. Para ver cada parte por separado, abre los scripts en orden (`01` → `04`) y
   córrelos con *Source*. `01_datos.R` va siempre primero, porque crea la tabla.
4. Para el reporte completo, abre `reporte.qmd` y presiona **Render**.
   Genera un HTML. También puedes elegir Word (`docx`) o PDF (`typst`,
   no necesita LaTeX) desde el menú de Render.

Necesitas [Quarto](https://quarto.org/docs/get-started/). Las versiones recientes
de RStudio ya lo traen instalado.

## Sobre la simulación

El artículo publica el plomo por edad (Cuadro 1) y el Beery por edad (Cuadro 3),
pero no la tabla cruzada plomo × edad × Beery. Por eso la Parte 3 usa **datos
simulados** a partir de esos cuadros. Los supuestos están comentados al inicio de
`R/04_simulacion_edad.R`:

- El Pb-S tiene distribución normal dentro de cada grupo de edad.
- El efecto del plomo (`or_verdadero`) es igual en todas las edades.
- La DE de Pb-S en 8–9 años es 2,6. El Cuadro 1 dice "22,6", que parece una errata.
