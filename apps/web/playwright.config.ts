import { defineConfig } from "@playwright/test";

const fakeMedia = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"];

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3100", trace: "off", launchOptions: { args: fakeMedia } },
  projects: [
    { name: "mobile-390", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 } },
    { name: "narrow-320", use: { viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 } },
  ],
  webServer: [
    { command: "bash e2e/stack.sh", url: "http://localhost:8100/healthz", timeout: 120_000, reuseExistingServer: false },
    {
      command: "npx next start -p 3100",
      url: "http://localhost:3100",
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VV_API_ORIGIN: "http://localhost:8100", VV_ENABLE_DUMMY_PROVIDER: "1" },
    },
  ],
});
