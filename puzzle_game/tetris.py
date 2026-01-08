#!/usr/bin/env python3
"""
TETRIS - Classic falling block puzzle game

Controls:
  ← / A  : Move left
  → / D  : Move right
  ↓ / S  : Soft drop (faster fall)
  ↑ / W  : Rotate clockwise
  Space  : Hard drop (instant fall)
  P      : Pause
  Q      : Quit
"""

import curses
import random
import time

# Tetromino shapes (each rotation state)
TETROMINOES = {
    'I': [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    'O': [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    'T': [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

# Color pairs for each piece
PIECE_COLORS = {
    'I': 1,  # Cyan
    'O': 2,  # Yellow
    'T': 3,  # Magenta
    'S': 4,  # Green
    'Z': 5,  # Red
    'J': 6,  # Blue
    'L': 7,  # White/Orange
}

BOARD_WIDTH = 10
BOARD_HEIGHT = 20
BLOCK = '[]'
EMPTY = '  '


class Tetris:
    def __init__(self):
        self.board = [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False
        self.paused = False

        self.bag = []
        self.current_piece = None
        self.current_type = None
        self.current_rotation = 0
        self.current_x = 0
        self.current_y = 0
        self.next_type = None

        self.spawn_piece()
        self.next_type = self.get_next_piece_type()

    def get_next_piece_type(self):
        """Get next piece using 7-bag randomizer."""
        if not self.bag:
            self.bag = list(TETROMINOES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn_piece(self):
        """Spawn a new piece at the top."""
        if self.next_type:
            self.current_type = self.next_type
        else:
            self.current_type = self.get_next_piece_type()

        self.next_type = self.get_next_piece_type()
        self.current_rotation = 0
        self.current_piece = TETROMINOES[self.current_type][0]
        self.current_x = BOARD_WIDTH // 2 - 2
        self.current_y = 0

        if not self.is_valid_position(self.current_x, self.current_y, self.current_piece):
            self.game_over = True

    def is_valid_position(self, x, y, piece):
        """Check if the piece can be placed at the given position."""
        for px, py in piece:
            new_x = x + px
            new_y = y + py

            if new_x < 0 or new_x >= BOARD_WIDTH:
                return False
            if new_y >= BOARD_HEIGHT:
                return False
            if new_y >= 0 and self.board[new_y][new_x] is not None:
                return False
        return True

    def move(self, dx, dy):
        """Try to move the current piece."""
        new_x = self.current_x + dx
        new_y = self.current_y + dy

        if self.is_valid_position(new_x, new_y, self.current_piece):
            self.current_x = new_x
            self.current_y = new_y
            return True
        return False

    def rotate(self):
        """Rotate the current piece clockwise."""
        new_rotation = (self.current_rotation + 1) % 4
        new_piece = TETROMINOES[self.current_type][new_rotation]

        # Try normal rotation
        if self.is_valid_position(self.current_x, self.current_y, new_piece):
            self.current_rotation = new_rotation
            self.current_piece = new_piece
            return True

        # Wall kick attempts
        kicks = [(-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for kick_x, kick_y in kicks:
            if self.is_valid_position(self.current_x + kick_x, self.current_y + kick_y, new_piece):
                self.current_x += kick_x
                self.current_y += kick_y
                self.current_rotation = new_rotation
                self.current_piece = new_piece
                return True

        return False

    def hard_drop(self):
        """Drop the piece instantly to the bottom."""
        drop_distance = 0
        while self.move(0, 1):
            drop_distance += 1
        self.score += drop_distance * 2
        self.lock_piece()

    def lock_piece(self):
        """Lock the current piece to the board."""
        for px, py in self.current_piece:
            x = self.current_x + px
            y = self.current_y + py
            if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                self.board[y][x] = self.current_type

        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        """Clear completed lines and update score."""
        lines_to_clear = []

        for y in range(BOARD_HEIGHT):
            if all(cell is not None for cell in self.board[y]):
                lines_to_clear.append(y)

        for y in lines_to_clear:
            del self.board[y]
            self.board.insert(0, [None for _ in range(BOARD_WIDTH)])

        # Scoring
        num_lines = len(lines_to_clear)
        if num_lines > 0:
            self.lines_cleared += num_lines
            points = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += points.get(num_lines, 800) * self.level

            # Level up every 10 lines
            self.level = self.lines_cleared // 10 + 1

    def get_drop_speed(self):
        """Get the current drop speed based on level."""
        speeds = {
            1: 1.0,
            2: 0.8,
            3: 0.65,
            4: 0.5,
            5: 0.4,
            6: 0.3,
            7: 0.25,
            8: 0.2,
            9: 0.15,
            10: 0.1,
        }
        return speeds.get(min(self.level, 10), 0.1)

    def get_ghost_y(self):
        """Get the Y position where the piece would land."""
        ghost_y = self.current_y
        while self.is_valid_position(self.current_x, ghost_y + 1, self.current_piece):
            ghost_y += 1
        return ghost_y


def draw_board(stdscr, game, start_y, start_x):
    """Draw the game board."""
    # Draw border
    for y in range(BOARD_HEIGHT + 2):
        stdscr.addstr(start_y + y, start_x, '|', curses.color_pair(7))
        stdscr.addstr(start_y + y, start_x + BOARD_WIDTH * 2 + 1, '|', curses.color_pair(7))

    stdscr.addstr(start_y + BOARD_HEIGHT + 1, start_x, '+' + '-' * (BOARD_WIDTH * 2) + '+', curses.color_pair(7))

    # Draw ghost piece
    ghost_y = game.get_ghost_y()
    ghost_positions = set()
    for px, py in game.current_piece:
        gx = game.current_x + px
        gy = ghost_y + py
        if gy >= 0:
            ghost_positions.add((gx, gy))

    # Draw board cells
    for y in range(BOARD_HEIGHT):
        for x in range(BOARD_WIDTH):
            screen_x = start_x + 1 + x * 2
            screen_y = start_y + y + 1

            cell = game.board[y][x]
            if cell is not None:
                color = curses.color_pair(PIECE_COLORS[cell])
                stdscr.addstr(screen_y, screen_x, BLOCK, color | curses.A_BOLD)
            elif (x, y) in ghost_positions:
                stdscr.addstr(screen_y, screen_x, '..', curses.color_pair(8))
            else:
                stdscr.addstr(screen_y, screen_x, EMPTY)

    # Draw current piece
    for px, py in game.current_piece:
        x = game.current_x + px
        y = game.current_y + py
        if y >= 0 and 0 <= x < BOARD_WIDTH:
            screen_x = start_x + 1 + x * 2
            screen_y = start_y + y + 1
            color = curses.color_pair(PIECE_COLORS[game.current_type])
            stdscr.addstr(screen_y, screen_x, BLOCK, color | curses.A_BOLD)


def draw_next_piece(stdscr, game, start_y, start_x):
    """Draw the next piece preview."""
    stdscr.addstr(start_y, start_x, 'NEXT:', curses.color_pair(7) | curses.A_BOLD)

    # Clear preview area
    for y in range(4):
        stdscr.addstr(start_y + 1 + y, start_x, '        ')

    # Draw next piece
    next_piece = TETROMINOES[game.next_type][0]
    color = curses.color_pair(PIECE_COLORS[game.next_type])

    for px, py in next_piece:
        stdscr.addstr(start_y + 1 + py, start_x + px * 2, BLOCK, color | curses.A_BOLD)


def draw_stats(stdscr, game, start_y, start_x):
    """Draw game statistics."""
    stdscr.addstr(start_y, start_x, f'SCORE:', curses.color_pair(7) | curses.A_BOLD)
    stdscr.addstr(start_y + 1, start_x, f'{game.score:>8}', curses.color_pair(2))

    stdscr.addstr(start_y + 3, start_x, f'LEVEL:', curses.color_pair(7) | curses.A_BOLD)
    stdscr.addstr(start_y + 4, start_x, f'{game.level:>8}', curses.color_pair(4))

    stdscr.addstr(start_y + 6, start_x, f'LINES:', curses.color_pair(7) | curses.A_BOLD)
    stdscr.addstr(start_y + 7, start_x, f'{game.lines_cleared:>8}', curses.color_pair(1))


def draw_controls(stdscr, start_y, start_x):
    """Draw control instructions."""
    controls = [
        ('CONTROLS:', None),
        ('', None),
        ('<-/A', 'Left'),
        ('->/D', 'Right'),
        ('v /S', 'Down'),
        ('^/W', 'Rotate'),
        ('Space', 'Drop'),
        ('P', 'Pause'),
        ('Q', 'Quit'),
    ]

    for i, (key, action) in enumerate(controls):
        if action is None:
            stdscr.addstr(start_y + i, start_x, key, curses.color_pair(7) | curses.A_BOLD)
        else:
            stdscr.addstr(start_y + i, start_x, f'{key:<6}', curses.color_pair(3))
            stdscr.addstr(start_y + i, start_x + 6, f'{action}', curses.color_pair(7))


def draw_title(stdscr, start_y, start_x):
    """Draw game title."""
    title = [
        " _____ _____ _____ ____  ___ ____  ",
        "|_   _| ____|_   _|  _ \\|_ _/ ___| ",
        "  | | |  _|   | | | |_) || |\\___ \\ ",
        "  | | | |___  | | |  _ < | | ___) |",
        "  |_| |_____| |_| |_| \\_\\___|____/ ",
    ]

    colors = [1, 4, 2, 3, 5]  # Rainbow effect
    for i, line in enumerate(title):
        stdscr.addstr(start_y + i, start_x, line, curses.color_pair(colors[i % len(colors)]) | curses.A_BOLD)


def show_game_over(stdscr, game):
    """Show game over screen."""
    height, width = stdscr.getmaxyx()

    box_width = 30
    box_height = 10
    box_y = height // 2 - box_height // 2
    box_x = width // 2 - box_width // 2

    # Draw box
    for y in range(box_height):
        stdscr.addstr(box_y + y, box_x, ' ' * box_width, curses.color_pair(5) | curses.A_REVERSE)

    stdscr.addstr(box_y + 1, box_x + 7, 'GAME OVER!', curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)
    stdscr.addstr(box_y + 3, box_x + 3, f'Final Score: {game.score}', curses.color_pair(5) | curses.A_REVERSE)
    stdscr.addstr(box_y + 4, box_x + 3, f'Level: {game.level}', curses.color_pair(5) | curses.A_REVERSE)
    stdscr.addstr(box_y + 5, box_x + 3, f'Lines: {game.lines_cleared}', curses.color_pair(5) | curses.A_REVERSE)
    stdscr.addstr(box_y + 7, box_x + 2, 'R: Restart  Q: Quit', curses.color_pair(5) | curses.A_REVERSE)

    stdscr.refresh()


def show_pause(stdscr):
    """Show pause screen."""
    height, width = stdscr.getmaxyx()

    box_width = 20
    box_height = 5
    box_y = height // 2 - box_height // 2
    box_x = width // 2 - box_width // 2

    for y in range(box_height):
        stdscr.addstr(box_y + y, box_x, ' ' * box_width, curses.color_pair(3) | curses.A_REVERSE)

    stdscr.addstr(box_y + 2, box_x + 5, 'PAUSED', curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)
    stdscr.refresh()


def init_colors():
    """Initialize color pairs."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_CYAN, -1)     # I
    curses.init_pair(2, curses.COLOR_YELLOW, -1)   # O
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)  # T
    curses.init_pair(4, curses.COLOR_GREEN, -1)    # S
    curses.init_pair(5, curses.COLOR_RED, -1)      # Z
    curses.init_pair(6, curses.COLOR_BLUE, -1)     # J
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # L / UI
    curses.init_pair(8, 8, -1)                     # Ghost (gray)


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()

    game = Tetris()
    last_drop = time.time()

    while True:
        stdscr.clear()

        # Calculate positions
        height, width = stdscr.getmaxyx()
        board_x = width // 2 - BOARD_WIDTH - 8
        board_y = 7

        # Draw everything
        draw_title(stdscr, 1, board_x - 5)
        draw_board(stdscr, game, board_y, board_x)
        draw_next_piece(stdscr, game, board_y, board_x + BOARD_WIDTH * 2 + 4)
        draw_stats(stdscr, game, board_y + 6, board_x + BOARD_WIDTH * 2 + 4)
        draw_controls(stdscr, board_y + 15, board_x + BOARD_WIDTH * 2 + 4)

        if game.game_over:
            show_game_over(stdscr, game)
            stdscr.nodelay(False)
            while True:
                key = stdscr.getch()
                if key in [ord('q'), ord('Q')]:
                    return
                if key in [ord('r'), ord('R')]:
                    game = Tetris()
                    stdscr.nodelay(True)
                    last_drop = time.time()
                    break
            continue

        if game.paused:
            show_pause(stdscr)

        stdscr.refresh()

        # Handle input
        try:
            key = stdscr.getch()
        except:
            key = -1

        if key in [ord('q'), ord('Q')]:
            break
        elif key in [ord('p'), ord('P')]:
            game.paused = not game.paused
            if not game.paused:
                last_drop = time.time()
        elif not game.paused:
            if key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                game.move(-1, 0)
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                game.move(1, 0)
            elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
                if game.move(0, 1):
                    game.score += 1
                    last_drop = time.time()
            elif key in [curses.KEY_UP, ord('w'), ord('W')]:
                game.rotate()
            elif key == ord(' '):
                game.hard_drop()
                last_drop = time.time()

        # Auto drop
        if not game.paused and not game.game_over:
            current_time = time.time()
            if current_time - last_drop >= game.get_drop_speed():
                if not game.move(0, 1):
                    game.lock_piece()
                last_drop = current_time

        time.sleep(0.016)  # ~60 FPS


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing Tetris! Goodbye!\n")
