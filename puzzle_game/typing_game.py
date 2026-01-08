#!/usr/bin/env python3
"""
TYPING GAME - Type falling words before they reach the bottom!

Controls:
  Type the words : Destroy them!
  Escape         : Clear current input
  Q (when idle)  : Quit
"""

import curses
import random
import time

# Word lists by difficulty
WORDS_EASY = [
    "cat", "dog", "sun", "run", "fun", "hat", "bat", "rat", "map", "cup",
    "pen", "red", "box", "fox", "ice", "hot", "big", "top", "win", "fly",
]

WORDS_MEDIUM = [
    "python", "coding", "typing", "screen", "cursor", "string", "number",
    "planet", "rocket", "galaxy", "forest", "stream", "bridge", "castle",
    "knight", "dragon", "wizard", "scroll", "potion", "shield", "silver",
]

WORDS_HARD = [
    "algorithm", "beautiful", "challenge", "dangerous", "excellent",
    "fantastic", "generated", "happiness", "important", "javascript",
    "knowledge", "legendary", "mysterious", "nightmare", "operating",
    "programmer", "quantum", "responsive", "synthesis", "typescript",
]

ALL_WORDS = WORDS_EASY + WORDS_MEDIUM + WORDS_HARD


class Word:
    def __init__(self, text, x, y, speed):
        self.text = text
        self.x = x
        self.y = y
        self.speed = speed
        self.active = True
        self.matched_chars = 0


class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.words = []
        self.score = 0
        self.lives = 5
        self.level = 1
        self.words_typed = 0
        self.game_over = False
        self.paused = False

        self.current_input = ""
        self.spawn_timer = 0
        self.spawn_delay = 2.0

        self.combo = 0
        self.max_combo = 0

    def get_spawn_delay(self):
        """Get spawn delay based on level."""
        return max(0.5, 2.0 - (self.level - 1) * 0.15)

    def get_word_speed(self):
        """Get word fall speed based on level."""
        return 0.3 + (self.level - 1) * 0.05

    def spawn_word(self):
        """Spawn a new word at the top."""
        # Choose word based on level
        if self.level <= 3:
            word_list = WORDS_EASY
        elif self.level <= 6:
            word_list = WORDS_EASY + WORDS_MEDIUM
        else:
            word_list = ALL_WORDS

        text = random.choice(word_list)

        # Avoid duplicate active words
        active_texts = [w.text for w in self.words if w.active]
        attempts = 0
        while text in active_texts and attempts < 10:
            text = random.choice(word_list)
            attempts += 1

        x = random.randint(2, self.width - len(text) - 2)
        y = 2
        speed = self.get_word_speed() + random.uniform(-0.1, 0.1)

        self.words.append(Word(text, x, y, speed))

    def update(self, dt):
        """Update game state."""
        if self.paused or self.game_over:
            return

        # Spawn new words
        self.spawn_timer += dt
        if self.spawn_timer >= self.get_spawn_delay():
            self.spawn_word()
            self.spawn_timer = 0

        # Update words
        for word in self.words:
            if not word.active:
                continue

            word.y += word.speed * dt

            # Word reached bottom
            if word.y >= self.height - 4:
                word.active = False
                self.lives -= 1
                self.combo = 0

                if self.lives <= 0:
                    self.game_over = True

        # Clean up inactive words
        self.words = [w for w in self.words if w.active]

    def type_char(self, char):
        """Handle typed character."""
        if self.game_over:
            return

        self.current_input += char

        # Check for matching words
        matched_word = None
        for word in self.words:
            if word.active and word.text == self.current_input:
                matched_word = word
                break

        if matched_word:
            matched_word.active = False
            self.words_typed += 1
            self.combo += 1

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Score based on word length and combo
            base_score = len(matched_word.text) * 10
            combo_bonus = self.combo * 5
            self.score += base_score + combo_bonus

            # Level up every 10 words
            self.level = self.words_typed // 10 + 1

            self.current_input = ""

        # Update matched characters display
        for word in self.words:
            if word.active and word.text.startswith(self.current_input):
                word.matched_chars = len(self.current_input)
            else:
                word.matched_chars = 0

    def clear_input(self):
        """Clear current input."""
        self.current_input = ""
        for word in self.words:
            word.matched_chars = 0


