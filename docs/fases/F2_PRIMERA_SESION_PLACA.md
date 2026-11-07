# Primera sesión en la placa con STONE OS (rebuild) F2

Guía para el propietario. Se hace en la BC-250, con mando, teclado y una terminal: TTY (Ctrl+Alt+F3) o SSH desde otro equipo.

Nada de esta sesión toca la BIOS, el firmware, las frecuencias, los voltajes, los núcleos ni los CU. Las únicas acciones que cambian el sistema están marcadas con **CAMBIA** y todas tienen vuelta atrás:
- fijar rc23;
- cambiar de imagen;
- elegir la sesión automática.

Lo que se vea se anota como `OBSERVED ON BOARD`, nunca `HARDWARE VERIFIED` (D-08).

## Antes de empezar

- Duración aproximada: 1 h 30 min.
- **Qué traer al Mac al final:**
  - la carpeta `~/stone-diag-<fecha>/`;
  - el archivo `~/stone-f2-<fecha>.txt` del paso 4;
  - fotos de lo que se vea raro en pantalla.
- **Si algo sale mal en cualquier paso:** se sale por la sección «Vuelta atrás». rc23 sigue en el menú de arranque durante toda la sesión.

## Paso 1 · Diagnóstico de solo lectura sobre rc23 (aprobado, D-14)

Se ejecuta antes de cambiar nada, con la consola tal como está hoy. Sigue `docs/diagnostico/PROCEDIMIENTO_DIAGNOSTICO_BC250.md` §3:

```bash
bash stone-diag-readonly.sh
```

Trae la carpeta `~/stone-diag-<fecha>/` al Mac **antes** de seguir. Es la foto de rc23 con la que se comparará F2.

## Paso 2 · Fijar rc23 para que no se borre nunca (**CAMBIA**)

Un sistema bootc guarda dos versiones: la actual y la anterior. Después de dos cambios más, rc23 desaparecería. Fijarla la mantiene en el menú de arranque hasta que se quite la marca.

```bash
sudo ostree admin status
```

La línea con `*` es la versión arrancada, rc23. Si es la primera de la lista, su índice es 0:

```bash
sudo ostree admin pin 0
```

Con `sudo ostree admin status` debe aparecer `Pinned: yes` en rc23. Para quitar la marca más adelante: `sudo ostree admin pin --unpin 0`.

## Paso 3 · Cambiar a la imagen F2 (**CAMBIA**, no borra nada)

1. **En el Mac, comprueba la firma** (`docs/FIRMA.md`):

   ```bash
   cosign verify ghcr.io/irl1997/stone-os-rebuild:dev \
     --certificate-identity-regexp '^https://github.com/irl1997/STONE-OS-REBUILD/\.github/workflows/build-image\.yml@' \
     --certificate-oidc-issuer https://token.actions.githubusercontent.com
   ```

   Anota el `sha256:` que imprime. Si la verificación falla, para aquí.

2. **En la placa:**

   ```bash
   sudo bootc switch ghcr.io/irl1997/stone-os-rebuild:dev
   ```

   Descarga la imagen y la deja preparada. Los datos, juegos y ajustes de `/home` no se tocan. Los argumentos de arranque actuales, como el de 40 CU si rc23 lo tenía, pasan a la versión nueva.

3. Reinicia: `systemctl reboot`.

La consola arranca en el **Game Mode normal de Bazzite**, no en la sesión STONE. F2 no cambia la sesión automática por su cuenta. En F2 tampoco aparece STONE Home sola al arrancar desde Game Mode: el autoarranque de rc23 por un acceso directo de Steam ya no existe (D-21).

## Paso 4 · Comprobaciones en el Game Mode normal (solo lectura)

Abre una terminal (TTY o SSH) y guarda todo en un archivo:

