<script lang="ts">
	import { timeRemaining, formattedTime } from '$lib/stores/gameStore';

	let remaining = $derived($timeRemaining);
	let formatted = $derived($formattedTime);
	let urgent = $derived(remaining <= 10);
</script>

<div class="text-center">
	<div
		class="text-6xl font-mono font-bold tracking-wider transition-colors duration-300"
		class:text-neon-green={!urgent}
		class:text-red-500={urgent}
		class:animate-pulse-glow={urgent}
	>
		{formatted}
	</div>
</div>
