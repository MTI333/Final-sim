# Supuestos y puntos a confirmar con la cátedra

Documento vivo: se actualiza cada vez que surge una ambigüedad nueva. Cada supuesto acá listado
tiene su default reflejado en el código con un comentario `# TODO: confirmar con cátedra`.

---

## 1. ⚠️ Unidad de la tasa de llegadas (crítico)

**Enunciado:** "clientes llegan de acuerdo con una distribución Poisson con media de 4
clientes/minuto."

**Ambigüedad:** leído literalmente, λ = 4 clientes/min es una tasa altísima frente a una atención
media de 15 min por cliente (utilización ρ = λ / (3·μ) = 4 / (3·(1/15)) = 20, es decir 2000%). Con
ese valor el sistema es inestable: la cola crece sin techo durante toda la corrida, y "cola
máxima" terminaría dominada por la duración de la simulación en vez de por la dinámica real del
sistema.

**Default adoptado:** tiempo entre llegadas ~ Exponencial(media = 0,25 min), es decir λ=4/min,
tal como dice el enunciado de forma literal.

**Alternativa considerada:** interpretar "media de 4 clientes/minuto" como redacción confusa de
"1 cliente cada 4 minutos" (media entre llegadas = 4 min). Con esta lectura ρ ≈ 1,25: sigue siendo
un sistema saturado, pero mucho más razonable para un centro de copiado con 3 máquinas.

**Acción:** parametrizado (`mean_interarrival_time`), un solo lugar para cambiarlo si en algún
momento se necesitara.

**Decisión final (2026-07-21):** se adopta de forma definitiva la lectura literal del enunciado
(λ=4/min, `mean_interarrival_time=0,25`), sin esperar confirmación de la cátedra. Se prioriza
apegarse al texto tal como está escrito por sobre "corregirlo" hacia una lectura que dé un
sistema más estable — la inestabilidad resultante (ρ=2000%, cola sin techo) es una consecuencia
esperada y aceptada de esa elección, no un error a evitar. Deja de ser un punto a confirmar con la
cátedra.

---

## 2. Interrupción por mantenimiento correctivo

**Default:** no se interrumpe una atención en curso. La copiadora termina de atender al cliente
actual y **recién entonces** entra a mantenimiento, aunque `uso_restante` haya llegado a `<= 0`
antes de que termine esa atención.

**Justificación:** el enunciado no menciona un evento de interrupción, y el prompt (§5.3) solo
define tres tipos de evento programado (Llegada, Fin de atención, Fin de mantenimiento). Modelar
una interrupción requeriría partir el evento "fin de atención" en dos o reprogramarlo, lo cual no
está contemplado.

**Alternativa descartada:** interrumpir la copia apenas `uso_restante` llega a 0 (el cliente en
curso quedaría con la copia a medio hacer, sin que el enunciado aclare qué pasa con él).

**Acción:** `# TODO: confirmar con cátedra`.

---

## 3. Fórmula de generación de la exponencial

**Default:** `T = -media * ln(1 - RND)`, con `RND ~ Uniforme(0,1)`.

**Justificación:** es la convención estándar de la cátedra de Simulación (método de la transformada
inversa). Es matemáticamente equivalente a `-media * ln(RND)` porque `RND` y `1-RND` tienen la
misma distribución Uniforme(0,1), pero se deja aislada en una función `exponential(mean, rnd)` para
poder cambiar la forma exacta en un solo lugar si la cátedra pide la otra variante.

**Acción:** `# TODO: confirmar con cátedra`.

---

## 4. ⚠️ Umbral mínimo para disparar la regla preventiva

