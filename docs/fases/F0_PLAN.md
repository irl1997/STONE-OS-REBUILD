# F0 — Plan de la imagen base

Estado: **APROBADO el 2026-11-06, con F0-A a F0-D. En implementación.**
Referencias:
- `../DECISIONES_TECNICAS.md`: D-16 a D-19, R-01, R-03, R-09 a R-12.
- `../ARQUITECTURA_STONE_MACHINE.md`: M01, M02, M04 y §5.

## 1. Objetivo

Una imagen bootc de STONE OS que se construya y se publique de forma reproducible desde este repositorio, con:
- la base Bazzite fijada;
- el arranque STONE;
- la consola sin reposo;
- el regulador v0.4.14 fijado;
- el mecanismo de 40 CU de rc23, para conservar la configuración de referencia de 8 núcleos y 40 CU.

Todo verificado por software. La puerta de placa queda **diferida** (D-19).

## 2. Alcance

| Entra en F0 | Origen en rc23 | Destino (R-10) |
| --- | --- | --- |
| Estructura del repositorio, `VERSION`, licencia, `.gitignore` | raíz | raíz |
| `Containerfile` (etapas `ctx`, `cu40`, base, lint) | `Containerfile` | `image/Containerfile` |
| `build.sh` **reducido a F0**: copia de rootfs, kernel check, regulador, sin reposo, HHD enmascarado, Plymouth + dracut, 40 CU, `stone-release` | `build_files/build.sh` | `image/build_files/build.sh` |
| `check-kernel.sh`, `governor-config.py` | `build_files/` | `image/build_files/` |
| Módulo `amdgpu` con opción 40 CU + `stone-cu-verify` | `build_files/cu40/` | `image/build_files/cu40/` |
| `stone-cu40` (`status`, `guard`, `enable`, `disable`, `test`) y `stone-cu40-guard.service` | `system_files/usr/bin/stone-cu40`, `usr/lib/stone/stone_cu40.py`, unidad | `system/` |
| Bloqueo de reposo | `sleep.conf.d/50-stone-no-sleep.conf` + máscaras en `build.sh` | `system/` + `build.sh` |
| Tema Plymouth `stone` | `usr/share/plymouth/themes/stone/` | `system/` |
| `config/build.env`, `disk_config/iso.toml` | ídem | `image/config/`, `image/disk_config/` |
| Workflows: CI, build de imagen, ISO (release en F0 sólo como borrador) | `.github/` | `.github/` |
| `validate.sh` adaptado a la nueva estructura | `scripts/validate.sh` | `scripts/` |
| Perfil de placa `hardware/bc250.yaml` (sólo datos documentados, cada uno con su origen y estado) | nuevo (R-05) | `hardware/` |
| Matriz de validación legible por máquina | `HARDWARE_VALIDATION.md` | `hardware/validation/` |
| Contenedor de desarrollo Fedora 44 | nuevo (R-11) | `dev/` |
| Pruebas: `test_cu40.py`, `test_cu40_patch.py`, prueba de `governor-config.py` | `tests/` | `tests/` (pytest, R-11) |

| No entra en F0 (fase) | Motivo |
| --- | --- |
| `stoned`, `stoned-recover`, D-Bus, polkit (F1) | Núcleo de rendimiento propio |
| STONE Home, vídeo de arranque, autoarranque, Chromium/WebKit (F2) | Interfaz |
| DISPLAY, GRAPHICS, OPTIMIZED, CONNECT, DOWNLOADS, EMULATION, DESKTOP (F4+) | Fases posteriores |

Ninguna de estas piezas se borra ni se pierde: siguen en rc23 y en `04_BACKUPS` hasta su fase.

## 3. Cambios respecto a rc23 (justificados)

