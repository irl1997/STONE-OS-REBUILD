# Clave de firma de las imágenes (cosign)

Cada imagen de STONE OS se firma (R-09, F0-C). La clave la crea **el propietario**. La clave privada nunca entra en el repositorio: `.gitignore` excluye `cosign.key`.

## Una sola vez

1. Instala cosign en el Mac:

   ```bash
   brew install cosign
   ```

2. En una carpeta **fuera** del repositorio, crea el par de claves. Cuando pida una contraseña, pulsa Enter para dejarla vacía: el flujo de GitHub firma sin contraseña.

   ```bash
   cosign generate-key-pair
   ```

   Se crean `cosign.key` (privada) y `cosign.pub` (pública).
3. En GitHub, ve a `irl1997/STONE-OS-REBUILD` → Settings → Secrets and variables → Actions → New repository secret:
   - Nombre: `SIGNING_SECRET`
   - Valor: el contenido completo de `cosign.key`
4. Copia **solo** `cosign.pub` a la raíz del repositorio y súbela con un commit. Es pública y sirve para verificar.
5. Guarda `cosign.key` en un lugar seguro, fuera del Mac de trabajo (por ejemplo, en un gestor de contraseñas). Si se pierde, se genera un par nuevo y se reemplazan el secreto y `cosign.pub`.

## Verificar una imagen

```bash
cosign verify --key cosign.pub ghcr.io/irl1997/stone-os-rebuild:dev
```
