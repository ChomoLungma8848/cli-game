#!/usr/bin/env python3
"""
VERTICAL SHOOTER - Shoot down enemies and survive!

Controls:
  ← / A  : Move left
  → / D  : Move right
  ↑ / W  : Move up
  ↓ / S  : Move down
  Space  : Fire
  P      : Pause
  Q      : Quit
"""

import curses
import random
import time
import math

# Player ship
PLAYER_SHIP = [
    "  ^  ",
    " /A\\ ",
    "/===\\",
]

# Enemy types
ENEMIES = {
    'scout': {
        'sprite': ["<*>"],
        'hp': 1,
        'points': 100,
        'speed': 0.8,
        'color': 3,
    },
    'fighter': {
        'sprite': [" V ", "/W\\"],
        'hp': 2,
        'points': 200,
        'speed': 0.5,
        'color': 5,
    },
    'bomber': {
        'sprite': ["[===]", " | | "],
        'hp': 4,
        'points': 400,
        'speed': 0.3,
        'color': 6,
    },
    'boss': {
        'sprite': [
            "  ___  ",
            " /o o\\ ",
            "|=====|",
            " \\___/ ",
        ],
        'hp': 20,
        'points': 2000,
        'speed': 0.2,
        'color': 5,
    },
}

POWERUP_TYPES = {
    'rapid': {'char': 'R', 'color': 3, 'name': 'Rapid Fire'},
    'spread': {'char': 'S', 'color': 6, 'name': 'Spread Shot'},
    'shield': {'char': 'O', 'color': 2, 'name': 'Shield'},
    'life': {'char': '+', 'color': 5, 'name': 'Extra Life'},
}


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 5
        self.height = 3
        self.lives = 3
        self.alive = True
        self.respawn_timer = 0
        self.invincible_timer = 0

        # Powerups
        self.rapid_fire = 0
        self.spread_shot = 0
        self.shield = 0

    def get_fire_delay(self):
        return 0.1 if self.rapid_fire > 0 else 0.25


class Bullet:
    def __init__(self, x, y, dx=0, dy=-1, is_player=True, speed=1.5):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.is_player = is_player
        self.speed = speed
        self.active = True


class Enemy:
    def __init__(self, x, y, enemy_type):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.data = ENEMIES[enemy_type]
        self.hp = self.data['hp']
        self.sprite = self.data['sprite']
        self.width = max(len(line) for line in self.sprite)
        self.height = len(self.sprite)
        self.alive = True
        self.move_timer = 0
        self.shoot_timer = random.uniform(1, 3)
        self.move_dir = random.choice([-1, 1])


class Powerup:
    def __init__(self, x, y, ptype):
        self.x = x
        self.y = y
        self.type = ptype
        self.data = POWERUP_TYPES[ptype]
        self.active = True


class Explosion:
    def __init__(self, x, y, size='small'):
        self.x = x
        self.y = y
        self.frame = 0
        self.size = size
        self.active = True

        if size == 'small':
            self.frames = ['*', '+', '.']
        else:
            self.frames = [
                ['\\|/', '-*-', '/|\\'],
                [' | ', '-+-', ' | '],
                [' . ', ' . ', ' . '],
            ]


class Star:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed
        self.char = random.choice(['.', '*', '+'])


