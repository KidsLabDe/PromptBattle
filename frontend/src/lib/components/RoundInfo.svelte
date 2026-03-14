<script lang="ts">
	import { currentRound, threshold } from '$lib/stores/gameStore';
</script>

<div class="flex items-center justify-between text-sm">
	<span class="rounded-lg bg-neon-pink/20 px-3 py-1 font-bold text-neon-pink">
		Runde {$currentRound}
	</span>
	<span class="rounded-lg bg-neon-yellow/20 px-3 py-1 font-bold text-neon-yellow">
		Mindestscore: {$threshold}%
	</span>
</div>
