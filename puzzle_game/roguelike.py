#!/usr/bin/env python3
"""
ROGUELIKE DUNGEON - Explore dungeons, fight monsters, collect loot!

Controls:
  Arrow keys / WASD / HJKL : Move
  Space / Enter            : Attack / Interact
  I                        : Inventory
  G                        : Pick up item
  .                        : Wait a turn
  Q                        : Quit
"""

import curses
import random

# Tile types
FLOOR = '.'
WALL = '#'
DOOR = '+'
STAIRS_DOWN = '>'
STAIRS_UP = '<'

# Entity symbols
PLAYER = '@'
GOBLIN = 'g'
ORC = 'o'
TROLL = 'T'
SKELETON = 's'
DRAGON = 'D'

# Item symbols
POTION_HEALTH = '!'
GOLD = '$'
WEAPON = '/'
ARMOR = '['
SCROLL = '?'

# Colors
COLOR_PLAYER = 2      # Green
COLOR_ENEMY = 5       # Red
COLOR_ITEM = 3        # Yellow
COLOR_WALL = 8        # Gray
COLOR_FLOOR = 8       # Gray
COLOR_STAIRS = 6      # Cyan
COLOR_UI = 7          # White


class Entity:
    def __init__(self, x, y, char, name, color, hp=10, attack=2, defense=0):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.alive = True

    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual_damage


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER, "Hero", COLOR_PLAYER, hp=30, attack=5, defense=1)
        self.level = 1
        self.exp = 0
        self.exp_to_level = 20
        self.gold = 0
        self.inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_level:
            self.level_up()
            return True
        return False

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_level
        self.exp_to_level = int(self.exp_to_level * 1.5)
        self.max_hp += 5
        self.hp = min(self.hp + 10, self.max_hp)
        self.attack += 2
        self.defense += 1

    def get_attack(self):
        bonus = self.equipped_weapon.bonus if self.equipped_weapon else 0
        return self.attack + bonus

    def get_defense(self):
        bonus = self.equipped_armor.bonus if self.equipped_armor else 0
        return self.defense + bonus


class Item:
    def __init__(self, x, y, char, name, color, item_type, value=0, bonus=0):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.item_type = item_type
        self.value = value
        self.bonus = bonus


class Monster(Entity):
    def __init__(self, x, y, monster_type):
        monsters = {
            'goblin': (GOBLIN, "Goblin", 8, 3, 0, 5),
            'orc': (ORC, "Orc", 15, 5, 1, 15),
            'skeleton': (SKELETON, "Skeleton", 12, 4, 2, 10),
            'troll': (TROLL, "Troll", 25, 7, 3, 30),
            'dragon': (DRAGON, "Dragon", 50, 12, 5, 100),
        }
        char, name, hp, attack, defense, exp = monsters[monster_type]
        super().__init__(x, y, char, name, COLOR_ENEMY, hp, attack, defense)
        self.exp_value = exp