**Default:** se aplica siempre que las 3 copiadoras están libres simultáneamente, sin exigir un
uso mínimo acumulado (lectura literal del enunciado: "en el caso de que las 3 copiadoras estén
libres... se debe realizar el mantenimiento").

**Riesgo del default confirmado empíricamente (Etapa 4):** con este default, en un escenario de
carga moderada (`mean_interarrival_time=6`, ρ≈0,83, 50.000 iteraciones, semilla 42) la regla
preventiva se disparó **353 veces** y el mantenimiento **correctivo no se disparó ni una sola
vez** (0 sobre 50.000 iteraciones). En un escenario de baja carga (`mean_interarrival_time=30`,
ρ≈0,17) la preventiva se disparó **5201 veces** con 0 correctivos. Es decir: sin umbral mínimo, la
regla preventiva "captura" a las copiadoras mucho antes de que puedan acumular las 10.200-13.800
min de uso necesarias para un correctivo, y el mecanismo de mantenimiento correctivo por uso
**queda vacío/vestigial** en la práctica salvo en cargas muy altas y sostenidas. Esto es
sospechoso: el enunciado describe dos mecanismos distintos (correctivo por uso, preventivo
aprovechando huecos), y no parece la intención que uno anule por completo al otro.

**Alternativa descartada:** exigir que la copiadora candidata tenga `uso_restante` por debajo de
cierto umbral (p. ej. <20% de su `umbral_actual`) antes de aplicar la regla preventiva — esto
dejaría que el correctivo también ocurra en cargas bajas/moderadas.

**Decisión final (2026-07-21):** mismo criterio que el #1 — se mantiene la lectura literal
(sin umbral mínimo) de forma definitiva, sin esperar confirmación de la cátedra. Se acepta que el
mantenimiento correctivo quede vestigial en cargas moderadas/bajas como consecuencia esperada de
apegarse al enunciado tal como está escrito, no como un bug a corregir. Deja de ser un punto a
confirmar con la cátedra — el hallazgo empírico queda documentado arriba como contexto para la
defensa oral (por si preguntan por qué el correctivo casi no aparece en las corridas), pero ya no
como pregunta abierta.

---

## 5. Selección de copiadora al asignar un cliente entrante

**Default:** entre las copiadoras libres, se asigna la de **mayor `uso_restante`** (la más lejana
a fallar).

**Justificación:** coherente con la lógica preventiva de todo el problema: se reserva "fresca"
(cerca de fallar) a la copiadora que más la va a necesitar más adelante, minimizando la chance de
que falle en medio de una atención larga con clientes esperando.

**Alternativa descartada:** asignar la de menor `uso_restante` primero (agotaría antes a las
copiadoras más "viejas", entra en tensión con la regla preventiva) / orden fijo por índice (más
simple pero sin justificación de negocio, y rompe cuando dos tienen `uso_restante` similar).

**Acción:** `# TODO: confirmar con cátedra`.

---

## 6. Criterio de desempate cuando dos copiadoras tienen igual `uso_restante`

**Contexto:** no está explícito en el enunciado. Aplica tanto a la selección de copiadora libre
para un cliente (supuesto 5) como a la elección de "la más próxima a fallar" en la regla
preventiva (§6.2 del prompt).

**Default:** desempate determinístico por índice/ID de copiadora (se elige la de menor ID entre
las empatadas). Elegido para que la simulación sea 100% reproducible con semilla fija.

**Acción:** documentado, no requiere confirmación con la cátedra — es un detalle de implementación
sin impacto en el resultado esperado, se deja constancia por transparencia.

---

## 7. Generador de números pseudoaleatorios (RND)

**Ambigüedad:** el enunciado y el prompt piden "mostrar el RND usado" para cada variable
aleatoria, pero no aclaran si debe implementarse un generador congruencial propio (tradición
frecuente en TPs de Simulación) o alcanza con el generador estándar del lenguaje.

**Default:** se usa `random.random()` de Python (Mersenne Twister) con semilla fija configurable,
ya que el foco del TP es la lógica de simulación de eventos discretos, no la calidad del generador
de aleatorios. Se aísla en una función `rnd()` para poder reemplazar el generador por uno
congruencial propio sin tocar el resto del código si la cátedra lo exige.

**Acción:** `# TODO: confirmar con cátedra`.

---

## 8. Estado inicial del sistema (t = 0)

**No especificado en el enunciado.**

**Default:** las 3 copiadoras arrancan en estado **Libre**, cada una con un `umbral_actual`
sorteado independientemente ~ Uniforme[10200; 13800] min, y `uso_restante = umbral_actual`. La
cola común arranca vacía. Se programa la primera llegada sorteando el primer tiempo entre
llegadas desde t=0.

**Justificación:** es el estado de "sistema recién puesto en marcha", consistente con no tener
información previa sobre desgaste de las copiadoras.

**Acción:** documentado como default razonable; no crítico salvo que la cátedra tenga un estado
inicial estándar distinto (por ejemplo, arrancar con umbrales ya parcialmente consumidos).

---

## 9. Condición de fin de simulación (parámetro X)

**No hay un valor dado:** el enunciado no fija un tiempo límite. El prompt (§8) pide simular
hasta 100.000 iteraciones **o** hasta el tiempo X, lo que ocurra primero, dejando X como
parámetro libre.

**Default para pruebas:** X queda configurable sin un valor "quemado"; se usará un valor de
prueba razonable al llegar a la etapa de validación (por ejemplo, una corrida larga en minutos
equivalente a varios meses de operación), documentado en `VALIDACION.md` en ese momento.

**Acción:** parametrizado, no requiere confirmación con la cátedra — es explícitamente un
parámetro libre según §8 del prompt.

---

*Última actualización: 2026-07-21 — #1 y #4 cerrados como decisión final (se prioriza apego
literal al enunciado sobre estabilidad del resultado).*
