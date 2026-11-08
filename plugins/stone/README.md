# Plugin STONE para Decky Loader

Los controles propios de STONE MACHINE en el menú de acceso rápido de Steam (botón `···`): perfil de rendimiento de la consola y del juego, 40 CU, calibración, salud y Modo seguro.

- `src/index.tsx`: el panel, en español.
- `main.py`: el backend. Corre como root y solo ejecuta `stonectl`, `stone-cu40`, `stone-doctor` y `systemctl reboot`, con valores comprobados.

40 CU nunca cambia solo: cada cambio sale de un diálogo que la persona acepta.

La imagen lo compila en su propia etapa (`image/Containerfile`). Para compilarlo a mano: `npm ci && npm run build`.

Estado: CODE TESTED. Sin verificar en la placa (T-PLUGIN-01).
