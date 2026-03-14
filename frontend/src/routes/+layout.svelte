<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head>
	<title>Prompt Battle</title>
</svelte:head>

<div class="min-h-screen bg-bg-dark">
	{@render children()}
</div>
