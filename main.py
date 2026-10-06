import pygame
import math
import random
import sys
import os

pygame.init()

WIDTH, HEIGHT = 1000, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EVOLUTION")

WORLD_W, WORLD_H = 3200, 2400

# --- MS-DOS-like low framerate -------------------------------------------
FPS = 30
clock = pygame.time.Clock()

# --- MS-DOS style pixel font loading -------------------------------------
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

FONT_CANDIDATES = [
    "dos.ttf",
    "Perfect DOS VGA 437.ttf",
    "PerfectDOSVGA437.ttf",
    "PressStart2P-Regular.ttf",
    "Fixedsys Excelsior 3.01.ttf",
    "More Perfect DOS VGA.ttf",
]

def load_font(size):
    for name in FONT_CANDIDATES:
        for base in (SCRIPT_DIR, os.getcwd()):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                try:
                    return pygame.font.Font(p, size)
                except Exception:
                    pass
    return pygame.font.SysFont("Courier New", size, bold=True)

small_font = load_font(16)
font       = load_font(24)
big_font   = load_font(56)

# --- MS-DOS / EGA 16 colour palette --------------------------------------
BLACK         = (0,   0,   0)
BLUE          = (0,   0,   170)
GREEN         = (0,   170, 0)
CYAN          = (0,   170, 170)
RED           = (170, 0,   0)
MAGENTA       = (170, 0,   170)
BROWN         = (170, 85,  0)
LIGHT_GRAY    = (170, 170, 170)
DARK_GRAY     = (85,  85,  85)
LIGHT_BLUE    = (85,  85,  255)
LIGHT_GREEN   = (85,  255, 85)
LIGHT_CYAN    = (85,  255, 255)
LIGHT_RED     = (255, 85,  85)
LIGHT_MAGENTA = (255, 85,  255)
YELLOW        = (255, 255, 85)
WHITE         = (255, 255, 255)

LEVELS = [
    {"bg": BLUE,        "fg": WHITE},     # 1  blue
    {"bg": RED,         "fg": YELLOW},    # 2  red
    {"bg": GREEN,       "fg": BLACK},     # 3  green
    {"bg": DARK_GRAY,   "fg": WHITE},     # 4  gray
    {"bg": WHITE,       "fg": BLACK},     # 5  white
    {"bg": BLACK,       "fg": WHITE},     # 6  black
    {"bg": CYAN,        "fg": RED},       # 7  cyan
    {"bg": MAGENTA,     "fg": YELLOW},    # 8  magenta
    {"bg": YELLOW,      "fg": BLUE},      # 9  yellow
    {"bg": LIGHT_GRAY,  "fg": MAGENTA},   # 10 light gray
]

# --- Camera: dead-zone + fixed-step snapping -----------------------------
CAM_STEP = 8
DEAD_L = WIDTH  * 0.35
DEAD_R = WIDTH  * 0.65
DEAD_T = HEIGHT * 0.35
DEAD_B = HEIGHT * 0.65

# --- Physics (tuned for 30 FPS: visible per-frame steps) -----------------
DECAY           = 0.95
PLAYER_ACCEL    = 0.50
AI_CHASE_ACCEL  = 0.20
AI_FLEE_ACCEL   = 0.30
AI_WANDER_ACCEL = 0.13

# --------------------------------------------------------------------------
def size_of(lvl, sub):
    return 10 + (lvl - 1) * 13 + (sub - 1) * 8


def shape_for_level(level):
    level = min(max(level, 1), 10)
    if level <= 6:
        return ('poly', level + 2)
    if level == 7:
        return ('poly', 14)
    if level == 8:
        return ('star', 5)
    if level == 9:
        return ('star', 6)
    return ('star', 8)


def polygon_points(kind, n, radius):
    pts = []
    if kind == 'poly':
        for i in range(n):
            a = 2 * math.pi * i / n - math.pi / 2
            pts.append((radius * math.cos(a), radius * math.sin(a)))
    else:
        for i in range(n * 2):
            r = radius if i % 2 == 0 else radius * 0.42
            a = math.pi * i / n - math.pi / 2
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def draw_creature(surf, c, color, thickness, cam_x, cam_y):
    kind, n = shape_for_level(c.level)
    r = c.size
    pts = polygon_points(kind, n, r)
    abs_pts = [(int(c.x - cam_x + p[0]),
                int(c.y - cam_y + p[1])) for p in pts]
    if len(abs_pts) >= 3:
        pygame.draw.polygon(surf, color, abs_pts, thickness)


