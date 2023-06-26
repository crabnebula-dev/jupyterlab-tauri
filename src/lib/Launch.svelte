<script lang="ts">
  import { invoke } from "@tauri-apps/api/tauri";
  import { Circle } from "svelte-loading-spinners";
  import logo from "./assets/jupyterlab-wordmark.svg";

  const areas = ["Setup and Signatures", "Authoring", "Reading"];
  const projects = {
    "Setup and Signatures": ["Quick Start", "Signatures", "Shared Libraries"],
    Authoring: ["Scratchpad"],
    Readings: ["Symbolic Math"],
  };

  let area = "";
  let project = "";

  async function launch() {
    try {
      await invoke("launch", { area, project });
    } catch (e) {
      alert(e);
    }
  }
</script>

<div class="content">
  <div class="logo">
    <img alt="JupyterLab Logo" width="300" src={logo} />
  </div>
  <div class="main">
    <select class="input" bind:value={area}>
      {#each areas as areaName}
        <option value={areaName}>{areaName}</option>
      {/each}
    </select>

    <select class="input" bind:value={project}>
      {#if area}
        {#each projects[area] as projectName}
          <option value={projectName}>{projectName}</option>
        {/each}
      {:else}
        <option value="" disabled>Select an area first</option>
      {/if}
    </select>

    <button on:click={launch} disabled={!(area && project)}>Launch</button>
  </div>
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
    margin: auto;
    min-width: 0;
    min-height: 0;
    width: 100%;
  }

  .logo img {
    max-width: 300px;
    width: 100%;
  }
  .main {
    display: flex;
    flex-direction: column;
    flex: 1;
  }
</style>
