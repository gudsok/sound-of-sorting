"""
Sound of Sorting - Sorting Algorithm Visualizer
================================================
Controls:
  [1] Bubble Sort      [2] Selection Sort   [3] Insertion Sort
  [4] Merge Sort       [5] Quick Sort       [6] Heap Sort
  [R] Shuffle Array    [SPACE] Pause/Resume
  [+] Speed Up         [-] Slow Down        [Q] Quit
"""

import pygame
import numpy as np
import random
import sys
import threading
from collections import deque

# ─── Audio ────────────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
SOUND_DURATION = 0.06  # seconds per tone


def make_tone(frequency: float, duration: float = SOUND_DURATION, volume: float = 0.25) -> pygame.mixer.Sound:
    frames = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, frames, endpoint=False)

    # Blend sine + triangle for a warmer timbre
    sine  = np.sin(2 * np.pi * frequency * t)
    tri   = 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
    #wave  = (0.7 * sine + 0.3 * tri) * volume
    wave = np.sign(np.sin(2 * np.pi * frequency * t)) * volume
    lo, hi = np.log(100), np.log(1000)

    # Smooth envelope: short attack, exponential decay
    attack  = int(SAMPLE_RATE * 0.005)
    wave[:attack] *= np.linspace(0, 1, attack)
    decay = int(SAMPLE_RATE * 0.02)
    wave[-decay:] *= np.exp(np.linspace(0, -4, decay))

    stereo = np.ascontiguousarray(np.stack([wave, wave], axis=1))
    return pygame.sndarray.make_sound((stereo * 32767).astype(np.int16))


def value_to_freq(value: int, n: int) -> float:
    """Map bar value (1..n) → frequency (180 Hz – 1800 Hz), log scale."""
    lo, hi = np.log(180), np.log(1800)
    return float(np.exp(lo + (value / n) * (hi - lo)))


# ─── Colour palette ───────────────────────────────────────────────────────────

BG          = (12,  14,  22)
BAR_DEFAULT = (55,  120, 210)
BAR_COMPARE = (255, 200,  50)   # yellow — being compared
BAR_SWAP    = (255,  75,  75)   # red    — being swapped
BAR_SORTED  = ( 60, 220, 120)   # green  — sorted / pivot placed
BAR_PIVOT   = (220,  80, 255)   # purple — pivot
TEXT_MAIN   = (230, 230, 240)
TEXT_DIM    = (110, 120, 140)
ACCENT      = ( 80, 160, 255)


# ─── Visualizer ───────────────────────────────────────────────────────────────

