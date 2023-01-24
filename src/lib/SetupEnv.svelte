<script lang="ts">
  import { invoke, transformCallback } from "@tauri-apps/api/tauri";
  import { relaunch } from "@tauri-apps/api/process";
  import { Circle } from "svelte-loading-spinners";

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
        console.log(event, payload);
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

<div>
  <div>
    Failed to find a compatible Python environment at the configured path "{installPath}"
    <button class="install" on:click={installAndRestart}>
      {#if installing}
        <Circle size="10" />
      {/if}
      Install and restart
    </button>
  </div>

  <div class="output">
    {#each output as line}
      <div>
        {line}
      </div>
    {/each}
  </div>
</div>

<style>
  button.install {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }
</style>
