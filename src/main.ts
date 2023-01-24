import "./style.css";
import App from "./App.svelte";

const app = new App({
  target: document.getElementById("app"),
});

export default app;

declare global {
  interface Window {
    __PYTHON_ENV_INSTALL_PATH__: string;
  }
}