| Cambio | Justificación |
| --- | --- |
| `GOVERNOR_VERSION` fijado a `v0.4.14-1.20260619120402457887.update.deps.3.g14080b4` | Es la versión de todas las mediciones de placa (H-02). Sigue publicada en el COPR `filippor/bazzite`, build 11067195, chroot `fedora-44-x86_64`, comprobado el 2026-11-06. No se adopta v0.4.15 (R-03) |
| El RPM exacto del regulador se guarda como artefacto del build, con SHA-256 | El COPR puede retirar versiones antiguas (R-03) |
| Prueba de contrato del regulador en el build: los métodos y propiedades D-Bus que STONE usa existen en el paquete instalado | R-03, P-02 |
| `stone-release` añade `STONE_REFERENCE_CPU_CORES=8` y `STONE_REFERENCE_GPU_CU=40` | Configuración de referencia D-16. **No son límites:** sirven para comparar con lo detectado |
| Firma obligatoria, sin clave (keyless, Sigstore) desde D-26; antes exigía `SIGNING_SECRET` | R-09, D-26 |
| Nombre de imagen y canal **distintos** de los de rc23 (ver §6, decisión F0-A) | Para que la consola no se actualice sola a una imagen sin `stoned` ni Home |
| Rutas según R-10; comentarios y código en inglés | D-07 |

No se cambia ninguna frecuencia, voltaje ni umbral (D-18). `governor-config.py` sigue tocando sólo `[dbus] enabled = true`.

## 4. Tareas

| # | Tarea | Resultado verificable |
| --- | --- | --- |
| 1 | Esqueleto del repositorio (R-10) y `VERSION` | Árbol creado; `validate.sh` pasa en vacío |
| 2 | Contenedor de desarrollo Fedora 44 (`dev/Containerfile`) | `dev/run-tests.sh` corre en el Mac con podman o docker |
| 3 | Portar `Containerfile`, `build.sh` (versión F0), `check-kernel.sh`, `governor-config.py`, `config/`, `disk_config/` | Build local o en CI sin errores; `bootc container lint` OK |
| 4 | Fijar el regulador + archivar el RPM + prueba de contrato D-Bus | `stone-release` muestra v0.4.14; el build falla si cambia |
| 5 | Portar 40 CU (`cu40/`, `stone-cu40`, guardia) | `STONE_CU40=ok` en `stone-release`; `test_cu40.py` y `test_cu40_patch.py` pasan |
| 6 | Portar Plymouth y bloqueo de reposo | Tema `stone` en el initramfs; cinco targets enmascarados en la imagen |
| 7 | `hardware/bc250.yaml` y matriz de validación | Cada valor con `source` y `state` (`documented`, `observed`, `owner-confirmed`, `verified`) |
| 8 | Workflows (CI, imagen con firma, ISO) | Ejecución verde en GitHub; imagen firmada en GHCR; ISO con SHA-256 |
| 9 | Documentación F0 (es): construir, instalar la imagen de validación, volver atrás | Documentos revisados |

## 5. Puertas de F0

**Software (ahora):**
- `validate.sh` (shellcheck, ruff, TOML, unidades, sin interruptores de prueba).
- Pruebas de 40 CU y de `governor-config.py`.
- Build de la imagen.
- `bootc container lint`.
- Prueba de contrato del regulador.
- ISO.
- Firma.
- `stone-release` coherente con `build-metadata.json`.

**Placa (diferida, D-19).** Se ejecuta en la primera sesión con la consola encendida, junto con F1 (ver §6, F0-B):

| Prueba | Qué se comprueba |
| --- | --- |
| Diagnóstico de solo lectura | Procedimiento aprobado (D-14) |
| §0 | Inventario |
| §1 | Arranque ×5 |
| §2 | Reposo en Home sin actividad (IDLE) |
| §14 | No se suspende |
| §16 | Instalación |
| §21 / §22 | Actualización / rollback |
| §25 | Estado de 40 CU, sólo lectura de `stone-cu40 status` |
| Comprobación física | 8 núcleos y 40 CU (D-16) |

## 6. Decisiones que necesita F0 (propuestas)