class SortingVisualizer:
    N_DEFAULT = 30
    DELAY_DEFAULT = 128   # ms

    def __init__(self, width: int = 1280, height: int = 720):
        pygame.init()
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
        pygame.mixer.init()
        pygame.display.set_caption("Sound of Sorting")

        self.screen = pygame.display.set_mode((width, height))
        self.W, self.H = width, height
        self.clock = pygame.time.Clock()

        try:
            self.font_sm = pygame.font.SysFont("Consolas,Courier New,monospace", 16)
            self.font_md = pygame.font.SysFont("Consolas,Courier New,monospace", 20)
            self.font_lg = pygame.font.SysFont("Consolas,Courier New,monospace", 28, bold=True)
        except Exception:
            self.font_sm = pygame.font.SysFont(None, 18)
            self.font_md = pygame.font.SysFont(None, 22)
            self.font_lg = pygame.font.SysFont(None, 30)

        self.n     = self.N_DEFAULT
        self.delay = self.DELAY_DEFAULT
        self.arr:  list[int] = []
        self.highlights: dict[int, tuple] = {}   # index → colour
        self.comparisons = 0
        self.swaps       = 0
        self.algo_name   = "—"
        self.sorting     = False
        self.paused      = False
        self.done        = False
        self._stop       = False

        # Sound cache: reuse tones to avoid GC pressure
        self._tone_cache: dict[int, pygame.mixer.Sound] = {}

        self.shuffle()

    # ── Array helpers ──────────────────────────────────────────────────────────

    def shuffle(self):
        self._stop = True                    # signal any running sort to stop
        pygame.time.wait(80)
        self.arr = list(range(1, self.n + 1))
        random.shuffle(self.arr)
        self.highlights  = {}
        self.comparisons = 0
        self.swaps       = 0
        self.sorting     = False
        self.paused      = False
        self.done        = False
        self._stop       = False
        self.algo_name   = "—"
        self._tone_cache.clear()

    def _play(self, value: int):
        if value not in self._tone_cache:
            self._tone_cache[value] = make_tone(value_to_freq(value, self.n))
        try:
            self._tone_cache[value].play()
        except Exception:
            pass

    # ── Sorting step helpers (call inside generator) ───────────────────────────

    def _wait(self):
        """Busy-wait while paused; return True if stop was requested."""
        while self.paused and not self._stop:
            pygame.time.wait(30)
        return self._stop

    def _step(self, compare_idx=(), swap_idx=(), pivot_idx=(), sorted_idx=()):
        """Highlight bars, play sound, wait delay; returns True if aborted."""
        if self._stop:
            return True

        self.highlights = {}
        for i in compare_idx: self.highlights[i] = BAR_COMPARE
        for i in swap_idx:    self.highlights[i] = BAR_SWAP
        for i in pivot_idx:   self.highlights[i] = BAR_PIVOT
        for i in sorted_idx:  self.highlights[i] = BAR_SORTED

        # play the sound of whatever is being touched
        touched = list(compare_idx) + list(swap_idx) + list(pivot_idx)
        if touched:
            self._play(self.arr[touched[0]])

        pygame.time.wait(self.delay)
        return self._wait()

    # ── Sorting algorithms (generators that yield per step) ───────────────────

    def _bubble_sort(self):
        a = self.arr
        for i in range(len(a)):
            for j in range(len(a) - i - 1):
                self.comparisons += 1
                if self._step(compare_idx=(j, j + 1)): return
                if a[j] > a[j + 1]:
                    a[j], a[j + 1] = a[j + 1], a[j]
                    self.swaps += 1
                    if self._step(swap_idx=(j, j + 1)): return
            if self._step(sorted_idx=(len(a) - i - 1,)): return
        self.highlights = {i: BAR_SORTED for i in range(len(a))}

    def _selection_sort(self):
        a = self.arr
        for i in range(len(a)):
            min_i = i
            for j in range(i + 1, len(a)):
                self.comparisons += 1
                if self._step(compare_idx=(min_i, j), sorted_idx=range(i)): return
                if a[j] < a[min_i]:
                    min_i = j
            if min_i != i:
                a[i], a[min_i] = a[min_i], a[i]
                self.swaps += 1
                if self._step(swap_idx=(i, min_i)): return
        self.highlights = {i: BAR_SORTED for i in range(len(a))}

    def _insertion_sort(self):
        a = self.arr
        for i in range(1, len(a)):
            key = a[i]
            j = i - 1
            while j >= 0 and a[j] > key:
                self.comparisons += 1
                a[j + 1] = a[j]
                self.swaps += 1
                if self._step(swap_idx=(j, j + 1)): return
                j -= 1
            a[j + 1] = key
            if self._step(sorted_idx=(j + 1,)): return
        self.highlights = {i: BAR_SORTED for i in range(len(a))}

    def _merge_sort(self):
        a = self.arr

        def merge(lo, mid, hi):
            left  = a[lo:mid + 1]
            right = a[mid + 1:hi + 1]
            li = ri = 0
            for k in range(lo, hi + 1):
                self.comparisons += 1
                if li < len(left) and (ri >= len(right) or left[li] <= right[ri]):
                    a[k] = left[li]; li += 1
                else:
                    a[k] = right[ri]; ri += 1
                self.swaps += 1
                if self._step(swap_idx=(k,)): return True
            return False

        def sort(lo, hi):
            if lo >= hi: return False
            mid = (lo + hi) // 2
            if sort(lo, mid):     return True
            if sort(mid + 1, hi): return True
            return merge(lo, mid, hi)

        sort(0, len(a) - 1)
        if not self._stop:
            self.highlights = {i: BAR_SORTED for i in range(len(a))}

    def _quick_sort(self):
        a = self.arr

        def partition(lo, hi):
            pivot = a[hi]
            i = lo - 1
            for j in range(lo, hi):
                self.comparisons += 1
                if self._step(compare_idx=(j,), pivot_idx=(hi,)): return None
                if a[j] <= pivot:
                    i += 1
                    a[i], a[j] = a[j], a[i]
                    self.swaps += 1
                    if self._step(swap_idx=(i, j), pivot_idx=(hi,)): return None
            a[i + 1], a[hi] = a[hi], a[i + 1]
            self.swaps += 1
            if self._step(sorted_idx=(i + 1,)): return None
            return i + 1

        stack = deque([(0, len(a) - 1)])
        while stack:
            lo, hi = stack.pop()
            if lo >= hi: continue
            p = partition(lo, hi)
            if p is None: return
            stack.append((lo, p - 1))
            stack.append((p + 1, hi))

        if not self._stop:
            self.highlights = {i: BAR_SORTED for i in range(len(a))}

    def _heap_sort(self):
        a  = self.arr
        n  = len(a)

        def heapify(size, root):
            largest = root
            l, r = 2 * root + 1, 2 * root + 2
            if l < size:
                self.comparisons += 1
                if self._step(compare_idx=(l, largest)): return True
                if a[l] > a[largest]: largest = l
            if r < size:
                self.comparisons += 1
                if self._step(compare_idx=(r, largest)): return True
                if a[r] > a[largest]: largest = r
            if largest != root:
                a[root], a[largest] = a[largest], a[root]
                self.swaps += 1
                if self._step(swap_idx=(root, largest)): return True
                return heapify(size, largest)
            return False

        for i in range(n // 2 - 1, -1, -1):
            if heapify(n, i): return

        for i in range(n - 1, 0, -1):
            a[0], a[i] = a[i], a[0]
            self.swaps += 1
            if self._step(swap_idx=(0, i), sorted_idx=(i,)): return
            if heapify(i, 0): return

        if not self._stop:
            self.highlights = {i: BAR_SORTED for i in range(len(a))}

    # ── Completion sweep ──────────────────────────────────────────────────────

    def _completion_sweep(self):
        """Left-to-right green sweep with ascending tones after sorting."""
        n = len(self.arr)
        sweep_delay = max(4, min(12, 600 // n))   # faster for large arrays

        for i in range(n):
            if self._stop:
                return
            self.highlights[i] = BAR_SORTED
            self._play(self.arr[i])
            pygame.time.wait(sweep_delay)

        # Final chord: play low, mid, high together
        pygame.time.wait(80)
        for v in (1, n // 2, n):
            self._play(v)
            pygame.time.wait(30)

    # ── Runner ─────────────────────────────────────────────────────────────────

    ALGORITHMS = {
        "1": ("Bubble Sort",     "_bubble_sort"),
        "2": ("Selection Sort",  "_selection_sort"),
        "3": ("Insertion Sort",  "_insertion_sort"),
        "4": ("Merge Sort",      "_merge_sort"),
        "5": ("Quick Sort",      "_quick_sort"),
        "6": ("Heap Sort",       "_heap_sort"),
    }

    def _run_sort(self, key: str):
        name, method = self.ALGORITHMS[key]
        self.shuffle()
        pygame.time.wait(200)
        self.algo_name = name
        self.sorting   = True
        self.done      = False
        getattr(self, method)()
        if not self._stop:
            self.highlights = {}          # reset highlights before sweep
            self._completion_sweep()
        self.sorting = False
        self.done    = not self._stop

    def start_sort(self, key: str):
        self._stop = True
        pygame.time.wait(60)
        t = threading.Thread(target=self._run_sort, args=(key,), daemon=True)
        t.start()

    # ── Drawing ────────────────────────────────────────────────────────────────

    def _bar_color(self, idx: int) -> tuple:
        if idx in self.highlights:
            return self.highlights[idx]
        if self.done:
            return BAR_SORTED
        return BAR_DEFAULT

    def draw(self):
        self.screen.fill(BG)
        W, H = self.W, self.H

        # ── Bars ──────────────────────────────────────────────────────────────
        chart_top  = 70
        chart_h    = H - 130
        bar_w_f    = W / self.n

        for i, v in enumerate(self.arr):
            bh    = int((v / self.n) * chart_h)
            x     = int(i * bar_w_f)
            bw    = max(int(bar_w_f) - 1, 1)
            y     = chart_top + chart_h - bh
            color = self._bar_color(i)

            # Main bar
            pygame.draw.rect(self.screen, color, (x, y, bw, bh))

            # Bright top edge highlight
            r, g, b = color
            hi = (min(r + 80, 255), min(g + 80, 255), min(b + 80, 255))
            pygame.draw.rect(self.screen, hi, (x, y, bw, 2))

        # ── Header ────────────────────────────────────────────────────────────
        title_surf = self.font_lg.render(
            f"▶ {self.algo_name}" if self.sorting else
            f"✓ {self.algo_name} — done!" if self.done else
            f"Sound of Sorting",
            True,
            ACCENT if self.sorting else BAR_SORTED if self.done else TEXT_MAIN,
        )
        self.screen.blit(title_surf, (20, 16))

        # ── Stats ─────────────────────────────────────────────────────────────
        stats = (
            f"N={self.n}   "
            f"CMP={self.comparisons:,}   "
            f"SWP={self.swaps:,}   "
            f"delay={self.delay}ms"
        )
        paused_tag = "  [PAUSED]" if self.paused else ""
        stats_surf = self.font_md.render(stats + paused_tag, True,
                                         (255, 220, 60) if self.paused else TEXT_DIM)
        self.screen.blit(stats_surf, (W - stats_surf.get_width() - 16, 18))

        # ── Colour legend ─────────────────────────────────────────────────────
        legend = [
            (BAR_DEFAULT, "default"),
            (BAR_COMPARE, "compare"),
            (BAR_SWAP,    "swap"),
            (BAR_SORTED,  "sorted"),
            (BAR_PIVOT,   "pivot"),
        ]
        lx = 20
        ly = H - 55
        for col, label in legend:
            pygame.draw.rect(self.screen, col, (lx, ly + 2, 12, 12))
            lbl = self.font_sm.render(label, True, TEXT_DIM)
            self.screen.blit(lbl, (lx + 16, ly))
            lx += lbl.get_width() + 32

        # ── Key guide ─────────────────────────────────────────────────────────
        guide = "[1] Bubble  [2] Selection  [3] Insertion  [4] Merge  [5] Quick  [6] Heap  " \
                "[R] Shuffle  [SPACE] Pause  [+/-] Speed  [Q] Quit"
        guide_surf = self.font_sm.render(guide, True, TEXT_DIM)
        self.screen.blit(guide_surf, (20, H - 28))

        pygame.display.flip()

    # ── Main loop ─────────────────────────────────────────────────────────────

    KEY_MAP = {
        pygame.K_1: "1", pygame.K_2: "2", pygame.K_3: "3",
        pygame.K_4: "4", pygame.K_5: "5", pygame.K_6: "6",
    }

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN:
                    k = event.key

                    if k == pygame.K_q or k == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()

                    elif k in self.KEY_MAP:
                        self.start_sort(self.KEY_MAP[k])

                    elif k == pygame.K_r:
                        self._stop = True
                        pygame.time.wait(80)
                        self.shuffle()

                    elif k == pygame.K_SPACE:
                        if self.sorting:
                            self.paused = not self.paused

                    elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.delay = max(1, self.delay - 5)

                    elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.delay = min(500, self.delay + 10)

            self.draw()
            self.clock.tick(60)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    vis = SortingVisualizer()
    vis.run()