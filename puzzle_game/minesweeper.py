#!/usr/bin/env python3
"""
MINESWEEPER - Classic puzzle game

Controls:
  Arrow keys / WASD : Move cursor
  Space / Enter     : Reveal cell
  F / M             : Flag/unflag mine
  R                 : New game
  Q                 : Quit
"""

import curses
import random
import time

# Difficulty settings
DIFFICULTIES = {
    'easy': {'width': 9, 'height': 9, 'mines': 10},
    'medium': {'width': 16, 'height': 16, 'mines': 40},
    'hard': {'width': 30, 'height': 16, 'mines': 99},
}

# Cell states
HIDDEN = 0
REVEALED = 1
FLAGGED = 2

# Colors for numbers
NUMBER_COLORS = {
    1: curses.COLOR_BLUE,
    2: curses.COLOR_GREEN,
    3: curses.COLOR_RED,
    4: curses.COLOR_MAGENTA,
    5: curses.COLOR_YELLOW,
    6: curses.COLOR_CYAN,
    7: curses.COLOR_WHITE,
    8: curses.COLOR_WHITE,
}


class Minesweeper:
    def __init__(self, width, height, num_mines):
        self.width = width
        self.height = height
        self.num_mines = num_mines
        self.cursor_x = 0
        self.cursor_y = 0
        self.game_over = False
        self.won = False
        self.first_click = True
        self.start_time = None
        self.end_time = None

        # Initialize board
        self.mines = [[False] * width for _ in range(height)]
        self.state = [[HIDDEN] * width for _ in range(height)]
        self.adjacent = [[0] * width for _ in range(height)]

    def place_mines(self, exclude_x, exclude_y):
        """Place mines randomly, excluding the first click area."""
        excluded = set()
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = exclude_x + dx, exclude_y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    excluded.add((nx, ny))

        positions = [(x, y) for x in range(self.width) for y in range(self.height)
                     if (x, y) not in excluded]

        mine_positions = random.sample(positions, min(self.num_mines, len(positions)))

        for x, y in mine_positions:
            self.mines[y][x] = True

        # Calculate adjacent mine counts
        for y in range(self.height):
            for x in range(self.width):
                if not self.mines[y][x]:
                    count = 0
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.mines[ny][nx]:
                                    count += 1
                    self.adjacent[y][x] = count

    def reveal(self, x, y):
        """Reveal a cell."""
        if self.game_over or self.state[y][x] != HIDDEN:
            return

        if self.first_click:
            self.first_click = False
            self.start_time = time.time()
            self.place_mines(x, y)

        if self.mines[y][x]:
            self.game_over = True
            self.won = False
            self.end_time = time.time()
            # Reveal all mines
            for my in range(self.height):
                for mx in range(self.width):
                    if self.mines[my][mx]:
                        self.state[my][mx] = REVEALED
            return

        # Flood fill for empty cells
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if self.state[cy][cx] == REVEALED:
                continue
            if self.state[cy][cx] == FLAGGED:
                continue

            self.state[cy][cx] = REVEALED

            if self.adjacent[cy][cx] == 0:
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if self.state[ny][nx] == HIDDEN:
                                stack.append((nx, ny))

        self.check_win()

    def toggle_flag(self, x, y):
        """Toggle flag on a cell."""
        if self.game_over or self.state[y][x] == REVEALED:
            return

        if self.state[y][x] == HIDDEN:
            self.state[y][x] = FLAGGED
        else:
            self.state[y][x] = HIDDEN

        self.check_win()

    def check_win(self):
        """Check if player has won."""
        for y in range(self.height):
            for x in range(self.width):
                if not self.mines[y][x] and self.state[y][x] != REVEALED:
                    return

        self.game_over = True
        self.won = True
        self.end_time = time.time()

    def count_flags(self):
        """Count number of flags placed."""
        count = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.state[y][x] == FLAGGED:
                    count += 1
        return count

    def get_elapsed_time(self):
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time else time.time()
        return int(end - self.start_time)


