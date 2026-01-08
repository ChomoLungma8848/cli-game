#!/usr/bin/env python3
"""
SPACE INVADERS - Classic arcade shooter

Controls:
  ← / A  : Move left
  → / D  : Move right
  Space  : Fire!
  P      : Pause
  Q      : Quit
"""

import curses
import random
import time

# Game settings
PLAYER_LIVES = 3
INVADER_ROWS = 5
INVADER_COLS = 11
INVADER_POINTS = [30, 20, 20, 10, 10]  # Points per row (top to bottom)

# Sprites
PLAYER_SPRITE = [" /^\\ ", "/###\\"]
PLAYER_WIDTH = 5

INVADER_SPRITES = [
    # Type 0 (top row - 30 pts)
    [[" {o} ", " /|\\ "], [" {o} ", " \\|/ "]],
    # Type 1 (rows 2-3 - 20 pts)
    [[" dOb ", " /^\\ "], [" dOb ", " \\v/ "]],
    # Type 2 (rows 4-5 - 10 pts)
    [[" |o| ", " / \\ "], [" |o| ", " \\ / "]],
]

UFO_SPRITE = "<=(@)=>"
UFO_WIDTH = 7
UFO_POINTS = [50, 100, 150, 300]

EXPLOSION_FRAMES = ["\\*/", " * ", " . ", "   "]

BARRIER_CHAR = '#'


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.lives = PLAYER_LIVES
        self.alive = True
        self.respawn_timer = 0

    def move(self, dx, max_x):
        new_x = self.x + dx
        if new_x >= 0 and new_x <= max_x - PLAYER_WIDTH:
            self.x = new_x


class Bullet:
    def __init__(self, x, y, dy, is_player=True):
        self.x = x
        self.y = y
        self.dy = dy
        self.is_player = is_player
        self.active = True


class Invader:
    def __init__(self, x, y, type_id, points):
        self.x = x
        self.y = y
        self.type_id = type_id
        self.points = points
        self.alive = True


class UFO:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.active = True
        self.points = random.choice(UFO_POINTS)


class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.frame = 0
        self.active = True


class Barrier:
    def __init__(self, x, y):
        self.blocks = set()
        # Create barrier shape
        pattern = [
            "  ######  ",
            " ######## ",
            "##########",
            "##########",
            "##########",
            "###    ###",
        ]
        for row, line in enumerate(pattern):
            for col, char in enumerate(line):
                if char == '#':
                    self.blocks.add((x + col, y + row))


