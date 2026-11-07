# Construir STONE OS (rebuild) — F0

Esta es la imagen base de la reconstrucción. **No es una versión para usar en la consola** (F0-B): no trae `stoned` ni STONE Home. La primera imagen que se instalará en la BC-250 será la de F1.

## Qué contiene F0

| Pieza | Detalle |
| --- | --- |
| Base | Bazzite `bazzite-deck:stable-44`, fijada al digest `sha256:278941ea…bdf4e`: la base de todas las mediciones de rc14–rc23 |
| Regulador de GPU | `cyan-skillfish-governor-smu` **v0.4.14** (COPR `filippor/bazzite`), fijado. Solo se activa su D-Bus; la curva, el rango y los umbrales quedan como los trae el paquete |
| 40 CU | `amdgpu` recompilado para el kernel exacto de la base con la opción `bc250_cc_write_mode`, más `stone-cu40` y la guardia de arranque. **Sin el módulo, el build falla**, porque la configuración de referencia es 8 núcleos y 40 CU |
| Arranque | Tema Plymouth `stone` dentro del initramfs |
| Sin reposo | Los cinco targets de suspensión enmascarados y `sleep.conf.d` |
| Handheld Daemon | Enmascarado |
| Procedencia | `/usr/lib/stone-release`: versión, fase F0, módulos ausentes, base, kernel, Mesa, regulador, 40 CU y configuración de referencia |

## Dónde se construye

Las imágenes bootc se construyen en Linux. Desde el Mac se usa GitHub Actions:

| Flujo | Cuándo | Resultado |
| --- | --- | --- |
| `CI` | Cada push y pull request | `scripts/validate.sh` + todas las pruebas, dentro del contenedor de desarrollo |
| `Build image` | Push a `main` o a mano | `ghcr.io/<usuario>/stone-os-rebuild:dev` y `dev-<sha>`, **firmada**, más los metadatos y el RPM del regulador archivados |
| `Build installer` | A mano | ISO de instalación (partes de menos de 2 GiB + SHA-256) |
| `Release` | Etiqueta `v<VERSION>` | Release en **borrador**: ISO, metadatos y paquete del regulador |

Antes del primer `Build image` hay que crear la clave de firma: [FIRMA_COSIGN.md](FIRMA_COSIGN.md). Sin ella, el flujo se detiene antes de compilar.

## Probar en el Mac

Necesita Podman Desktop o Docker Desktop:

```bash
dev/run-tests.sh
```

Construye un contenedor Fedora 44 con las mismas herramientas que CI y ejecuta dentro `scripts/validate.sh` y `scripts/test-all.sh`. El repositorio se monta en solo lectura.

Sin contenedor, `python3 tests/<archivo>.py` ejecuta cada prueba como script. Las que necesitan Python 3.11 o PyYAML se marcan como omitidas.

## Construir en Linux

```bash
scripts/build-local.sh --owner <usuario-de-github>
```

```bash
scripts/build-iso-local.sh localhost/stone-os-rebuild:0.2.0-dev.1
```

## Lo que F0 no verifica

La puerta de placa de F0 queda diferida (D-19) y se hará junto con F1 en la primera sesión con la consola encendida. Incluye el diagnóstico de solo lectura, las pruebas 0, 1, 2, 14, 16, 21, 22 y 25, y la comprobación física de 8 núcleos y 40 CU. Mientras tanto, todo lo de F0 está como mucho en `CODE TESTED`.
