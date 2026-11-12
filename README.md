# STONE-OS-REBUILD

Reconstrucción integral de STONE OS para **STONE MACHINE**: AMD BC-250 con 8 núcleos de CPU y 40 CU de GPU.

**Estado:** 3.1.0-rc3. STONE Home con el diseño Cristal; Steam funciona oculto y se muestra solo para iniciar sesión, pagar o cuando pregunta algo. Instalar comprueba lo que Steam hizo, y las actualizaciones se buscan cada día y a pedido. Probado en software (CODE TESTED); nada de 3.0 ni de 3.1 está observado todavía en la placa.

| Documento | Contenido |
| --- | --- |
| [docs/ARQUITECTURA_STONE_MACHINE.md](docs/ARQUITECTURA_STONE_MACHINE.md) | Arquitectura integral: módulos, interfaces y fases F0–F9 |
| [docs/DECISIONES_TECNICAS.md](docs/DECISIONES_TECNICAS.md) | Decisiones confirmadas, recomendaciones aprobadas y datos pendientes |
| [docs/fases/F0_PLAN.md](docs/fases/F0_PLAN.md) · [F1_PLAN.md](docs/fases/F1_PLAN.md) | Planes de F0 y F1 |
| [docs/NOTAS_DE_VERSION.md](docs/NOTAS_DE_VERSION.md) | Qué trae cada versión |
| [docs/AUDITORIA_3_0.md](docs/AUDITORIA_3_0.md) | Auditoría de 3.0: causas de los fallos de rc5, cambios y pruebas |
| [docs/CONSTRUIR.md](docs/CONSTRUIR.md) | Construir y probar |
| [docs/FIRMA.md](docs/FIRMA.md) | Firma de las imágenes (sin clave) y cómo verificarla |
| [docs/diagnostico/](docs/diagnostico/) | Diagnóstico de solo lectura de la BC-250 |
| [hardware/bc250.yaml](hardware/bc250.yaml) | Lo que se sabe de la placa, con su origen y estado |
| [hardware/validation/matrix.yaml](hardware/validation/matrix.yaml) | Matriz de validación en placa |

## Estructura

```
apps/       STONE Home: host (Python) e interfaz (apps/stone-home/ui, generada por dev/home/build_home.py)
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
