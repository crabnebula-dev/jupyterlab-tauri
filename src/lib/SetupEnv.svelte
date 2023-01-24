<script lang="ts">
  import { invoke } from "@tauri-apps/api/tauri";
  import { Circle } from "svelte-loading-spinners";

  let installPath = window.__PYTHON_ENV_INSTALL_PATH__;
  let installing = false;
  let error = "";

  async function installAndRestart() {
    installing = true;
    error = "";
    try {
      const _cancelled = await invoke("install_and_restart");
    } catch (e) {
      error = e;
    }
    installing = false;
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

  {#if error}
    <div>
      {error}
    </div>
  {/if}
</div>

<style>
  button.install {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }
</style>
