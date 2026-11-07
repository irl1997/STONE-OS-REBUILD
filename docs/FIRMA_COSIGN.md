# Clave de firma de las imágenes (cosign)

Cada imagen de STONE OS se firma (R-09, F0-C). La clave la crea **el propietario**. La clave privada nunca entra en el repositorio: `.gitignore` excluye `cosign.key`.

## Una sola vez

1. Descarga cosign v3.1.2 (la versión de CI) a una carpeta **fuera** del repositorio y comprueba su suma. El Mac de STONE MACHINE es Apple Silicon y no tiene Homebrew.

   ```bash
   mkdir -p ~/stone-firma && cd ~/stone-firma
   ```

   ```bash
   curl -LO https://github.com/sigstore/cosign/releases/download/v3.1.2/cosign-darwin-arm64
   ```

   ```bash
   curl -LO https://github.com/sigstore/cosign/releases/download/v3.1.2/cosign_checksums.txt
   ```

   ```bash
   grep ' cosign-darwin-arm64$' cosign_checksums.txt | shasum -a 256 -c
   ```

   Debe decir `cosign-darwin-arm64: OK`. Si no, no lo uses.

   ```bash
   chmod +x cosign-darwin-arm64 && mv cosign-darwin-arm64 cosign && ./cosign version
   ```

2. Crea el par de claves en esa carpeta. Cuando pida una contraseña, pulsa Enter para dejarla vacía: el flujo de GitHub firma sin contraseña.

   ```bash
   ./cosign generate-key-pair
   ```

   Se crean `cosign.key` (privada) y `cosign.pub` (pública).
3. En GitHub, ve a `irl1997/STONE-OS-REBUILD` → Settings → Secrets and variables → Actions → New repository secret:
   - Nombre: `SIGNING_SECRET`
   - Valor: el contenido completo de `cosign.key`
4. Copia **solo** `cosign.pub` a la raíz del repositorio y súbela con un commit. Es pública y sirve para verificar.
5. Guarda `cosign.key` en un lugar seguro, fuera del Mac de trabajo (por ejemplo, en un gestor de contraseñas). Si se pierde, se genera un par nuevo y se reemplazan el secreto y `cosign.pub`.

## Verificar una imagen

```bash
~/stone-firma/cosign verify --key cosign.pub ghcr.io/irl1997/stone-os-rebuild:dev
```

Si GitHub responde «Failed to add secret», no se guardó nada: recarga la página y repite el paso 3 escribiendo el nombre a mano.