def draw_game(stdscr, game):
    """Draw the game."""
    stdscr.clear()

    # Draw header
    header = f" Score: {game.score}  |  Level: {game.level}  |  Combo: {game.combo}x  |  Lives: {'<3 ' * game.lives}"
    stdscr.addstr(0, 0, header[:game.width], curses.color_pair(7) | curses.A_BOLD)

    # Draw separator
    stdscr.addstr(1, 0, '=' * game.width, curses.color_pair(8))

    # Draw words
    for word in game.words:
        if not word.active:
            continue

        y = int(word.y)
        if y < 2 or y >= game.height - 3:
            continue

        # Draw matched part in green, rest in white
        for i, char in enumerate(word.text):
            x = word.x + i
            if x >= game.width:
                break

            if i < word.matched_chars:
                color = curses.color_pair(2) | curses.A_BOLD
            else:
                # Color based on position (danger indicator)
                danger = word.y / (game.height - 4)
                if danger > 0.7:
                    color = curses.color_pair(5) | curses.A_BOLD
                elif danger > 0.5:
                    color = curses.color_pair(3) | curses.A_BOLD
                else:
                    color = curses.color_pair(7)

            try:
                stdscr.addstr(y, x, char, color)
            except curses.error:
                pass

    # Draw danger line
    danger_y = game.height - 4
    stdscr.addstr(danger_y, 0, '-' * game.width, curses.color_pair(5))

    # Draw input area
    input_y = game.height - 2
    stdscr.addstr(input_y, 0, '>' * game.width, curses.color_pair(8))
    stdscr.addstr(input_y + 1, 0, ' Type: ', curses.color_pair(7))

    # Draw current input with cursor
    input_display = game.current_input + '_'
    stdscr.addstr(input_y + 1, 7, input_display, curses.color_pair(4) | curses.A_BOLD)

    # Draw game over
    if game.game_over:
        lines = [
            "  GAME OVER!  ",
            "",
            f" Final Score: {game.score} ",
            f" Words Typed: {game.words_typed} ",
            f" Max Combo: {game.max_combo}x ",
            "",
            " Press R to restart ",
        ]

        box_width = max(len(line) for line in lines) + 4
        box_height = len(lines) + 2
        box_x = game.width // 2 - box_width // 2
        box_y = game.height // 2 - box_height // 2

        for i in range(box_height):
            try:
                stdscr.addstr(box_y + i, box_x, ' ' * box_width,
                              curses.color_pair(5) | curses.A_REVERSE)
            except curses.error:
                pass

        for i, line in enumerate(lines):
            x = game.width // 2 - len(line) // 2
            try:
                stdscr.addstr(box_y + 1 + i, x, line,
                              curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass

    stdscr.refresh()


def draw_title(stdscr, width, height):
    """Draw title screen."""
    stdscr.clear()

    title = [
        " _____ _  _ ___  _ _  _  ___    ",
        "|_   _| || | _ \\| | \\| |/ __|   ",
        "  | | \\_  _|  _/| | .` | (_ |   ",
        "  |_|   |_||_|  |_|_|\\_|\\___|   ",
        "                                ",
        "   ___   _   __  __ ___         ",
        "  / __| /_\\ |  \\/  | __|        ",
        " | (_ |/ _ \\| |\\/| | _|         ",
        "  \\___/_/ \\_\\_|  |_|___|        ",
    ]

    start_y = height // 2 - 8
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        color = curses.color_pair((i % 5) + 1)
        try:
            stdscr.addstr(start_y + i, max(0, x), line, color | curses.A_BOLD)
        except curses.error:
            pass

    instructions = [
        "",
        "Type the falling words before they hit the bottom!",
        "Build combos for bonus points!",
        "",
        "Press any key to start",
    ]

    for i, line in enumerate(instructions):
        y = height // 2 + 4 + i
        x = width // 2 - len(line) // 2
        try:
            stdscr.addstr(y, x, line, curses.color_pair(7))
        except curses.error:
            pass

    stdscr.refresh()


def init_colors():
    """Initialize colors."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    curses.init_pair(8, 8, -1)


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()

    height, width = stdscr.getmaxyx()

    # Title screen
    draw_title(stdscr, width, height)
    stdscr.nodelay(False)
    stdscr.getch()
    stdscr.nodelay(True)

    game = Game(width, height)
    last_time = time.time()

    while True:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Handle input
        try:
            key = stdscr.getch()
        except:
            key = -1

        if key != -1:
            if key == 27:  # Escape
                game.clear_input()
            elif key in [ord('r'), ord('R')] and game.game_over:
                game = Game(width, height)
            elif game.game_over:
                pass
            elif key == curses.KEY_BACKSPACE or key == 127:
                if game.current_input:
                    game.current_input = game.current_input[:-1]
                    # Update matched chars
                    for word in game.words:
                        if word.active and word.text.startswith(game.current_input):
                            word.matched_chars = len(game.current_input)
                        else:
                            word.matched_chars = 0
            elif 32 <= key <= 126:  # Printable characters
                char = chr(key).lower()
                game.type_char(char)

        # Check for quit (only when no input)
        if key in [ord('q'), ord('Q')] and not game.current_input and not game.game_over:
            break

        # Update
        game.update(dt)

        # Draw
        draw_game(stdscr, game)

        time.sleep(0.033)  # ~30 FPS


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing Typing Game! Goodbye!\n")