| ID | Pregunta | Propuesta |
| --- | --- | --- |
| F0-A | ¿Con qué nombre de imagen y canal se publica? La consola sigue hoy `ghcr.io/irl1997/stone-os:rc`, y publicar F0 con ese nombre podría actualizarla a una imagen sin `stoned` ni Home | `ghcr.io/irl1997/stone-os-rebuild`, canal `dev`. Versión `0.2.0-dev.N`. El nombre definitivo se decide al llegar a paridad con rc23 |
| F0-B | **Seguridad con 40 CU:** sin `stoned` no hay techo de STONE; el regulador queda en su rango de fábrica con 40 CU. Ese rango sólo se probó con una calibración rápida en rc15, sin validar | La imagen F0 **no se instala en la placa para uso diario**. La primera imagen que se instale será **F1**, con `stoned`, y se validará junto con la puerta de F0. Hasta entonces, la consola sigue en su imagen actual |
| F0-C | ~~Firma obligatoria con clave cosign y secreto `SIGNING_SECRET`~~ **Sustituida por D-26: firma sin clave** | La crea el propietario siguiendo una guía en español; la clave privada nunca entra en el repositorio |
| F0-D | ¿CI con GitHub Actions en `irl1997/STONE-OS-REBUILD`? | Sí, mismo modelo que rc23 (acciones fijadas por SHA) |

## 7. Riesgos de F0

| Riesgo | Mitigación |
| --- | --- |
| El COPR retira v0.4.14 | Se archiva el RPM en la tarea 4 |
| El kernel de Bazzite cambia y el parche de 40 CU no aplica | El build marca `STONE_CU40=unavailable`; **para F0 eso es un fallo de la puerta**, porque 40 CU es la configuración de referencia (D-16). En rc23 sólo era un aviso |
| La base Bazzite cambia | Digest fijado; actualización deliberada con CI |
| Actualizar la consola por error a una imagen F0 | F0-A y F0-B |

## 8. Estado de implementación (actualizado 2026-11-07)

| # | Tarea | Estado | Verificado |
| --- | --- | --- | --- |
| 1 | Esqueleto del repositorio y `VERSION` (0.2.0-dev.1) | Hecho | `validate.sh` en el Mac: PASS (5 comprobaciones omitidas por herramientas ausentes) |
| 2 | Contenedor de desarrollo (`dev/Containerfile`, `dev/run-tests.sh`) | Hecho | **No ejecutado:** no hay podman ni docker en el Mac. Se ejecutará en CI |
| 3 | `Containerfile`, `build.sh` F0, `check-kernel.sh`, `governor-config.py`, `config/`, `disk_config/` | Hecho | Sintaxis (`bash -n`); **build no ejecutado** (necesita Linux/CI) |
| 4 | Regulador v0.4.14 fijado + RPM archivado en CI + registro de contrato | Hecho | Disponibilidad comprobada en el COPR (build 11067195). Base fijada comprobada en GHCR (HTTP 200). **Contrato en vivo: sólo en placa** |
| 5 | 40 CU (obligatorio), Plymouth, bloqueo de reposo | Hecho | `test_cu40.py` 14/14 y `test_cu40_patch.py` PASS en el Mac |
| 6 | `hardware/bc250.yaml` y `hardware/validation/matrix.yaml` | Hecho | Comprobados con el analizador YAML de Ruby (Psych) y las reglas de `test_hardware_profile.py`: 6/6. Encontró y se corrigieron dos errores de sintaxis |
| 7 | Workflows (CI, imagen firmada, ISO, release en borrador) | Hecho | **CI ejecutado en GitHub: verde** en el Pull Request #1 (commit 344bacf, 37 s). La primera ejecución (40eec30) falló en Ruff por la caché en `/src` de solo lectura; corregido con `RUFF_CACHE_DIR`. `Build image` sin ejecutar: falta fusionar en `main` (la firma ya no necesita secreto, D-26) |
| 8 | Pruebas | Hecho | En el Mac: `test_build_config`, `test_release_info` y 40 CU PASS; `test_governor_config` omitida (necesita Python 3.11) |
| 9 | Documentación (es): `CONSTRUIR.md`, `FIRMA.md`, `NOTAS_DE_VERSION.md`, `README.md` | Hecho | — |

Puerta de software: **CI en verde** (2026-11-07). Pendiente: fusionar en `main` y el primer `Build image` (firma sin clave, D-26). Puerta de placa: diferida (D-19).
