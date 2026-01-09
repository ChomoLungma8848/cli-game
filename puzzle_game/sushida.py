#!/usr/bin/env python3
"""
SUSHIDA - Typing Game
Type the words before the sushi flows away!

Controls:
  Type the displayed word to eat the sushi
  ESC or Ctrl+C: Quit
"""

import curses
import random
import time
import sys
import os

# Word lists (Japanese romaji and English mix)
WORDS_EASY = [
    "sushi", "sake", "miso", "tofu", "ramen", "udon", "soba", "nori",
    "wasabi", "ginger", "rice", "fish", "tuna", "salmon", "shrimp",
    "tako", "ika", "ebi", "kani", "uni", "ikura", "tamago", "natto",
    "mochi", "dango", "matcha", "sencha", "gyoza", "tempura", "katsu",
]

WORDS_MEDIUM = [
    "maguro", "hamachi", "hirame", "kohada", "sawara", "suzuki",
    "teriyaki", "sukiyaki", "yakitori", "okonomiyaki", "takoyaki",
    "edamame", "shiitake", "daikon", "wakame", "kombu", "ponzu",
    "shoyu", "mirin", "dashi", "umami", "kawaii", "sugoi", "arigatou",
    "konnichiwa", "sayounara", "itadakimasu", "gochisousama",
]

WORDS_HARD = [
    "teppanyaki", "shabu-shabu", "chawanmushi", "kaiseki",
    "tamagoyaki", "chirashizushi", "makizushi", "nigirizushi",
    "inarizushi", "temakizushi", "futomaki", "hosomaki",
    "uramaki", "gunkanmaki", "oshizushi", "narezushi",
    "kaiten-zushi", "omakase", "itamae", "shokunin",
]

# Sushi art
SUSHI_ART = [
    "🍣",
    "[=]",
    "<==>",
    "(o)",
]

class Sushi:
    def __init__(self, word, y, speed, screen_width):
        self.word = word
        self.y = y
        self.x = float(screen_width - 1)
        self.speed = speed
        self.typed = ""
        self.active = True
        self.eaten = False

    def update(self, dt):
        self.x -= self.speed * dt
        if self.x < -len(self.word) - 5:
            self.active = False

    def check_input(self, char):
        if not self.active or self.eaten:
            return False

        expected = self.word[len(self.typed)]
        if char == expected:
            self.typed += char
            if self.typed == self.word:
                self.eaten = True
                self.active = False
                return True
        else:
            # Wrong key - reset progress
            self.typed = ""
        return False

    def get_progress(self):
        return len(self.typed)


class Game:
    def __init__(self, width, height, difficulty="normal"):
        self.width = width
        self.height = height
        self.difficulty = difficulty

        # Game settings based on difficulty
        if difficulty == "easy":
            self.words = WORDS_EASY
            self.spawn_interval = 3.0
            self.base_speed = 5.0
            self.time_limit = 60
        elif difficulty == "hard":
            self.words = WORDS_EASY + WORDS_MEDIUM + WORDS_HARD
            self.spawn_interval = 1.5
            self.base_speed = 12.0
            self.time_limit = 90
        else:  # normal
            self.words = WORDS_EASY + WORDS_MEDIUM
            self.spawn_interval = 2.0
            self.base_speed = 8.0
            self.time_limit = 60

        self.sushi_list = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.eaten_count = 0
        self.missed_count = 0
        self.total_chars = 0
        self.correct_chars = 0

        self.time_remaining = self.time_limit
        self.last_spawn = 0
        self.game_over = False
        self.used_rows = set()

    def spawn_sushi(self):
        # Find available row
        available_rows = []
        for y in range(3, self.height - 5):
            if y not in self.used_rows:
                available_rows.append(y)

        if not available_rows:
            return

        y = random.choice(available_rows)
        self.used_rows.add(y)

        word = random.choice(self.words)
        speed = self.base_speed + random.uniform(-2, 2)
        sushi = Sushi(word, y, speed, self.width)
        self.sushi_list.append(sushi)

    def update(self, dt):
        if self.game_over:
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.game_over = True
            return

        # Spawn new sushi
        self.last_spawn += dt
        if self.last_spawn >= self.spawn_interval:
            self.spawn_sushi()
            self.last_spawn = 0

        # Update sushi positions
        for sushi in self.sushi_list:
            old_active = sushi.active
            sushi.update(dt)

            # Check if sushi went off screen (missed)
            if old_active and not sushi.active and not sushi.eaten:
                self.missed_count += 1
                self.combo = 0
                if sushi.y in self.used_rows:
                    self.used_rows.discard(sushi.y)

        # Remove inactive sushi
        self.sushi_list = [s for s in self.sushi_list if s.active or s.eaten]

        # Clean up eaten sushi after a moment
        for sushi in self.sushi_list[:]:
            if sushi.eaten:
                self.sushi_list.remove(sushi)
                if sushi.y in self.used_rows:
                    self.used_rows.discard(sushi.y)

    def handle_input(self, char):
        if self.game_over:
            return

        self.total_chars += 1

        # Try to match input with any active sushi
        # Prioritize sushi that already has progress
        sorted_sushi = sorted(self.sushi_list,
                              key=lambda s: (-s.get_progress(), s.x))

        for sushi in sorted_sushi:
            if sushi.check_input(char):
                if sushi.eaten:
                    # Successfully ate the sushi
                    word_score = len(sushi.word) * 10
                    combo_bonus = self.combo * 5
                    self.score += word_score + combo_bonus
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.eaten_count += 1
                self.correct_chars += 1
                return

        # No match - wrong key
        self.combo = 0


