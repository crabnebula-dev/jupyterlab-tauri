<script lang="ts">
  import { invoke } from "@tauri-apps/api/tauri";
  import { Circle } from "svelte-loading-spinners";
  import logo from "./assets/jupyterlab-wordmark.svg";

  const areas = ["Setup and Signatures", "Authoring", "Readings"];
  const projects = {
    "Setup and Signatures": ["Quick Start", "Signatures", "Shared Libraries"],
    Authoring: ["Scratchpad"],
    Readings: ["Symbolic Math"],
  };

  let area = "";
  let project = "";
  let launching = false;

  async function launch() {
    try {
      launching = true;
      await invoke("launch", { area, project });
    } catch (e) {
      alert(e);
    } finally {
      launching = false;
    }
  }

  $: {
    if (area) {
      project = "";
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

    <button
      class="launch"
      on:click={launch}
      disabled={!(area && project && !launching)}>Launch</button
    >
  </div>

  {#if launching}
    <div class="circle">
      <span>
        <Circle size="20" />
      </span>
    </div>
  {/if}
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

  .circle {
    display: flex;
    margin-bottom: 3rem;
  }

  .circle span {
    display: inline-block;
    margin: 0 auto;
  }
</style>
