#!/usr/bin/env python3
"""
Sokoban (倉庫番) - A classic puzzle game
Move boxes ($) to goal positions (.) to complete each level!

Controls:
  W/w or ↑ : Move up
  S/s or ↓ : Move down
  A/a or ← : Move left
  D/d or → : Move right
  R/r     : Restart level
  U/u     : Undo last move
  N/n     : Next level (if unlocked)
  P/p     : Previous level
  Q/q     : Quit game
"""

import os
import sys
import copy

# Game symbols
WALL = '#'
FLOOR = ' '
GOAL = '.'
BOX = '$'
BOX_ON_GOAL = '*'
PLAYER = '@'
PLAYER_ON_GOAL = '+'

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BG_BLACK = '\033[40m'

# Level designs
LEVELS = [
    # Level 1 - Tutorial
    {
        'name': 'First Steps',
        'map': [
            "  #####",
            "###   #",
            "#.@$  #",
            "### $.#",
            "#.##$ #",
            "# # . ##",
            "#$  $$.#",
            "#   .  #",
            "########",
        ]
    },
    # Level 2
    {
        'name': 'The Corner',
        'map': [
            "########",
            "#      #",
            "# .$@. #",
            "#  $$  #",
            "#  ..  #",
            "#  $   #",
            "#      #",
            "########",
        ]
    },
    # Level 3
    {
        'name': 'Warehouse',
        'map': [
            "  ######",
            "  #    #",
            "  # ##.#",
            "### ## ##",
            "#  $    #",
            "# # # # #",
            "# ..#$$ #",
            "####  @##",
            "   #####",
        ]
    },
    # Level 4
    {
        'name': 'Labyrinth',
        'map': [
            "##########",
            "#        #",
            "# ###### #",
            "# #....# #",
            "# #$$$$# #",
            "# #    # #",
            "# # @  # #",
            "#   #### #",
            "#        #",
            "##########",
        ]
    },
    # Level 5
    {
        'name': 'The Challenge',
        'map': [
            "    #####",
            "    #   #",
            "    #$  #",
            "  ###  $##",
            "  #  $ $ #",
            "### # ## #   ######",
            "#   # ## #####  ..#",
            "# $  $          ..#",
            "##### ### #@##  ..#",
            "    #     #########",
            "    #######",
        ]
    },
]

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_char():
    """Get a single character from stdin without requiring Enter."""
    try:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            # Handle arrow keys (escape sequences)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                if ch2 == '[':
                    if ch3 == 'A': return 'w'  # Up
                    if ch3 == 'B': return 's'  # Down
                    if ch3 == 'C': return 'd'  # Right
                    if ch3 == 'D': return 'a'  # Left
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except ImportError:
        # Windows fallback
        import msvcrt
        ch = msvcrt.getch()
        if ch in [b'\x00', b'\xe0']:
            ch2 = msvcrt.getch()
            if ch2 == b'H': return 'w'  # Up
            if ch2 == b'P': return 's'  # Down
            if ch2 == b'M': return 'd'  # Right
            if ch2 == b'K': return 'a'  # Left
        return ch.decode('utf-8', errors='ignore')

