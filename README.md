# STONE-OS-REBUILD

Reconstrucción integral de STONE OS para **STONE MACHINE**: AMD BC-250 con 8 núcleos de CPU y 40 CU de GPU.

**Estado:** F0 (imagen base) en construcción. Es una imagen de validación, no para uso diario. Nada está verificado en hardware.

| Documento | Contenido |
| --- | --- |
| [docs/ARQUITECTURA_STONE_MACHINE.md](docs/ARQUITECTURA_STONE_MACHINE.md) | Arquitectura integral: módulos, interfaces y fases F0–F9 |
| [docs/DECISIONES_TECNICAS.md](docs/DECISIONES_TECNICAS.md) | Decisiones confirmadas, recomendaciones aprobadas y datos pendientes |
| [docs/fases/F0_PLAN.md](docs/fases/F0_PLAN.md) | Plan de F0 |
| [docs/CONSTRUIR.md](docs/CONSTRUIR.md) | Construir y probar |
| [docs/FIRMA.md](docs/FIRMA.md) | Firma de las imágenes (sin clave) y cómo verificarla |
| [docs/diagnostico/](docs/diagnostico/) | Diagnóstico de solo lectura de la BC-250 |
| [hardware/bc250.yaml](hardware/bc250.yaml) | Lo que se sabe de la placa, con su origen y estado |
| [hardware/validation/matrix.yaml](hardware/validation/matrix.yaml) | Matriz de validación en placa |

## Estructura

```
image/      Containerfile, build_files/ (build.sh, 40 CU, regulador), config/, disk_config/
system/     archivos que entran en la imagen, con su ruta final
hardware/   perfil de la placa y matriz de validación
tests/      pruebas (pytest o como script)
scripts/    validate.sh, test-all.sh, release-info.sh, build-local.sh, build-iso-local.sh
dev/        contenedor de desarrollo (Fedora 44)
docs/       documentación
```

## Licencia

Apache-2.0 ([LICENSE](LICENSE)). Bazzite, el regulador y el resto de componentes mantienen sus propias licencias. El cambio de 40 CU para `amdgpu` (duggasco/bc250-40cu-unlock) es GPL-2.0, como el kernel.