# --------------------------------------------------------------------------
class Creature:
    def __init__(self, x, y, level, sublevel, is_player=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.level = level
        self.sublevel = sublevel
        self.is_player = is_player
        self.angle = random.uniform(0, 2 * math.pi)
        self.wander_timer = random.randint(20, 70)
        self.alive = True
        self.flash = 0

    @property
    def size(self):
        return size_of(self.level, self.sublevel)

    def physics(self):
        self.vx *= DECAY
        self.vy *= DECAY
        self.x += self.vx
        self.y += self.vy
        m = self.size * 0.6
        if self.x < m:
            self.x = m
            self.vx = -self.vx * 0.6
        elif self.x > WORLD_W - m:
            self.x = WORLD_W - m
            self.vx = -self.vx * 0.6
        if self.y < m:
            self.y = m
            self.vy = -self.vy * 0.6
        elif self.y > WORLD_H - m:
            self.y = WORLD_H - m
            self.vy = -self.vy * 0.6
        if self.flash > 0:
            self.flash -= 1

    def update_ai(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 1
        vision = 320 + self.size

        if dist < vision and self.size > player.size * 1.15:
            self.angle = math.atan2(dy, dx)
            self.vx += math.cos(self.angle) * AI_CHASE_ACCEL
            self.vy += math.sin(self.angle) * AI_CHASE_ACCEL
        elif dist < vision * 0.9 and player.size > self.size * 1.15:
            self.angle = math.atan2(-dy, -dx)
            self.vx += math.cos(self.angle) * AI_FLEE_ACCEL
            self.vy += math.sin(self.angle) * AI_FLEE_ACCEL
        else:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.angle += random.uniform(-1.0, 1.0)
                self.wander_timer = random.randint(20, 70)
            self.vx += math.cos(self.angle) * AI_WANDER_ACCEL
            self.vy += math.sin(self.angle) * AI_WANDER_ACCEL

        self.physics()


# --------------------------------------------------------------------------
def find_candidates(player, mode):
    cands = []
    for lvl in range(1, 11):
        for sub in range(1, 6):
            s = size_of(lvl, sub)
            if mode == 'small' and s < player.size * 0.85:
                cands.append((lvl, sub))
            elif mode == 'big' and player.size * 1.15 < s < player.size * 1.9:
                cands.append((lvl, sub))
            elif mode == 'any' and 0.7 * player.size <= s <= 1.4 * player.size:
                cands.append((lvl, sub))
    return cands


def spawn_enemy(player, mode='any'):
    cands = find_candidates(player, mode)
    if not cands:
        return None
    lvl, sub = random.choice(cands)
    x = y = 0
    for _ in range(60):
        x = random.randint(80, WORLD_W - 80)
        y = random.randint(80, WORLD_H - 80)
        if math.hypot(x - player.x, y - player.y) > 350:
            break
    return Creature(x, y, lvl, sub)


def grow(c):
    c.sublevel += 1
    if c.sublevel > 5:
        c.sublevel = 1
        c.level += 1
    if c.level > 10:
        c.level = 10
        c.sublevel = 5
    c.flash = 8


def reset_game():
    player = Creature(WORLD_W // 2, WORLD_H // 2, 3, 1, is_player=True)
    enemies = []
    for _ in range(5):
        e = spawn_enemy(player, 'small')
        if e: enemies.append(e)
    for _ in range(5):
        e = spawn_enemy(player, 'any')
        if e: enemies.append(e)
    for _ in range(3):
        e = spawn_enemy(player, 'big')
        if e: enemies.append(e)
    return player, enemies, 'play', 30


def initial_cam(player):
    cx = int(max(0, min(WORLD_W - WIDTH,  player.x - WIDTH  // 2)))
    cy = int(max(0, min(WORLD_H - HEIGHT, player.y - HEIGHT // 2)))
    return cx, cy


# --------------------------------------------------------------------------
def draw_minimap(surf, player, enemies, cam_x, cam_y, fg):
    mw, mh = 160, 120
    mx = WIDTH - mw - 12
    my = HEIGHT - mh - 12
    pygame.draw.rect(surf, fg, (mx, my, mw, mh), 1)
    sx = mw / WORLD_W
    sy = mh / WORLD_H

    cx = mx + int(cam_x * sx)
    cy = my + int(cam_y * sy)
    pygame.draw.rect(surf, fg, (cx, cy,
                                int(WIDTH * sx), int(HEIGHT * sy)), 1)

    for e in enemies:
        px = mx + int(e.x * sx)
        py = my + int(e.y * sy)
        pygame.draw.circle(surf, fg, (px, py), 1)

    px = mx + int(player.x * sx)
    py = my + int(player.y * sy)
    pygame.draw.circle(surf, fg, (px, py), 2)


# --------------------------------------------------------------------------
def main():
    player, enemies, state, spawn_cooldown = reset_game()
    cam_x, cam_y = initial_cam(player)
    running = True

    while running:
        clock.tick(FPS)

        # ---------------- events ------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif state != 'play' and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    player, enemies, state, spawn_cooldown = reset_game()
                    cam_x, cam_y = initial_cam(player)

        # ---------------- update ------------------------------------------
        if state == 'play':
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.vx -= PLAYER_ACCEL
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.vx += PLAYER_ACCEL
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                player.vy -= PLAYER_ACCEL
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                player.vy += PLAYER_ACCEL
            player.physics()

            for e in enemies:
                e.update_ai(player)

            all_c = [player] + enemies
            for i, c1 in enumerate(all_c):
                if not c1.alive:
                    continue
                for c2 in all_c[i + 1:]:
                    if not c2.alive:
                        continue
                    dx = c1.x - c2.x
                    dy = c1.y - c2.y
                    dist = math.hypot(dx, dy)
                    if dist < (c1.size + c2.size) * 0.7:
                        if c1.size > c2.size * 1.15:
                            c2.alive = False
                            grow(c1)
                        elif c2.size > c1.size * 1.15:
                            c1.alive = False
                            grow(c2)
                        else:
                            if dist > 0.001:
                                nx, ny = dx / dist, dy / dist
                                c1.vx += nx * 1.4
                                c1.vy += ny * 1.4
                                c2.vx -= nx * 1.4
                                c2.vy -= ny * 1.4
                    if not c1.alive:
                        break

            enemies = [e for e in enemies if e.alive]

            if not player.alive:
                state = 'lose'
            elif player.level >= 10 and player.sublevel >= 5:
                state = 'win'

            spawn_cooldown -= 1
            if spawn_cooldown <= 0 and len(enemies) < 14:
                smalls = [e for e in enemies if e.size < player.size * 0.85]
                bigs   = [e for e in enemies if e.size > player.size * 1.15]
                if len(smalls) < 4:
                    mode = 'small'
                elif len(bigs) < 3:
                    mode = 'big'
                else:
                    mode = 'any'
                e = spawn_enemy(player, mode)
                if e:
                    enemies.append(e)
                spawn_cooldown = random.randint(10, 30)

            # ---------- retro camera: dead-zone + fixed-step snap ----------
            sx = player.x - cam_x
            sy = player.y - cam_y
            target_x = cam_x
            target_y = cam_y
            if sx < DEAD_L:
                target_x = int(round(player.x - DEAD_L))
            elif sx > DEAD_R:
                target_x = int(round(player.x - DEAD_R))
            if sy < DEAD_T:
                target_y = int(round(player.y - DEAD_T))
            elif sy > DEAD_B:
                target_y = int(round(player.y - DEAD_B))

            target_x = max(0, min(WORLD_W - WIDTH,  target_x))
            target_y = max(0, min(WORLD_H - HEIGHT, target_y))

            # snap in fixed integer steps (visible jumps like old DOS games)
            if target_x > cam_x:
                cam_x = min(target_x, cam_x + CAM_STEP)
            elif target_x < cam_x:
                cam_x = max(target_x, cam_x - CAM_STEP)
            if target_y > cam_y:
                cam_y = min(target_y, cam_y + CAM_STEP)
            elif target_y < cam_y:
                cam_y = max(target_y, cam_y - CAM_STEP)

        # ---------------- draw --------------------------------------------
        lv_idx = min(max(player.level - 1, 0), 9)
        bg = LEVELS[lv_idx]['bg']
        fg = LEVELS[lv_idx]['fg']

        screen.fill(bg)

        # world border
        pygame.draw.rect(screen, fg,
                         (-cam_x, -cam_y, WORLD_W, WORLD_H), 1)

        for e in enemies:
            if (e.x - cam_x < -e.size - 20 or e.x - cam_x > WIDTH  + e.size + 20 or
                e.y - cam_y < -e.size - 20 or e.y - cam_y > HEIGHT + e.size + 20):
                continue
            draw_creature(screen, e, fg, 1, cam_x, cam_y)
            if e.flash > 0:
                pygame.draw.circle(
                    screen, fg,
                    (int(e.x - cam_x), int(e.y - cam_y)),
                    int(e.size + (8 - e.flash) * 3), 1)

        if player.alive:
            draw_creature(screen, player, fg, 2, cam_x, cam_y)
            pygame.draw.circle(screen, fg,
                               (int(player.x - cam_x),
                                int(player.y - cam_y)), 2)

        # HUD (no anti-aliasing for crisp pixel font look)
        score = player.sublevel + (player.level - 1) * 5
        hud = "LEVEL {}/10   SUBLEVEL {}/5   SCORE {}".format(
            player.level, player.sublevel, score)
        screen.blit(small_font.render(hud, False, fg), (12, 10))
        screen.blit(small_font.render("WASD / ARROWS - move    ESC - quit",
                                      False, fg), (12, HEIGHT - 24))

        draw_minimap(screen, player, enemies, cam_x, cam_y, fg)

        if state == 'win':
            big = big_font.render("WINNER!", False, fg)
            screen.blit(big, (WIDTH // 2 - big.get_width() // 2,
                              HEIGHT // 2 - 70))
            sub = font.render("Press ENTER to play again", False, fg)
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2,
                              HEIGHT // 2 + 20))
        elif state == 'lose':
            big = big_font.render("GAME OVER", False, fg)
            screen.blit(big, (WIDTH // 2 - big.get_width() // 2,
                              HEIGHT // 2 - 70))
            sub = font.render("Press ENTER to try again", False, fg)
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2,
                              HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