def draw_game(stdscr, game):
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    def safe_addstr(y, x, text, attr=0):
        try:
            if 0 <= y < height and 0 <= x < width:
                available = width - x - 1
                if available > 0:
                    stdscr.addstr(y, x, str(text)[:available], attr)
        except curses.error:
            pass

    # Header
    safe_addstr(0, 0, "=" * (width - 1), curses.color_pair(8))
    title = " SUSHIDA - Typing Game "
    safe_addstr(0, width // 2 - len(title) // 2, title,
                curses.color_pair(3) | curses.A_BOLD)

    # Stats bar
    time_str = f"Time: {int(game.time_remaining):02d}s"
    score_str = f"Score: {game.score}"
    combo_str = f"Combo: {game.combo}x"
    eaten_str = f"Eaten: {game.eaten_count}"

    safe_addstr(1, 2, time_str, curses.color_pair(6) | curses.A_BOLD)
    safe_addstr(1, 20, score_str, curses.color_pair(3) | curses.A_BOLD)
    safe_addstr(1, 40, combo_str, curses.color_pair(5) | curses.A_BOLD)
    safe_addstr(1, 55, eaten_str, curses.color_pair(2) | curses.A_BOLD)

    safe_addstr(2, 0, "-" * (width - 1), curses.color_pair(8))

    # Draw conveyor belt lines
    for y in range(3, height - 4):
        safe_addstr(y, 0, "|", curses.color_pair(8))

    # Draw sushi
    for sushi in game.sushi_list:
        if sushi.eaten:
            continue

        x = int(sushi.x)
        y = sushi.y

        if x < 0:
            x = 0

        # Draw sushi icon
        if x < width - 5:
            safe_addstr(y, x, "[=]", curses.color_pair(5) | curses.A_BOLD)

        # Draw word with progress highlighting
        word_x = x - len(sushi.word) - 2
        if word_x >= 0:
            typed_part = sushi.word[:len(sushi.typed)]
            remaining_part = sushi.word[len(sushi.typed):]

            safe_addstr(y, word_x, typed_part, curses.color_pair(2) | curses.A_BOLD)
            safe_addstr(y, word_x + len(typed_part), remaining_part, curses.color_pair(7))

    # Bottom bar
    safe_addstr(height - 4, 0, "-" * (width - 1), curses.color_pair(8))

    # Current input hint
    hint = "Type the words to eat sushi! | ESC to quit"
    safe_addstr(height - 3, width // 2 - len(hint) // 2, hint, curses.color_pair(8))

    # Accuracy
    if game.total_chars > 0:
        accuracy = (game.correct_chars / game.total_chars) * 100
        acc_str = f"Accuracy: {accuracy:.1f}%"
        safe_addstr(height - 2, 2, acc_str, curses.color_pair(6))

    # Game over overlay
    if game.game_over:
        lines = [
            "    TIME'S UP!    ",
            "",
            f" Final Score: {game.score} ",
            f" Sushi Eaten: {game.eaten_count} ",
            f" Missed: {game.missed_count} ",
            f" Max Combo: {game.max_combo}x ",
            f" Accuracy: {(game.correct_chars / max(1, game.total_chars) * 100):.1f}% ",
            "",
            " Press R to restart ",
            " Press Q to quit ",
        ]

        box_width = max(len(line) for line in lines) + 4
        box_height = len(lines) + 2
        box_x = width // 2 - box_width // 2
        box_y = height // 2 - box_height // 2

        for i in range(box_height):
            safe_addstr(box_y + i, box_x, " " * box_width,
                        curses.color_pair(3) | curses.A_REVERSE)

        for i, line in enumerate(lines):
            lx = width // 2 - len(line) // 2
            safe_addstr(box_y + 1 + i, lx, line,
                        curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)

    stdscr.refresh()


def draw_title(stdscr, width, height):
    stdscr.clear()

    def safe_addstr(y, x, text, attr=0):
        try:
            if 0 <= y < height and 0 <= x < width:
                available = width - x - 1
                if available > 0:
                    stdscr.addstr(y, x, str(text)[:available], attr)
        except curses.error:
            pass

    title = [
        " ___  _   _  ___  _   _ ___ ___   _   ",
        "/ __|| | | |/ __|| | | |_ _|   \\ /_\\  ",
        "\\__ \\| |_| |\\__ \\| |_| || || |) / _ \\ ",
        "|___/ \\___/ |___/ \\___/|___|___/_/ \\_\\",
    ]

    start_y = height // 2 - 8

    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        safe_addstr(start_y + i, max(0, x), line,
                    curses.color_pair((i % 3) + 2) | curses.A_BOLD)

    subtitle = "~ Typing Game ~"
    safe_addstr(start_y + 5, width // 2 - len(subtitle) // 2, subtitle,
                curses.color_pair(3))

    # Instructions
    instructions = [
        "",
        "Type the words before sushi flows away!",
        "",
        "[=] <-- word    Type it fast!",
        "",
        "Select difficulty:",
        "",
        "  [1] Easy   - Slow speed, simple words",
        "  [2] Normal - Balanced challenge",
        "  [3] Hard   - Fast speed, complex words",
        "",
        "Press 1, 2, or 3 to start",
    ]

    for i, line in enumerate(instructions):
        y = height // 2 + i
        x = width // 2 - len(line) // 2
        safe_addstr(y, max(0, x), line, curses.color_pair(7))

    stdscr.refresh()


def init_colors():
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    if curses.COLORS > 8:
        curses.init_pair(8, 8, -1)
    else:
        curses.init_pair(8, curses.COLOR_WHITE, -1)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()

    height, width = stdscr.getmaxyx()

    # Minimum size check
    min_width = 70
    min_height = 20
    if width < min_width or height < min_height:
        stdscr.nodelay(False)
        stdscr.clear()
        try:
            stdscr.addstr(0, 0, f"Terminal too small! Need {min_width}x{min_height}, got {width}x{height}")
            stdscr.addstr(1, 0, "Please resize your terminal and restart.")
        except curses.error:
            pass
        stdscr.refresh()
        stdscr.getch()
        return

    while True:
        # Title screen
        stdscr.nodelay(False)
        draw_title(stdscr, width, height)

        while True:
            key = stdscr.getch()
            if key == ord('1'):
                difficulty = "easy"
                break
            elif key == ord('2'):
                difficulty = "normal"
                break
            elif key == ord('3'):
                difficulty = "hard"
                break
            elif key == 27 or key == ord('q') or key == ord('Q'):
                return

        # Game loop
        stdscr.nodelay(True)
        game = Game(width, height, difficulty)
        last_time = time.time()

        while True:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            game.update(dt)
            draw_game(stdscr, game)

            # Handle input
            try:
                key = stdscr.getch()
                if key != -1:
                    if key == 27:  # ESC
                        return
                    elif game.game_over:
                        if key == ord('r') or key == ord('R'):
                            break  # Restart
                        elif key == ord('q') or key == ord('Q'):
                            return
                    elif 32 <= key <= 126:  # Printable ASCII
                        game.handle_input(chr(key))
            except:
                pass

            time.sleep(0.016)  # ~60 FPS


if __name__ == '__main__':
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Error: This game requires an interactive terminal.")
        sys.exit(1)

    if 'TERM' not in os.environ:
        os.environ['TERM'] = 'xterm-256color'

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except curses.error as e:
        print(f"\nTerminal error: {e}")
        print("Please try a different terminal.")
        sys.exit(1)
    finally:
        print("\nThanks for playing SUSHIDA! Goodbye!\n")
