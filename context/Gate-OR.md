# Gate-OR — RtG-Video

## 1. Propósito

Los `Gate-OR` de RtG-Video **no son decoración** y no se generan arbitrariamente.
Su propósito es resolver una limitación de las conexiones de RtG:

> Un mismo punto de destino no puede recibir múltiples `Wire` independientes directamente.

Cuando varios frames necesitan activar el mismo Pixel, sus señales deben combinarse antes de llegar al Pixel. El `Gate-OR` permite combinar dos señales en una sola.

Conceptualmente:

```text
Signal A ──┐
           ├── Gate-OR ──► Signal AB
Signal B ──┘
```

donde:

```text
Signal AB = Signal A OR Signal B
```

La salida resultante puede volver a utilizarse como entrada de otro `Gate-OR`.

---

# 2. Regla fundamental

Un `Gate-OR` debe existir **solamente cuando sea necesario para combinar múltiples señales**.

No se debe crear un `Gate-OR` simplemente porque:

* hay un Pixel;
* hay un frame;
* hay espacio físico;
* se necesita colocar algo debajo de otro objeto;
* se quiere completar una cadena visual;
* o existe una tabla física de `Gate-OR`.

Un `Gate-OR` que solamente recibe una señal no aporta ninguna función lógica.

Ejemplo incorrecto:

```text
Frame
  │
 Wire
  │
  ▼
 OR
  │
 Wire
  │
Pixel
```

La señal podría ir directamente:

```text
Frame
  │
 Wire
  │
Pixel
```

Por lo tanto, el primer caso desperdicia un `Gate-OR` y objetos/conexiones adicionales sin producir ninguna ventaja.

---

# 3. Caso de una sola fuente

Si un Pixel solamente aparece en un frame, no necesita ningún `Gate-OR`.

```text
Delayer
   │
   ▼
 Wire
   │
   ▼
 Pixel
```

Número de `Gate-OR`:

```text
0
```

Esta optimización debe conservarse.

---

# 4. Caso de dos fuentes

Si un Pixel aparece en dos frames, las dos señales deben combinarse **antes de llegar al Pixel**.

```text
Frame A ──► Wire ──┐
                   │
                   ▼
                 Gate-OR ──► Wire ──► Pixel
                   ▲
                   │
Frame B ──► Wire ──┘
```

El `Gate-OR` recibe las dos señales y produce una única señal de salida.

El Pixel recibe únicamente esa salida final:

```text
Frame A ──► Wire ──┐
                   ▼
                 Gate-OR ──► Wire ──► Pixel
                   ▲
Frame B ──► Wire ──┘
```

Número de `Gate-OR`:

```text
1
```

**Regla:** un Pixel nunca debe utilizarse como punto de convergencia de múltiples señales. La convergencia debe realizarse previamente mediante un `Gate-OR` u otra compuerta lógica que soporte múltiples entradas.


---

# 5. Árbol lógico

Cuando existen varias fuentes, los `Gate-OR` forman un **árbol lógico binario**.

Todas las ramas convergen progresivamente hasta producir **una única salida final**.

Ejemplo con cuatro fuentes:

```text
                 OR0
                /   \
              OR1   OR2
             /  \   /  \
           F1   F3 F7   F9
```

La señal fluye desde las hojas hacia el root:

```text
F1 ──► Wire ──► OR1 Input A
F3 ──► Wire ──► OR1 Input B

F7 ──► Wire ──► OR2 Input A
F9 ──► Wire ──► OR2 Input B

OR1 ──► Wire ──► OR0 Input A
OR2 ──► Wire ──► OR0 Input B

OR0 ──► Wire ──► Pixel
```

La topología completa es:

```text
                    OR0
                   /   \
                 OR1   OR2
                /  \   /  \
              F1   F3 F7   F9
                         │
                         │
                         ▼
                    OR0 Output
                         │
                        Wire
                         │
                         ▼
                       Pixel
```

El Pixel solamente recibe el `Wire` procedente del `OR0`, que es el root.

