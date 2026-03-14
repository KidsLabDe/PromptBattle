<script lang="ts">
	import { uiState } from '$lib/stores/gameStore';

	let { onsubmit }: { onsubmit: (prompt: string) => void } = $props();

	let prompt = $state('');
	let disabled = $derived($uiState !== 'playing');

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (prompt.trim() && !disabled) {
			onsubmit(prompt.trim());
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}
</script>

<form onsubmit={handleSubmit} class="w-full">
	<div class="relative">
		<textarea
			bind:value={prompt}
			{disabled}
			onkeydown={handleKeydown}
			placeholder="Beschreibe das Zielbild..."
			rows="3"
			class="w-full rounded-xl border-2 border-neon-blue/30 bg-bg-card p-4 text-lg text-white
				placeholder-gray-500 transition-all duration-200
				focus:border-neon-blue focus:outline-none focus:ring-2 focus:ring-neon-blue/20
				disabled:opacity-50"
		></textarea>
		<button
			type="submit"
			{disabled}
			class="mt-3 w-full cursor-pointer rounded-xl bg-neon-blue px-6 py-3 text-lg font-bold
				text-black transition-all duration-200
				hover:bg-neon-blue/80 hover:shadow-lg hover:shadow-neon-blue/30
				disabled:cursor-not-allowed disabled:opacity-50"
		>
			Generieren
		</button>
	</div>
</form>