class Dungeon:
    def __init__(self, width, height, level=1):
        self.width = width
        self.height = height
        self.level = level
        self.tiles = [[WALL for _ in range(width)] for _ in range(height)]
        self.rooms = []
        self.monsters = []
        self.items = []
        self.stairs_down = None
        self.stairs_up = None

        self.generate()

    def generate(self):
        """Generate dungeon using BSP."""
        # Create rooms
        num_rooms = random.randint(5, 9)
        min_size = 4
        max_size = 10

        for _ in range(num_rooms * 3):
            if len(self.rooms) >= num_rooms:
                break

            w = random.randint(min_size, max_size)
            h = random.randint(min_size, max_size)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)

            new_room = {'x': x, 'y': y, 'w': w, 'h': h}

            # Check overlap
            overlap = False
            for room in self.rooms:
                if (x < room['x'] + room['w'] + 1 and x + w + 1 > room['x'] and
                    y < room['y'] + room['h'] + 1 and y + h + 1 > room['y']):
                    overlap = True
                    break

            if not overlap:
                self.carve_room(new_room)
                if self.rooms:
                    self.connect_rooms(self.rooms[-1], new_room)
                self.rooms.append(new_room)

        # Place stairs
        if self.rooms:
            first_room = self.rooms[0]
            self.stairs_up = (first_room['x'] + first_room['w'] // 2,
                              first_room['y'] + first_room['h'] // 2)
            self.tiles[self.stairs_up[1]][self.stairs_up[0]] = STAIRS_UP

            last_room = self.rooms[-1]
            self.stairs_down = (last_room['x'] + last_room['w'] // 2,
                                last_room['y'] + last_room['h'] // 2)
            self.tiles[self.stairs_down[1]][self.stairs_down[0]] = STAIRS_DOWN

        # Spawn monsters and items
        self.spawn_monsters()
        self.spawn_items()

    def carve_room(self, room):
        """Carve out a room."""
        for y in range(room['y'], room['y'] + room['h']):
            for x in range(room['x'], room['x'] + room['w']):
                self.tiles[y][x] = FLOOR

    def connect_rooms(self, room1, room2):
        """Connect two rooms with corridors."""
        x1 = room1['x'] + room1['w'] // 2
        y1 = room1['y'] + room1['h'] // 2
        x2 = room2['x'] + room2['w'] // 2
        y2 = room2['y'] + room2['h'] // 2

        if random.random() < 0.5:
            self.carve_h_corridor(x1, x2, y1)
            self.carve_v_corridor(y1, y2, x2)
        else:
            self.carve_v_corridor(y1, y2, x1)
            self.carve_h_corridor(x1, x2, y2)

    def carve_h_corridor(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y][x] = FLOOR

    def carve_v_corridor(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y][x] = FLOOR

    def spawn_monsters(self):
        """Spawn monsters in rooms."""
        monster_types = ['goblin', 'skeleton']
        if self.level >= 3:
            monster_types.append('orc')
        if self.level >= 5:
            monster_types.append('troll')
        if self.level >= 8:
            monster_types.append('dragon')

        for room in self.rooms[1:]:  # Skip first room (player spawn)
            num_monsters = random.randint(0, 2 + self.level // 2)
            for _ in range(num_monsters):
                x = random.randint(room['x'] + 1, room['x'] + room['w'] - 2)
                y = random.randint(room['y'] + 1, room['y'] + room['h'] - 2)

                if self.tiles[y][x] == FLOOR:
                    monster_type = random.choice(monster_types)
                    self.monsters.append(Monster(x, y, monster_type))

    def spawn_items(self):
        """Spawn items in rooms."""
        for room in self.rooms:
            # Gold
            if random.random() < 0.6:
                x = random.randint(room['x'] + 1, room['x'] + room['w'] - 2)
                y = random.randint(room['y'] + 1, room['y'] + room['h'] - 2)
                if self.tiles[y][x] == FLOOR:
                    value = random.randint(5, 20) * self.level
                    self.items.append(Item(x, y, GOLD, f"{value} Gold", COLOR_ITEM, 'gold', value))

            # Health potion
            if random.random() < 0.3:
                x = random.randint(room['x'] + 1, room['x'] + room['w'] - 2)
                y = random.randint(room['y'] + 1, room['y'] + room['h'] - 2)
                if self.tiles[y][x] == FLOOR:
                    self.items.append(Item(x, y, POTION_HEALTH, "Health Potion", COLOR_ITEM, 'potion', 20))

            # Weapon
            if random.random() < 0.15:
                x = random.randint(room['x'] + 1, room['x'] + room['w'] - 2)
                y = random.randint(room['y'] + 1, room['y'] + room['h'] - 2)
                if self.tiles[y][x] == FLOOR:
                    bonus = random.randint(1, 3) + self.level // 2
                    self.items.append(Item(x, y, WEAPON, f"Sword +{bonus}", COLOR_ITEM, 'weapon', 0, bonus))

            # Armor
            if random.random() < 0.1:
                x = random.randint(room['x'] + 1, room['x'] + room['w'] - 2)
                y = random.randint(room['y'] + 1, room['y'] + room['h'] - 2)
                if self.tiles[y][x] == FLOOR:
                    bonus = random.randint(1, 2) + self.level // 3
                    self.items.append(Item(x, y, ARMOR, f"Armor +{bonus}", COLOR_ITEM, 'armor', 0, bonus))

    def is_walkable(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x] != WALL
        return False

    def get_monster_at(self, x, y):
        for monster in self.monsters:
            if monster.alive and monster.x == x and monster.y == y:
                return monster
        return None

    def get_item_at(self, x, y):
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None


class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.dungeon_level = 1
        self.dungeon = Dungeon(width - 20, height - 6, self.dungeon_level)

        # Spawn player in first room
        room = self.dungeon.rooms[0]
        self.player = Player(room['x'] + room['w'] // 2, room['y'] + room['h'] // 2)

        self.messages = []
        self.game_over = False
        self.show_inventory = False

    def add_message(self, text):
        self.messages.append(text)
        if len(self.messages) > 5:
            self.messages.pop(0)

    def move_player(self, dx, dy):
        if self.game_over:
            return

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Check for monster
        monster = self.dungeon.get_monster_at(new_x, new_y)
        if monster:
            self.attack_monster(monster)
            self.monster_turns()
            return

        # Check walkable
        if self.dungeon.is_walkable(new_x, new_y):
            self.player.x = new_x
            self.player.y = new_y

            # Check stairs
            if self.dungeon.tiles[new_y][new_x] == STAIRS_DOWN:
                self.add_message("Press > to descend")
            elif self.dungeon.tiles[new_y][new_x] == STAIRS_UP:
                self.add_message("Press < to ascend")

            # Check item
            item = self.dungeon.get_item_at(new_x, new_y)
            if item:
                self.add_message(f"You see {item.name}. Press G to pick up.")

            self.monster_turns()

    def attack_monster(self, monster):
        damage = monster.take_damage(self.player.get_attack())
        self.add_message(f"You hit {monster.name} for {damage} damage!")

        if not monster.alive:
            self.add_message(f"You killed {monster.name}!")
            if self.player.gain_exp(monster.exp_value):
                self.add_message(f"Level up! You are now level {self.player.level}!")

    def monster_turns(self):
        """Process monster AI."""
        for monster in self.dungeon.monsters:
            if not monster.alive:
                continue

            # Simple AI: move toward player if close
            dx = self.player.x - monster.x
            dy = self.player.y - monster.y
            dist = abs(dx) + abs(dy)

            if dist == 1:
                # Attack player
                damage = self.player.take_damage(monster.attack)
                self.add_message(f"{monster.name} hits you for {damage} damage!")

                if not self.player.alive:
                    self.add_message("You have died!")
                    self.game_over = True
            elif dist < 10:
                # Move toward player
                move_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
                move_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

                new_x = monster.x + move_x
                new_y = monster.y + move_y

                if (self.dungeon.is_walkable(new_x, new_y) and
                    not self.dungeon.get_monster_at(new_x, new_y) and
                    (new_x != self.player.x or new_y != self.player.y)):
                    monster.x = new_x
                    monster.y = new_y

    def pick_up_item(self):
        item = self.dungeon.get_item_at(self.player.x, self.player.y)
        if item:
            if item.item_type == 'gold':
                self.player.gold += item.value
                self.add_message(f"Picked up {item.value} gold!")
            elif item.item_type == 'potion':
                self.player.inventory.append(item)
                self.add_message(f"Picked up {item.name}!")
            elif item.item_type == 'weapon':
                self.player.equipped_weapon = item
                self.add_message(f"Equipped {item.name}!")
            elif item.item_type == 'armor':
                self.player.equipped_armor = item
                self.add_message(f"Equipped {item.name}!")

            self.dungeon.items.remove(item)

    def use_potion(self):
        for i, item in enumerate(self.player.inventory):
            if item.item_type == 'potion':
                heal = item.value
                self.player.hp = min(self.player.hp + heal, self.player.max_hp)
                self.player.inventory.pop(i)
                self.add_message(f"Used {item.name}. Healed {heal} HP!")
                return
        self.add_message("No potions!")

    def go_down_stairs(self):
        if self.dungeon.tiles[self.player.y][self.player.x] == STAIRS_DOWN:
            self.dungeon_level += 1
            self.dungeon = Dungeon(self.width - 20, self.height - 6, self.dungeon_level)
            room = self.dungeon.rooms[0]
            self.player.x = room['x'] + room['w'] // 2
            self.player.y = room['y'] + room['h'] // 2
            self.add_message(f"You descend to dungeon level {self.dungeon_level}...")


def draw_game(stdscr, game):
    """Draw the game."""
    stdscr.clear()

    dungeon = game.dungeon
    player = game.player
    offset_y = 1

    # Draw dungeon
    for y in range(dungeon.height):
        for x in range(dungeon.width):
            tile = dungeon.tiles[y][x]
            color = COLOR_FLOOR

            if tile == WALL:
                color = COLOR_WALL
            elif tile in [STAIRS_DOWN, STAIRS_UP]:
                color = COLOR_STAIRS

            try:
                stdscr.addstr(y + offset_y, x, tile, curses.color_pair(color))
            except curses.error:
                pass

    # Draw items
    for item in dungeon.items:
        try:
            stdscr.addstr(item.y + offset_y, item.x, item.char,
                          curses.color_pair(item.color) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw monsters
    for monster in dungeon.monsters:
        if monster.alive:
            try:
                stdscr.addstr(monster.y + offset_y, monster.x, monster.char,
                              curses.color_pair(monster.color) | curses.A_BOLD)
            except curses.error:
                pass

    # Draw player
    try:
        stdscr.addstr(player.y + offset_y, player.x, player.char,
                      curses.color_pair(player.color) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw sidebar
    sidebar_x = dungeon.width + 2
    max_y, max_x = stdscr.getmaxyx()

    def safe_addstr(y, x, text, attr=0):
        """Safely add string, avoiding cursor at last position error."""
        try:
            if y < max_y and x < max_x:
                # Truncate text if it would go beyond screen
                available = max_x - x - 1
                if available > 0:
                    stdscr.addstr(y, x, text[:available], attr)
        except curses.error:
            pass

    safe_addstr(1, sidebar_x, "ROGUELIKE", curses.color_pair(COLOR_UI) | curses.A_BOLD)
    safe_addstr(2, sidebar_x, "=" * 15, curses.color_pair(COLOR_WALL))

    safe_addstr(4, sidebar_x, f"Level: {player.level}", curses.color_pair(COLOR_UI))
    safe_addstr(5, sidebar_x, f"HP: {player.hp}/{player.max_hp}", curses.color_pair(2 if player.hp > player.max_hp // 3 else 5))
    safe_addstr(6, sidebar_x, f"ATK: {player.get_attack()}", curses.color_pair(COLOR_UI))
    safe_addstr(7, sidebar_x, f"DEF: {player.get_defense()}", curses.color_pair(COLOR_UI))
    safe_addstr(8, sidebar_x, f"EXP: {player.exp}/{player.exp_to_level}", curses.color_pair(COLOR_UI))
    safe_addstr(9, sidebar_x, f"Gold: {player.gold}", curses.color_pair(3))
    safe_addstr(10, sidebar_x, f"Floor: {game.dungeon_level}", curses.color_pair(COLOR_UI))

    # Equipment
    safe_addstr(12, sidebar_x, "Equipment:", curses.color_pair(COLOR_UI) | curses.A_BOLD)
    weapon_name = player.equipped_weapon.name if player.equipped_weapon else "None"
    armor_name = player.equipped_armor.name if player.equipped_armor else "None"
    safe_addstr(13, sidebar_x, f"Wpn: {weapon_name[:12]}", curses.color_pair(COLOR_UI))
    safe_addstr(14, sidebar_x, f"Arm: {armor_name[:12]}", curses.color_pair(COLOR_UI))

    # Inventory
    potions = sum(1 for item in player.inventory if item.item_type == 'potion')
    safe_addstr(16, sidebar_x, f"Potions: {potions}", curses.color_pair(COLOR_ITEM))
    safe_addstr(17, sidebar_x, "P: Use potion", curses.color_pair(COLOR_WALL))

    # Messages
    msg_y = dungeon.height + 2
    if msg_y < max_y:
        safe_addstr(msg_y, 0, "-" * min(dungeon.width, max_x - 1), curses.color_pair(COLOR_WALL))
    for i, msg in enumerate(game.messages[-3:]):
        if msg_y + 1 + i < max_y:
            safe_addstr(msg_y + 1 + i, 0, msg[:dungeon.width], curses.color_pair(COLOR_UI))

    # Controls
    controls_y = dungeon.height + 6
    if controls_y < max_y:
        safe_addstr(controls_y, 0, "Move: Arrows/WASD | G: Get | >: Descend | Q: Quit",
                    curses.color_pair(COLOR_WALL))

    # Game over overlay
    if game.game_over:
        lines = [
            "  YOU DIED  ",
            "",
            f" Level: {player.level} ",
            f" Gold: {player.gold} ",
            f" Floor: {game.dungeon_level} ",
            "",
            " Press R to restart ",
        ]

        box_width = max(len(line) for line in lines) + 4
        box_height = len(lines) + 2
        box_x = dungeon.width // 2 - box_width // 2
        box_y = dungeon.height // 2 - box_height // 2

        for i in range(box_height):
            try:
                stdscr.addstr(box_y + i + offset_y, box_x, ' ' * box_width,
                              curses.color_pair(5) | curses.A_REVERSE)
            except curses.error:
                pass

        for i, line in enumerate(lines):
            x = dungeon.width // 2 - len(line) // 2
            try:
                stdscr.addstr(box_y + 1 + i + offset_y, x, line,
                              curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass

    stdscr.refresh()


def draw_title(stdscr, width, height):
    """Draw title screen."""
    stdscr.clear()

    title = [
        " ____   ___   ____ _   _ _____ _     ___ _  _______ ",
        "|  _ \\ / _ \\ / ___| | | | ____| |   |_ _| |/ / ____|",
        "| |_) | | | | |  _| | | |  _| | |    | || ' /|  _|  ",
        "|  _ <| |_| | |_| | |_| | |___| |___ | || . \\| |___ ",
        "|_| \\_\\\\___/ \\____|\\___/|_____|_____|___|_|\\_\\_____|",
    ]

    start_y = height // 2 - 8
    for i, line in enumerate(title):
        x = width // 2 - len(line) // 2
        color = curses.color_pair((i % 4) + 2)
        try:
            stdscr.addstr(start_y + i, max(0, x), line, color | curses.A_BOLD)
        except curses.error:
            pass

    subtitle = "~ Dungeon Crawler ~"
    try:
        stdscr.addstr(start_y + 6, max(0, width // 2 - len(subtitle) // 2), subtitle,
                      curses.color_pair(3))
    except curses.error:
        pass

    instructions = [
        "",
        "Explore dungeons, slay monsters, collect treasure!",
        "",
        "@ = You   g/o/s/T/D = Monsters",
        "! = Potion   $ = Gold   / = Weapon   [ = Armor",
        "> = Stairs down   < = Stairs up",
        "",
        "Press any key to start",
    ]

    for i, line in enumerate(instructions):
        y = height // 2 + 1 + i
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
    # Use gray (color 8) if available, otherwise fall back to white
    if curses.COLORS > 8:
        curses.init_pair(8, 8, -1)
    else:
        curses.init_pair(8, curses.COLOR_WHITE, -1)


def main(stdscr):
    """Main game loop."""
    curses.curs_set(0)
    init_colors()

    height, width = stdscr.getmaxyx()

    # Minimum size check
    min_width = 60
    min_height = 20
    if width < min_width or height < min_height:
        stdscr.clear()
        msg = f"Terminal too small! Need {min_width}x{min_height}, got {width}x{height}"
        try:
            stdscr.addstr(0, 0, msg[:width-1])
            stdscr.addstr(1, 0, "Please resize your terminal and restart."[:width-1])
        except curses.error:
            pass
        stdscr.refresh()
        stdscr.getch()
        return

    # Title screen
    draw_title(stdscr, width, height)
    stdscr.getch()

    game = Game(width, height)

    while True:
        draw_game(stdscr, game)

        key = stdscr.getch()

        if key in [ord('q'), ord('Q')]:
            break
        elif key in [ord('r'), ord('R')] and game.game_over:
            game = Game(width, height)
        elif not game.game_over:
            # Movement
            if key in [curses.KEY_UP, ord('w'), ord('W'), ord('k'), ord('K')]:
                game.move_player(0, -1)
            elif key in [curses.KEY_DOWN, ord('s'), ord('S'), ord('j'), ord('J')]:
                game.move_player(0, 1)
            elif key in [curses.KEY_LEFT, ord('a'), ord('A'), ord('h'), ord('H')]:
                game.move_player(-1, 0)
            elif key in [curses.KEY_RIGHT, ord('d'), ord('D'), ord('l'), ord('L')]:
                game.move_player(1, 0)
            elif key in [ord('g'), ord('G')]:
                game.pick_up_item()
            elif key in [ord('p'), ord('P')]:
                game.use_potion()
            elif key == ord('>'):
                game.go_down_stairs()
            elif key == ord('.'):
                game.monster_turns()


if __name__ == '__main__':
    import sys
    import os

    # Check if running in a proper terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Error: This game requires an interactive terminal.")
        print("Please run this game directly from a terminal (not through a pipe or script).")
        sys.exit(1)

    # Set TERM if not set
    if 'TERM' not in os.environ:
        os.environ['TERM'] = 'xterm-256color'

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except curses.error as e:
        print(f"\nTerminal error: {e}")
        print("This game requires a terminal that supports curses.")
        print("Try running in a different terminal emulator.")
        sys.exit(1)
    finally:
        print("\nThanks for playing Roguelike! Goodbye!\n")