Por lo tanto:

> **La convergencia de múltiples señales ocurre dentro de la lógica, nunca en el Pixel.**

Un Pixel siempre debe terminar teniendo una única entrada de señal.

---

# 6. Dirección de la señal

La dirección lógica siempre es:

```text
Frame source
    ↓
  Wire
    ↓
 Gate-OR
    ↓
  Wire
    ↓
 Gate-OR
    ↓
  Wire
    ↓
 Pixel
```

El árbol se debe interpretar desde las hojas hacia el root.

Por ejemplo:

```text
                 Pixel
                   ▲
                  Wire
                   ▲
                  OR0
                /     \
              Wire    Wire
               ▲        ▲
              OR1      OR2
             /  \      /  \
           Wire Wire  Wire Wire
             ▲    ▲     ▲    ▲
            F1   F3    F7   F9
```

La representación visual puede mostrar el árbol de cualquier forma conveniente, pero la topología lógica debe conservar esta dirección.

---

# 7. Los Gate-OR tienen dos entradas lógicas

RtG identifica los puntos lógicos del `Gate-OR` de esta manera:

```text
1 = Output
2 = Input A
3 = Input B
```

Por lo tanto:

```text
             Output
                ▲
                │
             Gate-OR
            /       \
       Input A    Input B
```

Un `Gate-OR` puede tener como máximo dos entradas lógicas directas.
Esto es lo que hace que el árbol sea binario.

---

# 8. Un hijo puede ser otro Gate-OR o un Wire

Una entrada de un `Gate-OR` puede recibir la salida lógica de:

1. Un `Wire` proveniente de un frame.
2. Un `Wire` que transporta la salida de otro `Gate-OR`.

Por ejemplo:

```text
               OR0
              /   \
            OR1   Wire
           /  \     │
        Wire Wire   F7
         │    │
        F1   F3
```

La conexión lógica sería:

```text
F1 ──► Wire ──► OR1 Input A
F3 ──► Wire ──► OR1 Input B

OR1 ──► Wire ──► OR0 Input A

F7 ──► Wire ──► OR0 Input B
```

El `Wire` es el elemento que transporta la señal entre objetos.

---

# 9. El root del árbol

Cada árbol asociado a un Pixel tiene un `Gate-OR` raíz cuando existen suficientes fuentes para necesitarlo.
El root es el `Gate-OR` cuya salida representa la combinación final de todas las fuentes de ese árbol.

Ejemplo:

```text
                 OR0  ← ROOT
                /   \
              OR1   OR2
             /  \   /  \
            F1  F3 F7  F9
```

La salida de `OR0` es la que finalmente se conecta al Pixel:

```text
OR0
 │
 ▼
Wire
 │
 ▼
Pixel
```

El Pixel **no debe conectarse directamente a un `Gate-OR` intermedio** si existe un root superior.

---

# 10. El árbol no es necesariamente una cadena

Esta estructura es incorrecta como modelo lógico:

```text
OR0
 │
OR1
 │
OR2
 │
OR3
```

Aunque pueda existir una disposición física parecida, no significa que las señales deban seguir esa estructura.

El objetivo lógico es reducir múltiples fuentes a una sola señal utilizando la menor cantidad necesaria de `Gate-OR`.
La estructura correcta puede ser:

```text
             OR0
            /   \
          OR1   OR2
         /  \   /  \
        F1  F3 F7  F9
```

o una estructura más profunda:

```text
                 OR0
                /   \
              OR1   OR2
             /  \     \
            F1  OR3    F7
               /  \
              F3  F5
```

En ambos casos, el criterio es la topología lógica, no la forma visual.

---

# 11. Cantidad mínima de Gate-OR

Para combinar `N` fuentes independientes en una única señal, un árbol binario necesita como mínimo:

```text
N - 1
```

`Gate-OR`.

Ejemplos:

