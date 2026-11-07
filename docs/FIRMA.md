# Firma de las imágenes

Cada imagen de STONE OS se firma (R-09). Desde D-26 la firma es **sin clave** (keyless): GitHub Actions firma con la identidad del propio flujo `build-image.yml` a través de Sigstore. No hay ninguna clave privada que crear, guardar o perder, ni ningún secreto en el repositorio.

## Qué queda registrado

- La firma se guarda en GHCR junto a la imagen.
- Se anota en el registro público de transparencia de Sigstore (Rekor). Esa entrada muestra el nombre del repositorio (`irl1997/STONE-OS-REBUILD`) y del flujo que firmó. **No** contiene código ni el contenido de la imagen.
- El propio flujo verifica la firma recién hecha antes de terminar.

## Verificar una imagen

Con cosign v3.1.2 (descarga y comprobación de suma en `GUIA_PASO_A_PASO`):

```bash
cosign verify ghcr.io/irl1997/stone-os-rebuild:dev \
  --certificate-identity-regexp '^https://github.com/irl1997/STONE-OS-REBUILD/\.github/workflows/build-image\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Una imagen que no pase esta verificación no se instala.