class Game:
    def __init__(self):
        self.current_level = 0
        self.max_unlocked = 0
        self.moves = 0
        self.pushes = 0
        self.history = []
        self.load_level(0)

    def load_level(self, level_num):
        """Load a specific level."""
        if level_num < 0 or level_num >= len(LEVELS):
            return False

        self.current_level = level_num
        self.moves = 0
        self.pushes = 0
        self.history = []

        # Parse level map
        level_data = LEVELS[level_num]['map']
        self.level_name = LEVELS[level_num]['name']

        # Find max width
        max_width = max(len(row) for row in level_data)

        # Create game grid
        self.grid = []
        self.goals = set()
        self.player_pos = None

        for y, row in enumerate(level_data):
            grid_row = []
            for x, char in enumerate(row.ljust(max_width)):
                if char == PLAYER:
                    self.player_pos = (x, y)
                    grid_row.append(FLOOR)
                elif char == PLAYER_ON_GOAL:
                    self.player_pos = (x, y)
                    self.goals.add((x, y))
                    grid_row.append(FLOOR)
                elif char == BOX_ON_GOAL:
                    self.goals.add((x, y))
                    grid_row.append(BOX)
                elif char == GOAL:
                    self.goals.add((x, y))
                    grid_row.append(FLOOR)
                else:
                    grid_row.append(char)
            self.grid.append(grid_row)

        return True

    def get_boxes(self):
        """Get all box positions."""
        boxes = set()
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == BOX:
                    boxes.add((x, y))
        return boxes

    def is_complete(self):
        """Check if all boxes are on goals."""
        return self.get_boxes() == self.goals

    def can_move(self, x, y):
        """Check if a position is walkable (floor or box can be pushed)."""
        if y < 0 or y >= len(self.grid) or x < 0 or x >= len(self.grid[y]):
            return False
        return self.grid[y][x] != WALL

    def move_player(self, dx, dy):
        """Try to move the player in the given direction."""
        px, py = self.player_pos
        new_x, new_y = px + dx, py + dy

        if not self.can_move(new_x, new_y):
            return False

        # Check if there's a box to push
        if self.grid[new_y][new_x] == BOX:
            box_new_x, box_new_y = new_x + dx, new_y + dy
            if not self.can_move(box_new_x, box_new_y) or self.grid[box_new_y][box_new_x] == BOX:
                return False

            # Save state for undo
            self.history.append({
                'player': self.player_pos,
                'grid': copy.deepcopy(self.grid),
                'moves': self.moves,
                'pushes': self.pushes
            })

            # Move box
            self.grid[new_y][new_x] = FLOOR
            self.grid[box_new_y][box_new_x] = BOX
            self.pushes += 1
        else:
            # Save state for undo
            self.history.append({
                'player': self.player_pos,
                'grid': copy.deepcopy(self.grid),
                'moves': self.moves,
                'pushes': self.pushes
            })

        # Move player
        self.player_pos = (new_x, new_y)
        self.moves += 1
        return True

    def undo(self):
        """Undo the last move."""
        if self.history:
            state = self.history.pop()
            self.player_pos = state['player']
            self.grid = state['grid']
            self.moves = state['moves']
            self.pushes = state['pushes']
            return True
        return False

    def render(self):
        """Render the game state."""
        clear_screen()

        c = Colors

        # Header
        print(f"{c.BOLD}{c.CYAN}{'=' * 50}{c.RESET}")
        print(f"{c.BOLD}{c.YELLOW}  SOKOBAN - 倉庫番  {c.RESET}")
        print(f"{c.BOLD}{c.CYAN}{'=' * 50}{c.RESET}")
        print()
        print(f"{c.WHITE}  Level {self.current_level + 1}/{len(LEVELS)}: {c.GREEN}{self.level_name}{c.RESET}")
        print(f"{c.WHITE}  Moves: {c.YELLOW}{self.moves}{c.RESET}  |  Pushes: {c.YELLOW}{self.pushes}{c.RESET}")
        print()

        # Render grid
        for y, row in enumerate(self.grid):
            line = "  "
            for x, cell in enumerate(row):
                pos = (x, y)
                if pos == self.player_pos:
                    if pos in self.goals:
                        line += f"{c.BOLD}{c.GREEN}{PLAYER_ON_GOAL}{c.RESET}"
                    else:
                        line += f"{c.BOLD}{c.BLUE}{PLAYER}{c.RESET}"
                elif cell == BOX:
                    if pos in self.goals:
                        line += f"{c.BOLD}{c.GREEN}{BOX_ON_GOAL}{c.RESET}"
                    else:
                        line += f"{c.BOLD}{c.YELLOW}{BOX}{c.RESET}"
                elif pos in self.goals:
                    line += f"{c.RED}{GOAL}{c.RESET}"
                elif cell == WALL:
                    line += f"{c.WHITE}{WALL}{c.RESET}"
                else:
                    line += cell
            print(line)

        print()
        print(f"{c.CYAN}  Controls:{c.RESET}")
        print(f"  {c.WHITE}WASD/Arrows{c.RESET}: Move  |  {c.WHITE}R{c.RESET}: Restart  |  {c.WHITE}U{c.RESET}: Undo")
        print(f"  {c.WHITE}N{c.RESET}: Next Level  |  {c.WHITE}P{c.RESET}: Prev Level  |  {c.WHITE}Q{c.RESET}: Quit")
        print()

        # Legend
        print(f"  {c.MAGENTA}Legend:{c.RESET}")
        print(f"  {c.BLUE}@{c.RESET}=You  {c.YELLOW}${c.RESET}=Box  {c.RED}.{c.RESET}=Goal  {c.GREEN}*{c.RESET}=Box on Goal  {c.WHITE}#{c.RESET}=Wall")
        print()

    def show_victory(self):
        """Show victory screen."""
        clear_screen()
        c = Colors

        print(f"\n{c.BOLD}{c.GREEN}")
        print("  ╔═══════════════════════════════════════╗")
        print("  ║                                       ║")
        print("  ║     ★ LEVEL COMPLETE! ★              ║")
        print("  ║                                       ║")
        print(f"  ║     Level: {self.level_name:<24} ║")
        print(f"  ║     Moves: {self.moves:<24} ║")
        print(f"  ║     Pushes: {self.pushes:<23} ║")
        print("  ║                                       ║")
        print("  ╚═══════════════════════════════════════╝")
        print(f"{c.RESET}")

        if self.current_level < len(LEVELS) - 1:
            print(f"\n  {c.YELLOW}Press N for next level, R to replay, Q to quit{c.RESET}")
        else:
            print(f"\n  {c.CYAN}★ Congratulations! You've completed all levels! ★{c.RESET}")
            print(f"  {c.YELLOW}Press R to replay, P for previous levels, Q to quit{c.RESET}")

    def run(self):
        """Main game loop."""
        while True:
            if self.is_complete():
                if self.current_level > self.max_unlocked:
                    self.max_unlocked = self.current_level
                self.show_victory()
            else:
                self.render()

            key = get_char().lower()

            if key == 'q':
                clear_screen()
                print("\nThanks for playing Sokoban! Goodbye!\n")
                break
            elif key == 'r':
                self.load_level(self.current_level)
            elif key == 'u':
                self.undo()
            elif key == 'n':
                if self.is_complete() or self.current_level < self.max_unlocked:
                    if self.current_level < len(LEVELS) - 1:
                        self.load_level(self.current_level + 1)
            elif key == 'p':
                if self.current_level > 0:
                    self.load_level(self.current_level - 1)
            elif key == 'w':
                self.move_player(0, -1)
            elif key == 's':
                self.move_player(0, 1)
            elif key == 'a':
                self.move_player(-1, 0)
            elif key == 'd':
                self.move_player(1, 0)
            elif key == '\x03':  # Ctrl+C
                clear_screen()
                print("\nGame interrupted. Goodbye!\n")
                break