| Fuentes | Gate-OR mínimo |
| ------: | -------------: |
|       0 |              0 |
|       1 |              0 |
|       2 |              1 |
|       3 |              2 |
|       4 |              3 |
|       5 |              4 |
|       6 |              5 |
|       7 |              6 |
|       8 |              7 |

La fórmula solamente describe la necesidad lógica de combinar las fuentes.
La generación física puede tener consideraciones adicionales, pero **no se deben agregar OR lógicos innecesarios**.

---

# 12. Separación entre estructura física y estructura lógica

RtG-Video debe distinguir dos conceptos:

## Estructura física

Los objetos necesitan estar físicamente conectados para que la build final sea un único objeto individual y no queden partes sueltas.

Por eso los `Gate-OR` se **pegan/anclan físicamente a otros objetos**.
Esto es independiente de su función lógica.

Por ejemplo:

```text
Base
 │
 ▼
OR0
 │
 ▼
OR1
 │
 ▼
OR2
```

puede ser una estructura de anclaje físico.

No significa que la señal lógica tenga que ser:

```text
OR0 → OR1 → OR2
```

---

# 13. Objetivo del anclaje físico

El objetivo del anclaje físico es que la build completa termine siendo:

```text
             ┌───────────────┐
             │   RtG Build   │
             │               │
             │ Base          │
             │ Pixels        │
             │ Gate-ORs      │
             │ Wires         │
             │ Delayers      │
             │ ...           │
             └───────────────┘
```

como **un objeto individual conectado físicamente**, en lugar de contener partes independientes flotando sin formar parte del mismo conjunto.

Por lo tanto:

> La conexión física existe para la integridad de la build.
> La conexión mediante `Wire` existe para la lógica de señales.

Son dos sistemas diferentes.

---

# 14. Posición inicial y ocultamiento de los Gate-OR

Los `Gate-OR` forman parte real de la build y deben estar físicamente conectados para que la construcción final permanezca como un único objeto individual.

Sin embargo, su función lógica no requiere que sean visibles.

Por ello, durante la generación física, los `Gate-OR` pueden conectarse inicialmente mediante UUIDs en una posición base:

```text
0,0,0
```

Esta posición funciona como una posición inicial común durante la construcción.

Posteriormente, se ajusta la dirección/orientación de los `Gate-OR` para colocarlos de forma que queden **ocultos dentro del bloque `Base`**.

Conceptualmente:

```text
                 Base
        ┌────────────────────┐
        │                    │
        │   Gate-ORs ocultos │
        │   ┌──┐ ┌──┐ ┌──┐   │
        │   │OR│ │OR│ │OR│   │
        │   └──┘ └──┘ └──┘   │
        │                    │
        └────────────────────┘
```

Esto tiene dos objetivos diferentes:

1. **Integridad física:** los `Gate-OR` quedan conectados a la estructura de la build.
2. **Presentación:** los `Gate-OR` no quedan visibles como objetos decorativos independientes.

El ocultamiento físico no modifica la topología lógica.

Es decir, aunque un `Gate-OR` esté físicamente dentro de `Base`, sus conexiones de señal siguen siendo:

```text
Wire ──► Gate-OR Input
Gate-OR Output ──► Wire
```

La posición física y la dirección utilizada para ocultarlo no deben interpretarse como conexiones de señal.

---

## Regla importante

El sistema debe generar primero la existencia física de los `Gate-OR` y su anclaje necesario.

Después puede ajustar su posición/orientación para ocultarlos dentro de `Base`.

No se debe modificar la topología lógica únicamente para conseguir el ocultamiento físico.

---

# 15. La tabla física de Gate-OR

RtG-Video puede generar previamente una tabla física de `Gate-OR`.
Esta tabla devuelve los índices de los objetos creados.

Conceptualmente:

```python
gate_indexes = [
    OR0_INDEX,
    OR1_INDEX,
    OR2_INDEX,
    OR3_INDEX,
    ...
]
```

Estos índices representan objetos que **ya existen en la build**.

