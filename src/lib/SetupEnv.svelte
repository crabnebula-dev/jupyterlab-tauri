<script lang="ts">
  import { invoke, transformCallback } from "@tauri-apps/api/tauri";
  import { relaunch } from "@tauri-apps/api/process";
  import { Circle } from "svelte-loading-spinners";
  import logo from "./assets/jupyterlab-wordmark.svg";
  import pythonLogo from "./assets/python.svg";

  let installPath = window.__PYTHON_ENV_INSTALL_PATH__;
  let installing = false;
  let output = [];

  type Event =
    | { event: "Stdout" | "Stderr" | "Error"; payload: string }
    | { event: "Exit"; payload: number };

  async function installAndRestart() {
    installing = true;
    output = [];
    try {
      const cb = transformCallback((message: Event) => {
        const { event, payload } = message;
        switch (event) {
          case "Stdout":
            output = [...output, payload];
            break;
          case "Stderr":
            if (payload.endsWith("\r")) {
              if (output.length) {
                output[output.length - 1] = payload;
              } else {
                output = [...output, payload];
              }
            }
            break;
          case "Error":
            output = [...output, payload];
            installing = false;
            break;
          case "Exit":
            installing = false;
            if (payload) {
              output = [
                ...output,
                `Installation failed with exit code ${payload}`,
              ];
            } else {
              relaunch();
            }
            break;
        }
      });
      await invoke("run_installer", { onEventFn: cb });
    } catch (e) {
      output = [...output, e];
    }
  }
</script>

<div class="content">
  <div class="logo">
    <img alt="JupyterLab Logo" width="300" src={logo} />
  </div>
  <div class="main">
    <h1>Getting started</h1>
    <p>
      Failed to find a compatible Python environment at the configured path:
    </p>
    <p>"<i>{installPath}</i>"</p>
    <p><strong>Please try to intall it</strong></p>
    <button disabled={installing} class="install" on:click={installAndRestart}>
      <img alt="Python Logo" width="30" src={pythonLogo} />
      Install and restart
    </button>
    {#if output.length > 0}
      <h2>Console Output:</h2>
      <div class="output">
        {#each output as line}
          <p><i>{line}</i></p>
        {/each}
      </div>
    {/if}
  </div>

  <dialog open={installing}>
    <h1>Installing Python Environment...</h1>
    <div class="circle">
      <span>
        <Circle size="40" />
      </span>
    </div>
    <p>
      <i
        >Do not close this window, the application will restart after a
        successfull install. This may take a couple of minutes.</i
      >
    </p>
    {#if output.length > 0}
      <h2>Console Output:</h2>
      <div class="output">
        {#each output as line}
          <p><i>{line}</i></p>
        {/each}
      </div>
    {/if}
  </dialog>
</div>

<style>
  :root {
    display: flex;
    align-items: center;
    justify-content: center;
    vertical-align: middle;
    flex-direction: column;
    height: 100vh;
  }
  .content {
    display: flex;
    flex-direction: column;
    align-items: left;
    gap: 2rem;
    padding: 2rem;
    position: relative;
    max-width: 620px;
    margin: 0 auto;
  }
  .main {
    display: flex;
    flex-direction: column;
    flex: 1;
  }
  .main h1 {
    margin-bottom: 1rem;
    margin-top: 0;
  }
  button.install img {
    filter: invert(0.8);
  }
  button.install {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 1rem;

    border: none;
    color: white;
    cursor: pointer;
    background-color: transparent;
    font-size: 18px;
    padding: 0.5rem;
    margin-bottom: 2rem;
  }
  button:disabled {
    filter: blur(1px);
  }

  button.install:hover {
    background-color: #424242;
    box-shadow: 1px 6px 21px #424242;
    border-radius: 3px;
  }

  dialog {
    top: 50%;
    left: 50%;
    -webkit-transform: translateX(-50%) translateY(-50%);
    -moz-transform: translateX(-50%) translateY(-50%);
    -ms-transform: translateX(-50%) translateY(-50%);
    transform: translateX(-50%) translateY(-50%);
    padding: 4rem 4rem;
    width: 75%;
    background-color: #424242;
    box-shadow: 0 0 79px #424242;
    color: white;
    border: none;
    border-radius: 8px;
  }
  dialog h1 {
    margin-bottom: 3rem;
    text-align: center;
    line-height: 1;
  }

  .circle {
    display: flex;
    margin-bottom: 3rem;
  }

  .circle span {
    display: inline-block;
    margin: 0 auto;
  }

  dialog::backdrop {
    background-color: black;
  }

  .output {
    border: 2px solid #424242;
    border-radius: 8px;
    padding: 1rem;
    overflow: auto;
    height: 200px;
    word-break: break-all;
    word-wrap: break-word;
  }

  dialog .output {
    border-color: white;
  }

  .output h2 {
    margin-top: 0.5rem;
  }
  .output p {
    font-size: 18px;
  }
</style>