def show_title():
    """Show title screen."""
    clear_screen()
    c = Colors

    print(f"""
{c.BOLD}{c.CYAN}
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   ███████╗ ██████╗ ██╗  ██╗ ██████╗ ██████╗  █████╗  ║
    ║   ██╔════╝██╔═══██╗██║ ██╔╝██╔═══██╗██╔══██╗██╔══██╗ ║
    ║   ███████╗██║   ██║█████╔╝ ██║   ██║██████╔╝███████║ ║
    ║   ╚════██║██║   ██║██╔═██╗ ██║   ██║██╔══██╗██╔══██║ ║
    ║   ███████║╚██████╔╝██║  ██╗╚██████╔╝██████╔╝██║  ██║ ║
    ║   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝ ║
    ║                                                       ║
    ║                     倉 庫 番                          ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
{c.RESET}
{c.YELLOW}    A Classic Puzzle Game{c.RESET}

    {c.WHITE}Push all boxes {c.YELLOW}${c.WHITE} onto the goals {c.RED}.{c.WHITE} to complete each level!{c.RESET}

    {c.GREEN}Press any key to start...{c.RESET}
""")
    get_char()

def main():
    """Main entry point."""
    try:
        show_title()
        game = Game()
        game.run()
    except KeyboardInterrupt:
        clear_screen()
        print("\nGame interrupted. Goodbye!\n")
    except Exception as e:
        clear_screen()
        print(f"\nAn error occurred: {e}\n")
        raise

if __name__ == '__main__':
    main()