class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.score = 0
        self.high_score = 0
        self.wave = 1
        self.game_over = False
        self.paused = False

        self.player = Player(width // 2 - 2, height - 5)
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.explosions = []
        self.stars = []

        self.fire_timer = 0
        self.spawn_timer = 0
        self.wave_timer = 0
        self.enemies_spawned = 0
        self.enemies_to_spawn = 5

        # Create stars
        for _ in range(30):
            self.stars.append(Star(
                random.randint(0, width - 1),
                random.randint(0, height - 1),
                random.uniform(0.2, 0.8)
            ))

    def spawn_enemy(self):
        """Spawn a new enemy."""
        if self.enemies_spawned >= self.enemies_to_spawn:
            return

        # Choose enemy type based on wave
        if self.wave >= 10 and random.random() < 0.1 and not any(e.type == 'boss' for e in self.enemies):
            enemy_type = 'boss'
        elif self.wave >= 5 and random.random() < 0.2:
            enemy_type = 'bomber'
        elif self.wave >= 3 and random.random() < 0.3:
            enemy_type = 'fighter'
        else:
            enemy_type = 'scout'

        sprite_width = max(len(line) for line in ENEMIES[enemy_type]['sprite'])
        x = random.randint(2, self.width - sprite_width - 2)
        y = -len(ENEMIES[enemy_type]['sprite'])

        self.enemies.append(Enemy(x, y, enemy_type))
        self.enemies_spawned += 1

    def fire_bullet(self):
        """Fire player bullet."""
        if self.fire_timer > 0 or not self.player.alive:
            return

        px = self.player.x + self.player.width // 2
        py = self.player.y - 1

        if self.player.spread_shot > 0:
            self.bullets.append(Bullet(px, py, -0.3, -1))
            self.bullets.append(Bullet(px, py, 0, -1))
            self.bullets.append(Bullet(px, py, 0.3, -1))
        else:
            self.bullets.append(Bullet(px, py))

        self.fire_timer = self.player.get_fire_delay()

    def enemy_fire(self, enemy):
        """Enemy fires a bullet."""
        ex = enemy.x + enemy.width // 2
        ey = enemy.y + enemy.height

        # Aim at player
        dx = self.player.x - ex
        dy = self.player.y - ey
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx = dx / dist * 0.5
            dy = dy / dist * 0.5

        self.bullets.append(Bullet(ex, ey, dx, max(0.3, dy), False, 0.8))

    def update(self, dt):
        """Update game state."""
        if self.paused or self.game_over:
            return

        # Update timers
        self.fire_timer = max(0, self.fire_timer - dt)

        # Update powerup timers
        if self.player.rapid_fire > 0:
            self.player.rapid_fire -= dt
        if self.player.spread_shot > 0:
            self.player.spread_shot -= dt
        if self.player.shield > 0:
            self.player.shield -= dt
        if self.player.invincible_timer > 0:
            self.player.invincible_timer -= dt

        # Player respawn
        if not self.player.alive:
            self.player.respawn_timer -= dt
            if self.player.respawn_timer <= 0:
                self.player.alive = True
                self.player.x = self.width // 2 - 2
                self.player.invincible_timer = 2.0

        # Update stars
        for star in self.stars:
            star.y += star.speed
            if star.y >= self.height:
                star.y = 0
                star.x = random.randint(0, self.width - 1)

        # Spawn enemies
        self.spawn_timer += dt
        if self.spawn_timer >= max(0.5, 2.0 - self.wave * 0.1):
            self.spawn_enemy()
            self.spawn_timer = 0

        # Check wave complete
        if self.enemies_spawned >= self.enemies_to_spawn and not self.enemies:
            self.wave += 1
            self.enemies_spawned = 0
            self.enemies_to_spawn = 5 + self.wave * 2

        # Update enemies
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            # Move down
            enemy.y += enemy.data['speed']

            # Horizontal movement for some enemies
            if enemy.type in ['fighter', 'boss']:
                enemy.move_timer += dt
                if enemy.move_timer >= 0.5:
                    enemy.x += enemy.move_dir * 2
                    if enemy.x <= 1 or enemy.x >= self.width - enemy.width - 1:
                        enemy.move_dir *= -1
                    enemy.move_timer = 0

            # Shooting
            enemy.shoot_timer -= dt
            if enemy.shoot_timer <= 0:
                self.enemy_fire(enemy)
                enemy.shoot_timer = random.uniform(1.5, 3.0) if enemy.type != 'boss' else 0.5

            # Off screen
            if enemy.y > self.height:
                enemy.alive = False

        # Update bullets
        for bullet in self.bullets:
            if not bullet.active:
                continue

            bullet.x += bullet.dx * bullet.speed
            bullet.y += bullet.dy * bullet.speed

            # Off screen
            if bullet.y < 0 or bullet.y >= self.height or bullet.x < 0 or bullet.x >= self.width:
                bullet.active = False
                continue

            if bullet.is_player:
                # Hit enemy
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue

                    if (enemy.x <= bullet.x <= enemy.x + enemy.width and
                        enemy.y <= bullet.y <= enemy.y + enemy.height):
                        bullet.active = False
                        enemy.hp -= 1

                        if enemy.hp <= 0:
                            enemy.alive = False
                            self.score += enemy.data['points'] * self.wave
                            size = 'big' if enemy.type == 'boss' else 'small'
                            self.explosions.append(Explosion(
                                enemy.x + enemy.width // 2,
                                enemy.y + enemy.height // 2,
                                size
                            ))

                            # Drop powerup
                            if random.random() < 0.15:
                                ptype = random.choice(list(POWERUP_TYPES.keys()))
                                self.powerups.append(Powerup(
                                    enemy.x + enemy.width // 2,
                                    enemy.y,
                                    ptype
                                ))
                        break
            else:
                # Hit player
                if self.player.alive and self.player.invincible_timer <= 0:
                    if (self.player.x <= bullet.x <= self.player.x + self.player.width and
                        self.player.y <= bullet.y <= self.player.y + self.player.height):

                        if self.player.shield > 0:
                            self.player.shield = 0
                            bullet.active = False
                        else:
                            bullet.active = False
                            self.player_hit()

        # Enemy collision with player
        for enemy in self.enemies:
            if not enemy.alive or not self.player.alive:
                continue
            if self.player.invincible_timer > 0:
                continue

            if (self.player.x < enemy.x + enemy.width and
                self.player.x + self.player.width > enemy.x and
                self.player.y < enemy.y + enemy.height and
                self.player.y + self.player.height > enemy.y):

                if self.player.shield > 0:
                    self.player.shield = 0
                    enemy.alive = False
                    self.explosions.append(Explosion(enemy.x, enemy.y, 'small'))
                else:
                    self.player_hit()
                    enemy.alive = False

        # Update powerups
        for powerup in self.powerups:
            if not powerup.active:
                continue

            powerup.y += 0.3

            if powerup.y >= self.height:
                powerup.active = False
                continue

            # Collect
            if self.player.alive:
                if (self.player.x <= powerup.x <= self.player.x + self.player.width and
                    self.player.y <= powerup.y <= self.player.y + self.player.height):
                    powerup.active = False
                    self.apply_powerup(powerup.type)

        # Update explosions
        for exp in self.explosions:
            exp.frame += dt * 5
            max_frames = len(exp.frames) if exp.size == 'small' else len(exp.frames)
            if exp.frame >= max_frames:
                exp.active = False

        # Clean up
        self.bullets = [b for b in self.bullets if b.active]
        self.enemies = [e for e in self.enemies if e.alive]
        self.powerups = [p for p in self.powerups if p.active]
        self.explosions = [e for e in self.explosions if e.active]

        # Update high score
        if self.score > self.high_score:
            self.high_score = self.score

    def player_hit(self):
        """Handle player being hit."""
        self.player.lives -= 1
        self.player.alive = False
        self.explosions.append(Explosion(
            self.player.x + self.player.width // 2,
            self.player.y + 1,
            'big'
        ))

        if self.player.lives <= 0:
            self.game_over = True
        else:
            self.player.respawn_timer = 2.0
            self.player.rapid_fire = 0
            self.player.spread_shot = 0
            self.player.shield = 0

    def apply_powerup(self, ptype):
        """Apply powerup effect."""
        if ptype == 'rapid':
            self.player.rapid_fire = 10.0
        elif ptype == 'spread':
            self.player.spread_shot = 10.0
        elif ptype == 'shield':
            self.player.shield = 15.0
        elif ptype == 'life':
            self.player.lives += 1

    def move_player(self, dx, dy):
        """Move player."""
        if not self.player.alive:
            return

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        if 1 <= new_x <= self.width - self.player.width - 1:
            self.player.x = new_x
        if 5 <= new_y <= self.height - self.player.height - 1:
            self.player.y = new_y


def draw_game(stdscr, game):
    """Draw the game."""
    stdscr.clear()

    # Draw stars
    for star in game.stars:
        try:
            stdscr.addstr(int(star.y), int(star.x), star.char, curses.color_pair(8))
        except curses.error:
            pass

    # Draw powerups
    for powerup in game.powerups:
        try:
            stdscr.addstr(int(powerup.y), int(powerup.x), powerup.data['char'],
                          curses.color_pair(powerup.data['color']) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw enemies
    for enemy in game.enemies:
        if not enemy.alive:
            continue
        color = curses.color_pair(enemy.data['color'])
        for i, line in enumerate(enemy.sprite):
            y = int(enemy.y) + i
            if 0 <= y < game.height:
                try:
                    stdscr.addstr(y, int(enemy.x), line, color | curses.A_BOLD)
                except curses.error:
                    pass

    # Draw bullets
    for bullet in game.bullets:
        if not bullet.active:
            continue
        char = '|' if bullet.is_player else 'v'
        color = curses.color_pair(2 if bullet.is_player else 5)
        try:
            stdscr.addstr(int(bullet.y), int(bullet.x), char, color | curses.A_BOLD)
        except curses.error:
            pass

    # Draw player
    if game.player.alive:
        # Blink when invincible
        if game.player.invincible_timer <= 0 or int(time.time() * 10) % 2:
            color = curses.color_pair(2)
            if game.player.shield > 0:
                color = curses.color_pair(6)
            for i, line in enumerate(PLAYER_SHIP):
                try:
                    stdscr.addstr(game.player.y + i, game.player.x, line, color | curses.A_BOLD)
                except curses.error:
                    pass

    # Draw explosions
    for exp in game.explosions:
        frame_idx = min(int(exp.frame), len(exp.frames) - 1)
        if exp.size == 'small':
            try:
                stdscr.addstr(int(exp.y), int(exp.x), exp.frames[frame_idx],
                              curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
        else:
            frame = exp.frames[frame_idx]
            for i, line in enumerate(frame):
                y = int(exp.y) - 1 + i
                x = int(exp.x) - 1
                if 0 <= y < game.height:
                    try:
                        stdscr.addstr(y, x, line, curses.color_pair(5) | curses.A_BOLD)
                    except curses.error:
                        pass

    # Draw HUD
    hud = f" Score: {game.score}  |  High: {game.high_score}  |  Wave: {game.wave}  |  Lives: {'<3 ' * game.player.lives}"
    stdscr.addstr(0, 0, hud[:game.width], curses.color_pair(7) | curses.A_BOLD)

    # Powerup indicators
    indicators = []
    if game.player.rapid_fire > 0:
        indicators.append(f"R:{int(game.player.rapid_fire)}")
    if game.player.spread_shot > 0:
        indicators.append(f"S:{int(game.player.spread_shot)}")
    if game.player.shield > 0:
        indicators.append(f"O:{int(game.player.shield)}")

    if indicators:
        indicator_str = " | ".join(indicators)
        stdscr.addstr(1, 0, indicator_str, curses.color_pair(6))

    # Pause/Game over
    if game.paused:
        msg = " PAUSED "
        stdscr.addstr(game.height // 2, game.width // 2 - len(msg) // 2, msg,
                      curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)

    if game.game_over:
        lines = [
            "  GAME OVER  ",
            "",
            f" Score: {game.score} ",
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
        " ____  _   _  ___   ___ _____ _____ ____  ",
        "/ ___|| | | |/ _ \\ / _ \\_   _| ____|  _ \\ ",
        "\\___ \\| |_| | | | | | | || | |  _| | |_) |",
        " ___) |  _  | |_| | |_| || | | |___|  _ < ",
        "|____/|_| |_|\\___/ \\___/ |_| |_____|_| \\_\\",
    ]

    start_y = height // 2 - 8
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        color = curses.color_pair((i % 4) + 2)
        try:
            stdscr.addstr(start_y + i, max(0, x), line, color | curses.A_BOLD)
        except curses.error:
            pass

    instructions = [
        "",
        "Destroy enemies and survive!",
        "",
        "Arrow keys / WASD: Move",
        "Space: Fire",
        "P: Pause",
        "",
        "Powerups: R=Rapid  S=Spread  O=Shield  +=Life",
        "",
        "Press SPACE to start",
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
        elif key in [ord('p'), ord('P')]:
            game.paused = not game.paused
        elif not game.game_over and not game.paused:
            if key in [curses.KEY_LEFT, ord('a'), ord('A')]:
                game.move_player(-2, 0)
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D')]:
                game.move_player(2, 0)
            elif key in [curses.KEY_UP, ord('w'), ord('W')]:
                game.move_player(0, -1)
            elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
                game.move_player(0, 1)
            elif key == ord(' '):
                game.fire_bullet()

        # Update
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
        print("\nThanks for playing Shooter! Goodbye!\n")