La etapa posterior de conexión lógica debe utilizar estos objetos existentes.
No debe crear nuevos `Gate-OR` solamente porque necesita conectar una señal.

---

# 16. Regla para `_connect_pixel_sources()`

`_connect_pixel_sources()` no debe crear `Gate-OR` nuevos.

Su función debe ser conectar las fuentes al árbol de `Gate-OR` previamente generado.

Conceptualmente:

```text
                    árbol OR preexistente
                              │
                              ▼
Frame sources ──► Wires ──► Gate-ORs ──► Wire ──► Pixel
```

No:

```text
Frame sources
     │
     ▼
_connect_pixel_sources()
     │
     ├── crea OR
     ├── crea OR
     └── crea OR
```

La etapa de generación y la etapa de conexión deben estar separadas.

---

# 17. No confundir "pre-generado" con "decorativo"

Que los `Gate-OR` sean pre-generados físicamente no significa que todos deban recibir una señal.

Cada `Gate-OR` que forme parte de un árbol lógico debe tener una función real.
Si un objeto no es necesario para combinar señales, no debería existir como parte de la topología lógica.

El sistema debe evitar:

```text
Wire → OR de una entrada
```

y también evitar ORs que nunca participan en la señal final.

---

# 18. Ejemplo completo

Supongamos que un Pixel está activo en:

```text
Frame 1
Frame 3
Frame 7
Frame 9
```

Los Delayers correspondientes son:

```text
D1
D3
D7
D9
```

Las fuentes serían:

```text
D1
D3
D7
D9
```

La topología puede ser:

```text
                    OR0
                   /   \
                 OR1   OR2
                /  \   /  \
               W1  W3 W7  W9
               ▲   ▲  ▲   ▲
               │   │  │   │
              D1  D3 D7  D9
```

Conexiones:

```text
D1  → W1  → OR1 Input A
D3  → W3  → OR1 Input B

D7  → W7  → OR2 Input A
D9  → W9  → OR2 Input B

OR1 → Wire → OR0 Input A
OR2 → Wire → OR0 Input B

OR0 → Wire → Pixel
```

Cantidad de Gate-OR:

```text
3
```

Ninguno es redundante.

---

# 19. Ejemplo con tres fuentes

Para:

```text
Frame 1
Frame 3
Frame 7
```

podemos utilizar:

```text
              OR0
             /   \
           OR1   W7
          /  \    │
         W1  W3   │
         │    │   │
         F1   F3  F7
```

Conexiones:

```text
F1 → W1 → OR1 Input A
F3 → W3 → OR1 Input B

OR1 → Wire → OR0 Input A
F7  → W7  → OR0 Input B

OR0 → Wire → Pixel
```

Cantidad:

```text
2 Gate-OR
```

---

# 20. Ejemplo con una fuente

Para:

```text
Frame 4
```

no se crea ningún OR:

```text
F4
 │
 ▼
Wire
 │
 ▼
Pixel
```

Esto es obligatorio como optimización.

---

# 21. Regla de oro

El sistema debe poder responder esta pregunta para cada `Gate-OR`:

> "¿Qué múltiples señales estoy combinando con este objeto?"

Si la respuesta es:

```text
ninguna
```

o:

```text
solamente una
```

ese `Gate-OR` probablemente no debería formar parte de la lógica.
Los `Gate-OR` existen para **combinar señales**, no para decorar, rellenar espacio ni representar frames individualmente.

---

# 22. Arquitectura final esperada

El sistema completo debe entenderse en estas capas:

```text
┌───────────────────────────────────────────────┐
│                  FRAME SOURCES                │
│                                               │
│ D0   D1   D2   D3   D4   D5   D6   D7       │
└─┬────┬────┬────┬────┬────┬────┬────┬────────┘
  │    │    │    │    │    │    │    │
  ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
 W    W    W    W    W    W    W    W
  │    │    │    │    │    │    │    │
  └────┴────┘    └────┴────┘    ...
       │               │
       ▼               ▼
      OR              OR
       │               │
       └───────┬───────┘
               ▼
              OR
               │
              Wire
               │
               ▼
             Pixel
```