class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.score = 0
        self.high_score = 0
        self.wave = 1
        self.game_over = False
        self.paused = False

        self.player = None
        self.invaders = []
        self.bullets = []
        self.explosions = []
        self.barriers = []
        self.ufo = None

        self.invader_direction = 1
        self.invader_move_timer = 0
        self.invader_move_delay = 0.5
        self.invader_frame = 0

        self.ufo_timer = 0
        self.ufo_spawn_delay = 15

        self.init_game()

    def init_game(self):
        """Initialize or reset the game."""
        # Create player
        self.player = Player(self.width // 2 - PLAYER_WIDTH // 2, self.height - 3)

        # Create invaders
        self.spawn_invaders()

        # Create barriers
        self.barriers = []
        barrier_spacing = self.width // 5
        for i in range(4):
            bx = barrier_spacing * (i + 1) - 5
            by = self.height - 10
            self.barriers.append(Barrier(bx, by))

        self.bullets = []
        self.explosions = []
        self.ufo = None
        self.invader_direction = 1
        self.invader_frame = 0
        self.update_speed()

    def spawn_invaders(self):
        """Spawn a wave of invaders."""
        self.invaders = []
        start_x = (self.width - INVADER_COLS * 6) // 2
        start_y = 4

        for row in range(INVADER_ROWS):
            type_id = 0 if row == 0 else (1 if row < 3 else 2)
            points = INVADER_POINTS[row]

            for col in range(INVADER_COLS):
                x = start_x + col * 6
                y = start_y + row * 3
                self.invaders.append(Invader(x, y, type_id, points))

    def update_speed(self):
        """Update invader speed based on remaining count and wave."""
        alive_count = sum(1 for inv in self.invaders if inv.alive)
        total = INVADER_ROWS * INVADER_COLS

        if alive_count == 0:
            return

        # Speed increases as fewer invaders remain
        ratio = alive_count / total
        base_delay = max(0.1, 0.5 - (self.wave - 1) * 0.05)

        if ratio > 0.75:
            self.invader_move_delay = base_delay
        elif ratio > 0.5:
            self.invader_move_delay = base_delay * 0.7
        elif ratio > 0.25:
            self.invader_move_delay = base_delay * 0.5
        elif ratio > 0.1:
            self.invader_move_delay = base_delay * 0.3
        else:
            self.invader_move_delay = base_delay * 0.15

    def fire_player_bullet(self):
        """Fire a bullet from the player."""
        # Limit player bullets on screen
        player_bullets = sum(1 for b in self.bullets if b.is_player and b.active)
        if player_bullets < 3 and self.player.alive:
            bx = self.player.x + PLAYER_WIDTH // 2
            by = self.player.y - 1
            self.bullets.append(Bullet(bx, by, -1, True))

    def fire_invader_bullet(self):
        """Random invader fires a bullet."""
        alive_invaders = [inv for inv in self.invaders if inv.alive]
        if alive_invaders and random.random() < 0.02 + self.wave * 0.005:
            # Find bottom invaders in each column
            columns = {}
            for inv in alive_invaders:
                col = inv.x
                if col not in columns or inv.y > columns[col].y:
                    columns[col] = inv

            shooter = random.choice(list(columns.values()))
            bx = shooter.x + 2
            by = shooter.y + 2
            self.bullets.append(Bullet(bx, by, 1, False))

    def move_invaders(self):
        """Move all invaders."""
        alive_invaders = [inv for inv in self.invaders if inv.alive]
        if not alive_invaders:
            return

        # Check boundaries
        min_x = min(inv.x for inv in alive_invaders)
        max_x = max(inv.x for inv in alive_invaders) + 5
        max_y = max(inv.y for inv in alive_invaders)

        move_down = False

        if self.invader_direction > 0 and max_x >= self.width - 2:
            move_down = True
            self.invader_direction = -1
        elif self.invader_direction < 0 and min_x <= 2:
            move_down = True
            self.invader_direction = 1

        for inv in alive_invaders:
            if move_down:
                inv.y += 1
            else:
                inv.x += self.invader_direction * 2

            # Check if invaders reached bottom
            if inv.y >= self.player.y - 2:
                self.game_over = True

        self.invader_frame = 1 - self.invader_frame
        self.update_speed()

    def spawn_ufo(self):
        """Spawn a UFO."""
        if self.ufo is None and random.random() < 0.02:
            direction = random.choice([-1, 1])
            x = -UFO_WIDTH if direction > 0 else self.width
            self.ufo = UFO(x, 2, direction)

    def update(self, dt):
        """Update game state."""
        if self.paused or self.game_over:
            return

        # Update player respawn
        if not self.player.alive:
            self.player.respawn_timer -= dt
            if self.player.respawn_timer <= 0:
                self.player.alive = True
                self.player.x = self.width // 2 - PLAYER_WIDTH // 2

        # Move invaders
        self.invader_move_timer += dt
        if self.invader_move_timer >= self.invader_move_delay:
            self.move_invaders()
            self.invader_move_timer = 0

        # Invader shooting
        self.fire_invader_bullet()

        # UFO
        self.ufo_timer += dt
        if self.ufo_timer >= self.ufo_spawn_delay:
            self.spawn_ufo()
            self.ufo_timer = 0

        if self.ufo and self.ufo.active:
            self.ufo.x += self.ufo.direction * 0.5
            if self.ufo.x < -UFO_WIDTH or self.ufo.x > self.width:
                self.ufo = None

        # Update bullets
        for bullet in self.bullets:
            if not bullet.active:
                continue

            bullet.y += bullet.dy * 0.5

            # Off screen
            if bullet.y < 0 or bullet.y >= self.height:
                bullet.active = False
                continue

            # Check barrier collision
            for barrier in self.barriers:
                bx, by = int(bullet.x), int(bullet.y)
                if (bx, by) in barrier.blocks:
                    barrier.blocks.discard((bx, by))
                    barrier.blocks.discard((bx, by - bullet.dy))
                    bullet.active = False
                    break

            if not bullet.active:
                continue

            if bullet.is_player:
                # Hit invader
                for inv in self.invaders:
                    if inv.alive:
                        if (inv.x <= bullet.x <= inv.x + 4 and
                            inv.y <= bullet.y <= inv.y + 1):
                            inv.alive = False
                            bullet.active = False
                            self.score += inv.points
                            self.explosions.append(Explosion(inv.x + 1, inv.y))
                            self.update_speed()
                            break

                # Hit UFO
                if self.ufo and self.ufo.active:
                    if (self.ufo.x <= bullet.x <= self.ufo.x + UFO_WIDTH and
                        self.ufo.y <= bullet.y <= self.ufo.y + 1):
                        self.score += self.ufo.points
                        self.explosions.append(Explosion(int(self.ufo.x) + 2, self.ufo.y))
                        self.ufo = None
                        bullet.active = False

            else:
                # Hit player
                if self.player.alive:
                    if (self.player.x <= bullet.x <= self.player.x + PLAYER_WIDTH and
                        self.player.y <= bullet.y <= self.player.y + 1):
                        bullet.active = False
                        self.player_hit()

        # Update explosions
        for exp in self.explosions:
            exp.frame += 0.15
            if exp.frame >= len(EXPLOSION_FRAMES):
                exp.active = False

        # Clean up
        self.bullets = [b for b in self.bullets if b.active]
        self.explosions = [e for e in self.explosions if e.active]

        # Check wave complete
        if all(not inv.alive for inv in self.invaders):
            self.wave += 1
            self.spawn_invaders()
            self.update_speed()

        # Update high score
        if self.score > self.high_score:
            self.high_score = self.score

    def player_hit(self):
        """Handle player being hit."""
        self.player.lives -= 1
        self.player.alive = False
        self.explosions.append(Explosion(self.player.x + 1, self.player.y))

        if self.player.lives <= 0:
            self.game_over = True
        else:
            self.player.respawn_timer = 2.0


def draw_game(stdscr, game):
    """Draw the game."""
    stdscr.clear()

    # Draw header
    header = f" SCORE: {game.score:06d}  |  HIGH: {game.high_score:06d}  |  WAVE: {game.wave}  |  LIVES: {'A ' * game.player.lives}"
    stdscr.addstr(0, 0, header[:game.width], curses.color_pair(7) | curses.A_BOLD)

    # Draw UFO
    if game.ufo and game.ufo.active:
        x = int(game.ufo.x)
        if 0 <= x < game.width - UFO_WIDTH:
            stdscr.addstr(game.ufo.y, x, UFO_SPRITE, curses.color_pair(5) | curses.A_BOLD)

    # Draw invaders
    for inv in game.invaders:
        if inv.alive and 0 <= inv.x < game.width - 4:
            sprite = INVADER_SPRITES[inv.type_id][game.invader_frame]
            color = curses.color_pair(inv.type_id + 1)
            try:
                stdscr.addstr(inv.y, inv.x, sprite[0], color | curses.A_BOLD)
                stdscr.addstr(inv.y + 1, inv.x, sprite[1], color | curses.A_BOLD)
            except curses.error:
                pass

    # Draw barriers
    for barrier in game.barriers:
        for bx, by in barrier.blocks:
            if 0 <= bx < game.width and 0 <= by < game.height:
                try:
                    stdscr.addstr(by, bx, BARRIER_CHAR, curses.color_pair(4))
                except curses.error:
                    pass

    # Draw player
    if game.player.alive:
        try:
            stdscr.addstr(game.player.y, game.player.x, PLAYER_SPRITE[0], curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(game.player.y + 1, game.player.x, PLAYER_SPRITE[1], curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw bullets
    for bullet in game.bullets:
        if bullet.active:
            by = int(bullet.y)
            bx = int(bullet.x)
            if 0 <= bx < game.width and 0 <= by < game.height:
                char = '|' if bullet.is_player else 'v'
                color = curses.color_pair(2 if bullet.is_player else 5)
                try:
                    stdscr.addstr(by, bx, char, color | curses.A_BOLD)
                except curses.error:
                    pass

    # Draw explosions
    for exp in game.explosions:
        frame_idx = min(int(exp.frame), len(EXPLOSION_FRAMES) - 1)
        try:
            stdscr.addstr(exp.y, exp.x, EXPLOSION_FRAMES[frame_idx], curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw pause overlay
    if game.paused:
        msg = " PAUSED - Press P to continue "
        x = game.width // 2 - len(msg) // 2
        y = game.height // 2
        stdscr.addstr(y, x, msg, curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)

    # Draw game over
    if game.game_over:
        lines = [
            "  GAME OVER  ",
            "",
            f" Final Score: {game.score} ",
            f" Wave: {game.wave} ",
            "",
            " R: Restart  Q: Quit ",
        ]
        box_width = max(len(line) for line in lines) + 4
        box_height = len(lines) + 2
        box_x = game.width // 2 - box_width // 2
        box_y = game.height // 2 - box_height // 2

        for i in range(box_height):
            try:
                stdscr.addstr(box_y + i, box_x, ' ' * box_width, curses.color_pair(5) | curses.A_REVERSE)
            except curses.error:
                pass

        for i, line in enumerate(lines):
            try:
                lx = game.width // 2 - len(line) // 2
                stdscr.addstr(box_y + 1 + i, lx, line, curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass

    stdscr.refresh()


def draw_title(stdscr, width, height):
    """Draw title screen."""
    stdscr.clear()

    title = [
        "  ____  ____   _    ____ _____   ",
        " / ___||  _ \\ / \\  / ___| ____|  ",
        " \\___ \\| |_) / _ \\| |   |  _|    ",
        "  ___) |  __/ ___ \\ |___| |___   ",
        " |____/|_| /_/   \\_\\____|_____|  ",
        "",
        " ___ _   ___     ___    ____  _____ ____  ____  ",
        "|_ _| \\ | \\ \\   / / \\  |  _ \\| ____|  _ \\/ ___| ",
        " | ||  \\| |\\ \\ / / _ \\ | | | |  _| | |_) \\___ \\ ",
        " | || |\\  | \\ V / ___ \\| |_| | |___|  _ < ___) |",
        "|___|_| \\_|  \\_/_/   \\_\\____/|_____|_| \\_\\____/ ",
    ]

    start_y = height // 2 - len(title) // 2 - 4

    colors = [1, 1, 1, 1, 1, 7, 4, 4, 4, 4, 4]
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        if x >= 0 and start_y + i < height:
            try:
                stdscr.addstr(start_y + i, x, line, curses.color_pair(colors[i]) | curses.A_BOLD)
            except curses.error:
                pass

    # Instructions
    instructions = [
        "",
        "< > or A D : Move",
        "  SPACE    : Fire",
        "    P      : Pause",
        "    Q      : Quit",
        "",
        "Press SPACE to start!",
    ]

    start_y = height // 2 + 4
    for i, line in enumerate(instructions):
        x = width // 2 - len(line) // 2
        color = curses.color_pair(2) if i == len(instructions) - 1 else curses.color_pair(7)
        if 0 <= start_y + i < height:
            try:
                stdscr.addstr(start_y + i, max(0, x), line, color)
            except curses.error:
                pass

    # Invader preview
    preview_y = height - 6
    preview_x = width // 2 - 15

    previews = [
        (" {o} ", 30, 1),
        (" dOb ", 20, 2),
        (" |o| ", 10, 3),
    ]

    for i, (sprite, pts, color) in enumerate(previews):
        x = preview_x + i * 12
        if x >= 0 and x + 10 < width:
            try:
                stdscr.addstr(preview_y, x, sprite, curses.color_pair(color) | curses.A_BOLD)
                stdscr.addstr(preview_y + 1, x, f"={pts}pts", curses.color_pair(7))
            except curses.error:
                pass

    stdscr.refresh()


def init_colors():
    """Initialize color pairs."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_MAGENTA, -1)  # Top invaders
    curses.init_pair(2, curses.COLOR_CYAN, -1)     # Middle invaders
    curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Bottom invaders
    curses.init_pair(4, curses.COLOR_GREEN, -1)    # Player/barriers
    curses.init_pair(5, curses.COLOR_RED, -1)      # UFO/enemy bullets
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # UI


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
        elif key in [ord('p'), ord('P')]:
            game.paused = not game.paused

        if game.game_over:
            if key in [ord('r'), ord('R')]:
                game = Game(width, height)
        elif not game.paused:
            if key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                game.player.move(-2, width)
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                game.player.move(2, width)
            elif key == ord(' '):
                game.fire_player_bullet()

        # Update and draw
        game.update(dt)
        draw_game(stdscr, game)

        time.sleep(0.016)  # ~60 FPS


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nThanks for playing Space Invaders! Goodbye!\n")
