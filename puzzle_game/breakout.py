#!/usr/bin/env python3
"""
BREAKOUT - Classic brick breaker game

Controls:
  ← / A  : Move paddle left
  → / D  : Move paddle right
  Space  : Launch ball / Pause
  Q      : Quit
"""

import curses
import time
import math
import random

# Game settings
PADDLE_WIDTH = 10
BALL_CHAR = 'O'
BRICK_CHARS = '[]'

# Brick colors and points
BRICK_TYPES = [
    {'color': 5, 'points': 50, 'char': '<>'},   # Red
    {'color': 3, 'points': 40, 'char': '{}'},   # Yellow
    {'color': 4, 'points': 30, 'char': '[]'},   # Green
    {'color': 6, 'points': 20, 'char': '()'},   # Cyan
    {'color': 2, 'points': 10, 'char': '##'},   # Blue
]


class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.active = False

    def launch(self):
        """Launch the ball."""
        angle = random.uniform(-0.5, 0.5)
        self.dx = math.sin(angle) * 0.8
        self.dy = -0.8
        self.active = True


class Brick:
    def __init__(self, x, y, brick_type):
        self.x = x
        self.y = y
        self.type = brick_type
        self.alive = True


class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_over = False
        self.paused = False
        self.won = False

        self.paddle_x = width // 2 - PADDLE_WIDTH // 2
        self.paddle_y = height - 3

        self.ball = Ball(width // 2, self.paddle_y - 1)
        self.bricks = []

        self.create_bricks()

    def create_bricks(self):
        """Create brick layout."""
        self.bricks = []
        brick_width = 4
        start_x = 4
        start_y = 4

        cols = (self.width - start_x * 2) // brick_width
        rows = len(BRICK_TYPES)

        for row in range(rows):
            brick_type = BRICK_TYPES[row]
            for col in range(cols):
                x = start_x + col * brick_width
                y = start_y + row * 2
                self.bricks.append(Brick(x, y, brick_type))

    def reset_ball(self):
        """Reset ball to paddle."""
        self.ball.x = self.paddle_x + PADDLE_WIDTH // 2
        self.ball.y = self.paddle_y - 1
        self.ball.dx = 0
        self.ball.dy = 0
        self.ball.active = False

    def move_paddle(self, dx):
        """Move paddle."""
        new_x = self.paddle_x + dx
        if new_x >= 1 and new_x <= self.width - PADDLE_WIDTH - 1:
            self.paddle_x = new_x
            if not self.ball.active:
                self.ball.x = self.paddle_x + PADDLE_WIDTH // 2

    def update(self, dt):
        """Update game state."""
        if self.paused or self.game_over or not self.ball.active:
            return

        # Move ball
        self.ball.x += self.ball.dx
        self.ball.y += self.ball.dy

        # Wall collision
        if self.ball.x <= 1:
            self.ball.x = 1
            self.ball.dx = abs(self.ball.dx)
        elif self.ball.x >= self.width - 2:
            self.ball.x = self.width - 2
            self.ball.dx = -abs(self.ball.dx)

        if self.ball.y <= 1:
            self.ball.y = 1
            self.ball.dy = abs(self.ball.dy)

        # Bottom - lose life
        if self.ball.y >= self.height - 1:
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                self.reset_ball()
            return

        # Paddle collision
        if (self.ball.dy > 0 and
            self.paddle_y <= self.ball.y <= self.paddle_y + 1 and
            self.paddle_x <= self.ball.x <= self.paddle_x + PADDLE_WIDTH):

            self.ball.dy = -abs(self.ball.dy)

            # Angle based on hit position
            hit_pos = (self.ball.x - self.paddle_x) / PADDLE_WIDTH
            self.ball.dx = (hit_pos - 0.5) * 1.5

            # Speed up slightly
            speed = math.sqrt(self.ball.dx ** 2 + self.ball.dy ** 2)
            if speed < 1.5:
                factor = 1.02
                self.ball.dx *= factor
                self.ball.dy *= factor

        # Brick collision
        ball_x = int(self.ball.x)
        ball_y = int(self.ball.y)

        for brick in self.bricks:
            if not brick.alive:
                continue

            if (brick.x <= ball_x <= brick.x + 3 and
                brick.y <= ball_y <= brick.y + 1):

                brick.alive = False
                self.score += brick.type['points'] * self.level

                # Determine bounce direction
                # Simple approach: reverse y direction
                self.ball.dy = -self.ball.dy
                break

        # Check win
        if all(not b.alive for b in self.bricks):
            self.level += 1
            self.create_bricks()
            self.reset_ball()


def draw_game(stdscr, game):
    """Draw the game."""
    stdscr.clear()

    # Draw border
    for y in range(game.height):
        stdscr.addstr(y, 0, '|', curses.color_pair(7))
        stdscr.addstr(y, game.width - 1, '|', curses.color_pair(7))
    for x in range(game.width):
        stdscr.addstr(0, x, '-', curses.color_pair(7))

    # Draw header
    header = f" Score: {game.score}  Level: {game.level}  Lives: {'O ' * game.lives}"
    stdscr.addstr(0, 2, header, curses.color_pair(7) | curses.A_BOLD)

    # Draw bricks
    for brick in game.bricks:
        if brick.alive:
            try:
                stdscr.addstr(brick.y, brick.x, brick.type['char'] * 2,
                              curses.color_pair(brick.type['color']) | curses.A_BOLD)
            except curses.error:
                pass

    # Draw paddle
    paddle_str = '=' * PADDLE_WIDTH
    try:
        stdscr.addstr(game.paddle_y, game.paddle_x, paddle_str, curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw ball
    ball_x = int(game.ball.x)
    ball_y = int(game.ball.y)
    if 0 <= ball_x < game.width and 0 <= ball_y < game.height:
        try:
            stdscr.addstr(ball_y, ball_x, BALL_CHAR, curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw status
    if game.paused:
        msg = " PAUSED - Press Space to continue "
        stdscr.addstr(game.height // 2, game.width // 2 - len(msg) // 2, msg,
                      curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)
    elif not game.ball.active:
        msg = " Press Space to launch ball "
        stdscr.addstr(game.height // 2, game.width // 2 - len(msg) // 2, msg,
                      curses.color_pair(4) | curses.A_BOLD)
    elif game.game_over:
        lines = [
            " GAME OVER ",
            f" Final Score: {game.score} ",
            " Press R to restart, Q to quit ",
        ]
        for i, line in enumerate(lines):
            y = game.height // 2 - 1 + i
            x = game.width // 2 - len(line) // 2
            stdscr.addstr(y, x, line, curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)

    # Controls hint
    hint = " <-/-> or A/D: Move | Space: Launch/Pause | Q: Quit "
    stdscr.addstr(game.height - 1, 2, hint[:game.width - 4], curses.color_pair(8))

    stdscr.refresh()


def draw_title(stdscr, width, height):
    """Draw title screen."""
    stdscr.clear()

    title = [
        " ____  ____  _____ _   _ _  _____  _   _ _____ ",
        "| __ )|  _ \\| ____/ \\ | |/ /  _ \\| | | |_   _|",
        "|  _ \\| |_) |  _|/ _ \\| ' /| | | | | | | | |  ",
        "| |_) |  _ <| |_/ ___ \\ . \\| |_| | |_| | | |  ",
        "|____/|_| \\_\\___|_/   \\_\\_|\\_\\____/ \\___/  |_|  ",
    ]

    start_y = height // 2 - 6
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        color = curses.color_pair((i % 5) + 1)
        try:
            stdscr.addstr(start_y + i, max(0, x), line, color | curses.A_BOLD)
        except curses.error:
            pass

    instructions = [
        "",
        "Break all the bricks!",
        "",
        "Press SPACE to start",
    ]

    for i, line in enumerate(instructions):
        y = height // 2 + 2 + i
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
    curses.init_pair(2, curses.COLOR_BLUE, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
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
    while True:
        key = stdscr.getch()
        if key == ord(' '):
            break
        if key in [ord('q'), ord('Q')]:
            return
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

        if key in [ord('q'), ord('Q')]:
            break
        elif key in [ord('r'), ord('R')] and game.game_over:
            game = Game(width, height)
        elif not game.game_over:
            if key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                game.move_paddle(-3)
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                game.move_paddle(3)
            elif key == ord(' '):
                if game.ball.active:
                    game.paused = not game.paused
                else:
                    game.ball.launch()

        # Update
        if not game.paused:
            game.update(dt)

        # Draw
        draw_game(stdscr, game)

        time.sleep(0.016)


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing Breakout! Goodbye!\n")
