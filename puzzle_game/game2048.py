#!/usr/bin/env python3
"""
2048 - Slide and merge tiles to reach 2048!

Controls:
  Arrow keys / WASD : Slide tiles
  R                 : New game
  Q                 : Quit
"""

import curses
import random
import copy

# Tile colors
TILE_COLORS = {
    0: (0, 0),        # Empty
    2: (7, 0),        # White
    4: (6, 0),        # Cyan
    8: (3, 0),        # Yellow
    16: (2, 0),       # Green
    32: (4, 0),       # Blue
    64: (5, 0),       # Red
    128: (3, 1),      # Yellow bold
    256: (2, 1),      # Green bold
    512: (6, 1),      # Cyan bold
    1024: (5, 1),     # Red bold
    2048: (4, 1),     # Blue bold
}


class Game2048:
    def __init__(self, size=4):
        self.size = size
        self.board = [[0] * size for _ in range(size)]
        self.score = 0
        self.best_score = 0
        self.game_over = False
        self.won = False
        self.continue_playing = False

        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        """Spawn a new tile (2 or 4) in a random empty cell."""
        empty_cells = [(x, y) for y in range(self.size) for x in range(self.size)
                       if self.board[y][x] == 0]

        if empty_cells:
            x, y = random.choice(empty_cells)
            self.board[y][x] = 4 if random.random() < 0.1 else 2

    def slide_row_left(self, row):
        """Slide and merge a single row to the left."""
        # Remove zeros
        new_row = [x for x in row if x != 0]

        # Merge adjacent equal tiles
        merged = []
        skip = False
        for i in range(len(new_row)):
            if skip:
                skip = False
                continue

            if i + 1 < len(new_row) and new_row[i] == new_row[i + 1]:
                merged_value = new_row[i] * 2
                merged.append(merged_value)
                self.score += merged_value
                skip = True
            else:
                merged.append(new_row[i])

        # Pad with zeros
        while len(merged) < self.size:
            merged.append(0)

        return merged

    def move(self, direction):
        """Move tiles in the given direction."""
        old_board = copy.deepcopy(self.board)

        if direction == 'left':
            for y in range(self.size):
                self.board[y] = self.slide_row_left(self.board[y])

        elif direction == 'right':
            for y in range(self.size):
                self.board[y] = self.slide_row_left(self.board[y][::-1])[::-1]

        elif direction == 'up':
            for x in range(self.size):
                col = [self.board[y][x] for y in range(self.size)]
                new_col = self.slide_row_left(col)
                for y in range(self.size):
                    self.board[y][x] = new_col[y]

        elif direction == 'down':
            for x in range(self.size):
                col = [self.board[y][x] for y in range(self.size)]
                new_col = self.slide_row_left(col[::-1])[::-1]
                for y in range(self.size):
                    self.board[y][x] = new_col[y]

        # Check if board changed
        if self.board != old_board:
            self.spawn_tile()
            self.check_game_state()

        if self.score > self.best_score:
            self.best_score = self.score

    def check_game_state(self):
        """Check if game is won or over."""
        # Check for 2048 tile
        if not self.continue_playing:
            for row in self.board:
                if 2048 in row:
                    self.won = True
                    return

        # Check for empty cells
        for row in self.board:
            if 0 in row:
                return

        # Check for possible merges
        for y in range(self.size):
            for x in range(self.size):
                current = self.board[y][x]
                # Check right neighbor
                if x + 1 < self.size and self.board[y][x + 1] == current:
                    return
                # Check bottom neighbor
                if y + 1 < self.size and self.board[y + 1][x] == current:
                    return

        self.game_over = True


def draw_tile(stdscr, y, x, value, cell_width=7, cell_height=3):
    """Draw a single tile."""
    color_pair, bold = TILE_COLORS.get(value, (7, 0))
    attr = curses.color_pair(color_pair)
    if bold:
        attr |= curses.A_BOLD

    if value == 0:
        # Empty cell
        for row in range(cell_height):
            try:
                stdscr.addstr(y + row, x, '.' + ' ' * (cell_width - 2) + '.', curses.color_pair(8))
            except curses.error:
                pass
    else:
        # Tile with value
        value_str = str(value).center(cell_width - 2)
        try:
            stdscr.addstr(y, x, '+' + '-' * (cell_width - 2) + '+', attr)
            stdscr.addstr(y + 1, x, '|' + value_str + '|', attr | curses.A_BOLD)
            stdscr.addstr(y + 2, x, '+' + '-' * (cell_width - 2) + '+', attr)
        except curses.error:
            pass


