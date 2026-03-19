import path from 'node:path';
import type { Plugin } from 'vite';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

function reloadOnUserDataChanges(): Plugin {
  const userDataPaths = Array.from(
    new Set([
      path.resolve(__dirname, 'user-data'),
      path.resolve(__dirname, '../user-data'),
    ]),
  );

  return {
    name: 'reload-on-user-data-changes',
    configureServer(server) {
      const reloadEvents = new Set(['add', 'change', 'unlink']);
      const normalizePath = (filePath: string) => filePath.split(path.sep).join('/');
      const normalizedUserDataPaths = userDataPaths.map(normalizePath);

      server.watcher.add(
        userDataPaths.flatMap((userDataPath) => [userDataPath, path.join(userDataPath, '**/*')]),
      );

      const triggerReload = (filePath: string) => {
        const normalizedFilePath = normalizePath(filePath);

        const isUserDataFile = normalizedUserDataPaths.some(
          (userDataPath) =>
            normalizedFilePath === userDataPath ||
            normalizedFilePath.startsWith(`${userDataPath}/`),
        );

        if (isUserDataFile) {
          server.ws.send({ type: 'full-reload' });
        }
      };

      for (const eventName of reloadEvents) {
        server.watcher.on(eventName, triggerReload);
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), reloadOnUserDataChanges()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.ts',
  },
});
