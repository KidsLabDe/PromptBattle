import { writable, derived } from 'svelte/store';

export type UIState = 'title' | 'playing' | 'generating' | 'result' | 'gameover';

export interface RoundResult {
	round: number;
	prompt: string;
	score: number;
	threshold: number;
	passed: boolean;
	generated_image: string;
	target_image: string;
}

export const uiState = writable<UIState>('title');
export const gameId = writable<string>('');
export const currentRound = writable<number>(1);
export const threshold = writable<number>(25);
export const timeRemaining = writable<number>(60);
export const targetImage = writable<string>('');
export const generatedImage = writable<string>('');
export const generationStep = writable<number>(0);
export const generationTotal = writable<number>(4);
export const currentScore = writable<number>(0);
export const currentPassed = writable<boolean>(false);
export const history = writable<RoundResult[]>([]);

export const formattedTime = derived(timeRemaining, ($t) => {
	const m = Math.floor($t / 60);
	const s = $t % 60;
	return `${m}:${s.toString().padStart(2, '0')}`;
});

export function resetGame() {
	uiState.set('title');
	gameId.set('');
	currentRound.set(1);
	threshold.set(25);
	timeRemaining.set(60);
	targetImage.set('');
	generatedImage.set('');
	generationStep.set(0);
	currentScore.set(0);
	currentPassed.set(false);
	history.set([]);
}