def draw_game(stdscr, game, offset_y, offset_x):
    """Draw the game board."""
    cell_width = 7
    cell_height = 3

    # Draw title
    title = "2048"
    stdscr.addstr(offset_y - 4, offset_x + (cell_width * game.size) // 2 - 2,
                  title, curses.color_pair(3) | curses.A_BOLD)

    # Draw scores
    score_text = f"Score: {game.score}"
    best_text = f"Best: {game.best_score}"
    stdscr.addstr(offset_y - 2, offset_x, score_text, curses.color_pair(7) | curses.A_BOLD)
    stdscr.addstr(offset_y - 2, offset_x + cell_width * game.size - len(best_text),
                  best_text, curses.color_pair(6) | curses.A_BOLD)

    # Draw board
    for y in range(game.size):
        for x in range(game.size):
            tile_x = offset_x + x * cell_width
            tile_y = offset_y + y * cell_height
            draw_tile(stdscr, tile_y, tile_x, game.board[y][x], cell_width, cell_height)

    # Draw controls
    controls = "Arrow keys / WASD: Move | R: New Game | Q: Quit"
    stdscr.addstr(offset_y + game.size * cell_height + 1, offset_x, controls, curses.color_pair(8))

    # Draw win/lose message
    if game.won and not game.continue_playing:
        msg = " YOU WIN! Press C to continue or R for new game "
        y = offset_y + (game.size * cell_height) // 2
        x = offset_x + (game.size * cell_width) // 2 - len(msg) // 2
        stdscr.addstr(y, x, msg, curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD)
    elif game.game_over:
        msg = " GAME OVER! Press R for new game "
        y = offset_y + (game.size * cell_height) // 2
        x = offset_x + (game.size * cell_width) // 2 - len(msg) // 2
        stdscr.addstr(y, x, msg, curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)


def draw_title_screen(stdscr, width, height):
    """Draw title screen."""
    stdscr.clear()

    title = [
        " ___   ___  _  _   ___  ",
        "|__ \\ / _ \\| || | / _ \\ ",
        "   ) | | | | || || (_) |",
        "  / /| | | |__   _> _ < ",
        " / /_| |_| |  | || (_) |",
        "|____|\\___/   |_| \\___/ ",
    ]

    start_y = height // 2 - 8
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        color = curses.color_pair((i % 5) + 2)
        try:
            stdscr.addstr(start_y + i, x, line, color | curses.A_BOLD)
        except curses.error:
            pass

    instructions = [
        "",
        "Join the numbers and get to the 2048 tile!",
        "",
        "Press any key to start",
    ]

    for i, line in enumerate(instructions):
        y = height // 2 + i
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

    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    curses.init_pair(8, 8, -1)


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    init_colors()

    height, width = stdscr.getmaxyx()

    # Title screen
    draw_title_screen(stdscr, width, height)
    stdscr.getch()

    game = Game2048()

    cell_width = 7
    cell_height = 3
    board_width = game.size * cell_width
    board_height = game.size * cell_height

    offset_x = (width - board_width) // 2
    offset_y = (height - board_height) // 2

    while True:
        stdscr.clear()
        draw_game(stdscr, game, offset_y, offset_x)
        stdscr.refresh()

        key = stdscr.getch()

        if key in [ord('q'), ord('Q')]:
            break
        elif key in [ord('r'), ord('R')]:
            game = Game2048()
        elif key in [ord('c'), ord('C')] and game.won:
            game.continue_playing = True
            game.won = False
        elif not game.game_over and (not game.won or game.continue_playing):
            if key in [curses.KEY_UP, ord('w'), ord('W')]:
                game.move('up')
            elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
                game.move('down')
            elif key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                game.move('left')
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                game.move('right')


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing 2048! Goodbye!\n")