Mientras tanto, físicamente:

```text
              Base
               │
             OR/...
               │
             OR/...
               │
             OR/...
               │
            Pixel/build
```

La estructura física mantiene la build unida.
La estructura lógica transporta las señales.

---

# 23. Requisito para la implementación futura

Antes de modificar `_connect_pixel_sources()`, el sistema debe conocer la correspondencia entre:

```text
Pixel
   ↓
su árbol de Gate-OR
   ↓
root
   ↓
hijos
   ↓
subárboles
   ↓
hojas/Wires
```

Una lista plana de índices:

```python
[100, 101, 102, 103]
```

no contiene suficiente información por sí misma para describir una topología arbitraria.

Debe existir alguna forma de saber:

```text
OR0
├── OR1
│   ├── source F1
│   └── source F3
└── OR2
    ├── source F7
    └── source F9
```

La representación exacta de esa relación debe definirse antes de implementar la conexión automática.

---

# 24. Resumen de reglas

1. `Gate-OR` existe para combinar señales.
2. No es decoración.
3. No debe existir un `Gate-OR` de una sola entrada útil.
4. Una sola fuente → `Wire → Pixel`, sin OR.
5. Varias fuentes → árbol de OR.
6. Cada OR tiene como máximo dos entradas lógicas.
7. Los Wires transportan las señales.
8. Un subárbol puede alimentar otro OR.
9. El root representa la señal combinada final.
10. El root termina conectado al Pixel.
11. `_connect_pixel_sources()` no debe crear OR nuevos.
12. Los OR deben utilizarse desde la tabla previamente generada.
13. La estructura física y la estructura lógica son independientes.
14. Los OR se anclan físicamente para mantener la build como un único objeto individual.
15. Un anclaje físico no implica una conexión lógica.
16. La topología lógica debe estar definida explícitamente.
17. No se debe asumir que una lista de ORs es una cadena lógica.
18. No se deben generar objetos que no tengan una función necesaria dentro de la build.

---

## Modelo mental definitivo

```text
                 ┌──────────────────┐
                 │  ESTRUCTURA      │
                 │     FÍSICA       │
                 │                  │
                 │ "Mantener todo   │
                 │  unido"          │
                 └────────┬─────────┘
                          │
                          │
                 Gate-OR físicamente
                    anclado a objetos
                          │
                          ▼
                 ┌──────────────────┐
                 │   ESTRUCTURA     │
                 │     LÓGICA       │
                 │                  │
                 │ "Combinar varias │
                 │  señales"        │
                 └────────┬─────────┘
                          │
                          ▼
                 Frame → Wire
                          │
                          ▼
                      Gate-OR
                       /    \
                    Wire    Wire
                     │        │
                   Gate-OR   Frame
                     │
                     ▼
                    Wire
                     │
                     ▼
                   Pixel
```

**Los dos sistemas deben coexistir, pero no deben confundirse.**

## Regla de convergencia

* Un Pixel **no puede ni debe recibir múltiples entradas de señal**.
* Un Pixel recibe exactamente **una señal final**.
* Las múltiples fuentes se combinan previamente mediante `Gate-OR` u otras compuertas lógicas capaces de recibir múltiples entradas.
* La salida del root del árbol es la señal que finalmente llega al Pixel mediante un único `Wire`.
* Los `Gate-OR` son los puntos de convergencia de la señal, no los Pixels.

Modelo correcto:

```text
Sources
  │
  ├──► Wire ──┐
  │            │
  ├──► Wire ──► Gate-OR ──► Wire ──► Pixel
  │            ▲
  └──► Wire ───┘
```

Nunca:

```text
Wire ──────────► Pixel
Wire ──────────► Pixel
Wire ──────────► Pixel
```

ni:

```text
Gate-OR ──► Pixel
Wire ─────► Pixel
```

El Pixel debe tener una única entrada final.