```bash
f=~/stone-f2-$(date +%Y%m%d-%H%M).txt
{ bootc status; cat /usr/lib/stone-release; cat /proc/cmdline; stonectl status; stone-cu40 status;
  systemctl status stoned --no-pager; stone-session status; stone-session boot; systemd-analyze time; } > "$f" 2>&1
echo "$f"
```

Qué se mira:

| Comprobación | Qué se espera |
| --- | --- |
| `bootc status` | Arrancada `ghcr.io/irl1997/stone-os-rebuild:dev` con el mismo `sha256:` que verificó cosign; rc23 como versión anterior |
| `stone-release` | `STONE_PHASE="F2"` |
| `/proc/cmdline` | Los mismos argumentos que en el diagnóstico de rc23 |
| `stonectl status` | `stoned` responde; perfil BALANCED; configuración detectada de 8 núcleos y, si estaba activa, 40 CU |
| `stone-cu40 status` | Lo mismo que en rc23 |

Si `stoned` no responde o la configuración detectada no coincide, para aquí y trae el archivo al Mac.

## Paso 5 · La sesión STONE (**CAMBIA**: la sesión automática)

```bash
sudo stone-session default on
systemctl reboot
```

Desde este reinicio la consola arranca en la sesión STONE: Steam oculto y STONE Home delante. En cada prueba anota lo que pase, sobre todo cualquier pantalla de Steam o de escritorio que aparezca.

| Prueba | Qué hacer | Qué se espera |
| --- | --- | --- |
| T-FR-01 / T-SESS-07 | Primer encendido | FIRST RUN: placa, 8 núcleos, CU; pantalla; Steam (si pide sesión, iniciarla una vez); BALANCED. Todo solo con el mando |
| T-SESS-01 / T-BOOT-01 | Apagar y encender 5 veces | Plymouth y luego Home, sin pantallas de Steam. Después, `stone-session boot` lista los 5 arranques |
| T-SESS-02 | JUGAR en un juego instalado; salir del juego | El juego aparece delante; al salir vuelve Home |
| T-SESS-03 | Jugar unos minutos con el mando | El mando funciona dentro del juego |
| T-SESS-04 | Durante el juego, botón guía; luego REANUDAR | Home delante con el juego abierto; REANUDAR devuelve el juego. Anota si también aparece algo de Steam |
| T-SESS-08 | Ajustes → una fila «Abrir en Steam» | Anota si el panel de Steam se ve delante de Home |
| T-UPD-01 | Ajustes → Actualizaciones | Versión instalada y estado de la comprobación automática |

Al terminar, el estado de la sesión, incluida la recuperación si saltó:

```bash
stone-session status
cat ~/.local/state/stone/session.log
```

## Vuelta atrás

| Situación | Qué hacer |
| --- | --- |
| La sesión STONE falla pero aparece el Game Mode de Steam | Es la recuperación automática (D-21). En la terminal: `stone-session status` dice por qué |
| Pantalla negra o la sesión no arranca | Ctrl+Alt+F3, entra con el usuario de la consola, `sudo stone-session default off`, `systemctl reboot`. Vuelve el Game Mode de Bazzite |
| Cualquier problema con la imagen F2 | En el menú de arranque elige la entrada de rc23 o, desde una terminal, `sudo bootc rollback` y reinicia. rc23 conserva su propia configuración: la sesión automática de F2 no la afecta |
| Volver a rc23 de forma definitiva | `sudo bootc switch` a la imagen de rc23, con la referencia que muestre el diagnóstico del paso 1 (`bootc status`) |

## Qué se hace después en el Mac

- Se compara el diagnóstico de rc23 con el archivo del paso 4.
- Cada prueba de la tabla pasa a `OBSERVED ON BOARD` en `hardware/validation/matrix.yaml`, con lo que se vio.
- Se cierran o se reabren V-13, V-14, V-15, V-18 y V-19 según el resultado.
- Con T-SESS-04 se decide si se construye el Quick Menu superpuesto (plan A de V-13).