def draw_game(stdscr, game, offset_y, offset_x):
    """Draw the game board."""
    # Draw header
    flags = game.count_flags()
    mines_left = game.num_mines - flags
    elapsed = game.get_elapsed_time()

    header = f" Mines: {mines_left:3d}  |  Time: {elapsed:3d}s "
    stdscr.addstr(offset_y - 2, offset_x, header, curses.color_pair(7) | curses.A_BOLD)

    # Draw board
    for y in range(game.height):
        for x in range(game.width):
            screen_x = offset_x + x * 2
            screen_y = offset_y + y

            is_cursor = (x == game.cursor_x and y == game.cursor_y)
            attr = curses.A_REVERSE if is_cursor else 0

            if game.state[y][x] == HIDDEN:
                stdscr.addstr(screen_y, screen_x, "[]", curses.color_pair(8) | attr)
            elif game.state[y][x] == FLAGGED:
                stdscr.addstr(screen_y, screen_x, ">F", curses.color_pair(5) | curses.A_BOLD | attr)
            elif game.mines[y][x]:
                char = "><" if (x == game.cursor_x and y == game.cursor_y and game.game_over and not game.won) else "()"
                stdscr.addstr(screen_y, screen_x, char, curses.color_pair(5) | curses.A_BOLD | attr)
            else:
                count = game.adjacent[y][x]
                if count == 0:
                    stdscr.addstr(screen_y, screen_x, "  ", attr)
                else:
                    stdscr.addstr(screen_y, screen_x, f" {count}", curses.color_pair(count) | curses.A_BOLD | attr)

    # Draw status
    status_y = offset_y + game.height + 1
    if game.game_over:
        if game.won:
            msg = " YOU WIN! Press R for new game, Q to quit "
            stdscr.addstr(status_y, offset_x, msg, curses.color_pair(4) | curses.A_BOLD)
        else:
            msg = " GAME OVER! Press R for new game, Q to quit "
            stdscr.addstr(status_y, offset_x, msg, curses.color_pair(5) | curses.A_BOLD)
    else:
        msg = " Space: Reveal | F: Flag | R: New | Q: Quit "
        stdscr.addstr(status_y, offset_x, msg, curses.color_pair(7))


def select_difficulty(stdscr):
    """Show difficulty selection screen."""
    stdscr.clear()
    curses.curs_set(0)

    options = ['easy', 'medium', 'hard']
    selected = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        title = "MINESWEEPER"
        stdscr.addstr(height // 2 - 6, width // 2 - len(title) // 2, title,
                      curses.color_pair(4) | curses.A_BOLD)

        stdscr.addstr(height // 2 - 4, width // 2 - 10, "Select Difficulty:",
                      curses.color_pair(7) | curses.A_BOLD)

        for i, opt in enumerate(options):
            diff = DIFFICULTIES[opt]
            text = f"{opt.upper():8} ({diff['width']}x{diff['height']}, {diff['mines']} mines)"
            y = height // 2 - 2 + i * 2

            if i == selected:
                stdscr.addstr(y, width // 2 - 15, "> " + text, curses.color_pair(4) | curses.A_BOLD)
            else:
                stdscr.addstr(y, width // 2 - 15, "  " + text, curses.color_pair(7))

        stdscr.addstr(height // 2 + 5, width // 2 - 12, "Enter: Select  Q: Quit", curses.color_pair(8))
        stdscr.refresh()

        key = stdscr.getch()

        if key in [curses.KEY_UP, ord('w'), ord('W')]:
            selected = (selected - 1) % len(options)
        elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
            selected = (selected + 1) % len(options)
        elif key in [ord('\n'), ord(' ')]:
            return options[selected]
        elif key in [ord('q'), ord('Q')]:
            return None


def init_colors():
    """Initialize colors."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_BLUE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    curses.init_pair(8, 8, -1)  # Gray


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    init_colors()

    while True:
        difficulty = select_difficulty(stdscr)
        if difficulty is None:
            break

        settings = DIFFICULTIES[difficulty]
        game = Minesweeper(settings['width'], settings['height'], settings['mines'])

        height, width = stdscr.getmaxyx()
        offset_x = (width - game.width * 2) // 2
        offset_y = (height - game.height) // 2

        while True:
            stdscr.clear()
            draw_game(stdscr, game, offset_y, offset_x)
            stdscr.refresh()

            key = stdscr.getch()

            if key in [ord('q'), ord('Q')]:
                return
            elif key in [ord('r'), ord('R')]:
                break  # New game
            elif not game.game_over:
                if key in [curses.KEY_UP, ord('w'), ord('W')]:
                    game.cursor_y = max(0, game.cursor_y - 1)
                elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
                    game.cursor_y = min(game.height - 1, game.cursor_y + 1)
                elif key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                    game.cursor_x = max(0, game.cursor_x - 1)
                elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                    game.cursor_x = min(game.width - 1, game.cursor_x + 1)
                elif key in [ord(' '), ord('\n')]:
                    game.reveal(game.cursor_x, game.cursor_y)
                elif key in [ord('f'), ord('F'), ord('m'), ord('M')]:
                    game.toggle_flag(game.cursor_x, game.cursor_y)


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing Minesweeper! Goodbye!\n")
