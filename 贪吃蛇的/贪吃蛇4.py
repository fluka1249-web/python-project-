import pygame
import random
import json
import os
from dataclasses import dataclass
from datetime import datetime

# =========================
# 基础配置
# =========================
W, H = 1000, 720
FPS = 60
GRID = 20

SAVE_FILE = "snake_scores.json"

DIFFICULTY = {
    "Easy": 9,     # 每秒移动次数（tick）
    "Normal": 12,
    "Hard": 16,
    "Insane": 20,
}

NEON = {
    "bg": (8, 12, 20),
    "panel": (14, 20, 32),
    "panel2": (18, 26, 40),
    "stroke": (40, 60, 90),
    "text": (226, 237, 243),
    "muted": (150, 170, 190),

    "neon_cyan": (0, 240, 255),
    "neon_green": (120, 255, 120),
    "neon_pink": (255, 70, 160),
    "neon_yellow": (255, 210, 90),
    "danger": (255, 80, 80),
}

LEVEL_STEP = 60
MAX_LEVEL = 10
POWERUP_T = 6.0


# =========================
# 存档：Top10 + settings
# =========================
def load_save():
    if not os.path.exists(SAVE_FILE):
        return {"best": 0, "top": [], "settings": {}}
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("best", 0)
        d.setdefault("top", [])
        d.setdefault("settings", {})
        return d
    except Exception:
        return {"best": 0, "top": [], "settings": {}}


def save_save(d):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_top_score(score):
    d = load_save()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d["top"].append({"score": int(score), "time": now})
    d["top"].sort(key=lambda x: x["score"], reverse=True)
    d["top"] = d["top"][:10]
    d["best"] = max(int(d.get("best", 0)), int(score))
    save_save(d)


def clear_top():
    d = load_save()
    d["top"] = []
    save_save(d)


# =========================
# UI：绘制辅助
# =========================
def draw_glow_rect(surf, rect, color, radius=14, glow=10, alpha=80):
    x, y, w, h = rect
    for i in range(glow, 0, -2):
        r = pygame.Rect(x - i, y - i, w + 2 * i, h + 2 * i)
        c = (*color, max(0, alpha - i * 6))
        tmp = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(tmp, c, tmp.get_rect(), border_radius=radius + i)
        surf.blit(tmp, (r.x, r.y))
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=2)


def draw_card(surf, rect, fill, stroke):
    pygame.draw.rect(surf, fill, rect, border_radius=18)
    pygame.draw.rect(surf, stroke, rect, border_radius=18, width=2)


class Button:
    def __init__(self, rect, text, on_click, accent=NEON["neon_cyan"]):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.accent = accent
        self.hover = False

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.on_click()

    def draw(self, surf, font):
        fill = NEON["panel2"] if self.hover else NEON["panel"]
        draw_card(surf, self.rect, fill, self.accent if self.hover else NEON["stroke"])
        draw_glow_rect(surf, self.rect, self.accent if self.hover else NEON["stroke"],
                       glow=10 if self.hover else 6, alpha=90)
        label = font.render(self.text, True, NEON["text"])
        surf.blit(label, label.get_rect(center=self.rect.center))


class Toggle:
    def __init__(self, rect, label, getv, setv, accent=NEON["neon_green"]):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.getv = getv
        self.setv = setv
        self.accent = accent
        self.hover = False

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.setv(not self.getv())

    def draw(self, surf, small):
        draw_card(surf, self.rect, NEON["panel"], NEON["stroke"])
        lab = small.render(self.label, True, NEON["muted"])
        surf.blit(lab, (self.rect.x + 16, self.rect.y + 17))

        v = self.getv()
        track = pygame.Rect(self.rect.right - 84, self.rect.y + 14, 64, 26)
        pygame.draw.rect(surf, (30, 40, 58), track, border_radius=13)
        pygame.draw.rect(surf, self.accent if v else (90, 100, 120), track, border_radius=13, width=2)

        knob_center = (track.right - 13, track.centery) if v else (track.left + 13, track.centery)
        pygame.draw.circle(surf, self.accent if v else (170, 180, 200), knob_center, 11)


class Segmented:
    def __init__(self, rect, label, options, getv, setv, accent=NEON["neon_cyan"]):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.options = options
        self.getv = getv
        self.setv = setv
        self.accent = accent
        self.hover_index = None

    def _option_rects(self):
        base = pygame.Rect(self.rect)
        base.x += 210
        base.w -= 220
        n = len(self.options)
        w = (base.w - (n - 1) * 8) // n
        rects = []
        x = base.x
        for _ in range(n):
            rects.append(pygame.Rect(x, base.y + 10, w, base.h - 20))
            x += w + 8
        return rects

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover_index = None
            for i, r in enumerate(self._option_rects()):
                if r.collidepoint(e.pos):
                    self.hover_index = i
                    break
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._option_rects()):
                if r.collidepoint(e.pos):
                    self.setv(self.options[i])
                    break

    def draw(self, surf, small):
        draw_card(surf, self.rect, NEON["panel"], NEON["stroke"])
        lab = small.render(self.label, True, NEON["muted"])
        surf.blit(lab, (self.rect.x + 16, self.rect.y + 17))

        current = self.getv()
        for i, (opt, r) in enumerate(zip(self.options, self._option_rects())):
            active = (opt == current)
            hover = (self.hover_index == i)
            fill = (24, 34, 52) if not (active or hover) else (32, 48, 72)
            stroke = self.accent if active else (NEON["stroke"] if not hover else self.accent)
            pygame.draw.rect(surf, fill, r, border_radius=12)
            pygame.draw.rect(surf, stroke, r, border_radius=12, width=2)
            txt = small.render(opt, True, NEON["text"] if active else NEON["muted"])
            surf.blit(txt, txt.get_rect(center=r.center))


# =========================
# 游戏状态结构
# =========================
@dataclass
class Settings:
    difficulty: str = "Normal"
    wrap: bool = False
    obstacles: bool = True
    sound: bool = True
    level_mode: bool = True


@dataclass
class Buffs:
    inv_until: float = 0.0
    slow_until: float = 0.0
    wrap_until: float = 0.0
    double_until: float = 0.0


# =========================
# 游戏核心
# =========================
class SnakeGame:
    def __init__(self, settings: Settings, best=0):
        self.settings = settings
        self.best = best
        self.reset()

    def reset(self):
        self.score = 0
        self.level = 1
        self.tick_rate = float(DIFFICULTY[self.settings.difficulty])
        self.accum = 0.0
        self.running = False
        self.paused = False
        self.game_over = False

        self.buffs = Buffs()

        self.play = pygame.Rect(280, 90, W - 320, H - 130)

        cx = self.play.x + (self.play.w // 2 // GRID) * GRID
        cy = self.play.y + (self.play.h // 2 // GRID) * GRID
        self.dir = (0, 0)
        self.snake = [(cx, cy)]
        self.grow = 0

        self.obstacles = set()
        self.food = self.rand_cell(avoid=set(self.snake))
        if self.settings.obstacles:
            self.rebuild_obstacles()

        self.powerup = None  # (kind, (x,y))

    def now(self):
        return pygame.time.get_ticks() / 1000.0

    def buff_active(self, name):
        t = self.now()
        b = self.buffs
        return {
            "inv": t < b.inv_until,
            "slow": t < b.slow_until,
            "wrap": t < b.wrap_until,
            "double": t < b.double_until,
        }.get(name, False)

    def effective_wrap(self):
        return self.settings.wrap or self.buff_active("wrap")

    def effective_tick(self):
        base = self.tick_rate
        if self.buff_active("slow"):
            base = max(6.0, base - 5.0)
        return base

    def rand_cell(self, avoid=set()):
        for _ in range(2000):
            x = random.randrange(self.play.x, self.play.right, GRID)
            y = random.randrange(self.play.y, self.play.bottom, GRID)
            x = (x // GRID) * GRID
            y = (y // GRID) * GRID
            if (x, y) not in avoid:
                return (x, y)
        return (self.play.x, self.play.y)

    def rebuild_obstacles(self):
        self.obstacles.clear()
        count = 12 + (self.level - 1) * 3
        avoid = set(self.snake) | {self.food}
        for _ in range(count * 12):
            if len(self.obstacles) >= count:
                break
            c = self.rand_cell(avoid=avoid | self.obstacles)
            if abs(c[0] - self.snake[0][0]) <= GRID * 2 and abs(c[1] - self.snake[0][1]) <= GRID * 2:
                continue
            self.obstacles.add(c)

    def set_dir(self, dx, dy):
        if not self.running or self.paused or self.game_over:
            return
        if self.dir == (0, 0):
            self.dir = (dx, dy)
            return
        if (dx, dy) == (-self.dir[0], -self.dir[1]):
            return
        self.dir = (dx, dy)

    def start(self):
        self.running = True
        self.paused = False
        self.game_over = False

    def toggle_pause(self):
        if not self.running or self.game_over:
            return
        self.paused = not self.paused

    def spawn_powerup(self):
        if self.powerup is not None:
            return
        p = min(0.20, 0.08 + (self.level - 1) * 0.01)
        if random.random() > p:
            return
        kind = random.choice(["inv", "slow", "wrap", "double", "bonus"])
        avoid = set(self.snake) | {self.food} | self.obstacles
        pos = self.rand_cell(avoid=avoid)
        self.powerup = (kind, pos)

    def apply_powerup(self, kind):
        t = self.now()
        if kind == "inv":
            self.buffs.inv_until = t + POWERUP_T
        elif kind == "slow":
            self.buffs.slow_until = t + POWERUP_T
        elif kind == "wrap":
            self.buffs.wrap_until = t + POWERUP_T
        elif kind == "double":
            self.buffs.double_until = t + POWERUP_T
        elif kind == "bonus":
            self.score += 30 * (2 if self.buff_active("double") else 1)
        self.powerup = None

    def step(self):
        if not self.running or self.paused or self.game_over:
            return
        dx, dy = self.dir
        if (dx, dy) == (0, 0):
            return

        hx, hy = self.snake[0]
        nx, ny = hx + dx * GRID, hy + dy * GRID

        if self.effective_wrap():
            if nx < self.play.x: nx = self.play.right - GRID
            if nx >= self.play.right: nx = self.play.x
            if ny < self.play.y: ny = self.play.bottom - GRID
            if ny >= self.play.bottom: ny = self.play.y

        if not self.effective_wrap():
            if not (self.play.x <= nx < self.play.right and self.play.y <= ny < self.play.bottom):
                if not self.buff_active("inv"):
                    self.game_over = True
                    return

        new_head = (nx, ny)

        if not self.buff_active("inv"):
            if new_head in self.obstacles:
                self.game_over = True
                return
            if new_head in self.snake:
                self.game_over = True
                return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            mult = 2 if self.buff_active("double") else 1
            self.score += 10 * mult
            self.grow += 1

            self.tick_rate = min(26.0, self.tick_rate + 0.35)

            if self.settings.level_mode:
                new_level = min(MAX_LEVEL, 1 + self.score // LEVEL_STEP)
                if new_level != self.level:
                    self.level = new_level
                    if self.settings.obstacles:
                        self.rebuild_obstacles()

            avoid = set(self.snake) | self.obstacles
            self.food = self.rand_cell(avoid=avoid)
        else:
            if self.powerup and new_head == self.powerup[1]:
                self.apply_powerup(self.powerup[0])

            if self.grow > 0:
                self.grow -= 1
            else:
                self.snake.pop()

        self.spawn_powerup()

    def update(self, dt):
        if not self.running or self.paused or self.game_over:
            return
        self.accum += dt
        tick = 1.0 / self.effective_tick()
        while self.accum >= tick:
            self.accum -= tick
            self.step()


# =========================
# App：场景管理
# =========================
class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake // Neon UI (pygame)")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("Consolas", 34, bold=True)
        self.font = pygame.font.SysFont("Consolas", 18)
        self.font_small = pygame.font.SysFont("Consolas", 15)

        data = load_save()
        self.best = int(data.get("best", 0))

        s = data.get("settings", {})
        self.settings = Settings(
            difficulty=s.get("difficulty", "Normal"),
            wrap=bool(s.get("wrap", False)),
            obstacles=bool(s.get("obstacles", True)),
            sound=bool(s.get("sound", True)),
            level_mode=bool(s.get("level_mode", True)),
        )

        self.scene = "menu"  # menu / settings / scores / game
        self.game = SnakeGame(self.settings, best=self.best)
        self.controls = []
        self.build_ui()

    def persist_settings(self):
        d = load_save()
        d["settings"] = {
            "difficulty": self.settings.difficulty,
            "wrap": self.settings.wrap,
            "obstacles": self.settings.obstacles,
            "sound": self.settings.sound,
            "level_mode": self.settings.level_mode,
        }
        d["best"] = max(int(d.get("best", 0)), int(self.best))
        save_save(d)

    def build_ui(self):
        self.controls = []
        if self.scene == "menu":
            self.controls += [
                Button((60, 210, 190, 54), "PLAY", self.play, accent=NEON["neon_cyan"]),
                Button((60, 280, 190, 54), "SETTINGS", self.to_settings, accent=NEON["neon_green"]),
                Button((60, 350, 190, 54), "SCORES", self.to_scores, accent=NEON["neon_pink"]),
                Button((60, 420, 190, 54), "QUIT", self.quit, accent=NEON["danger"]),
            ]
        elif self.scene == "settings":
            self.controls += [
                Segmented((60, 190, 400, 56), "Difficulty", list(DIFFICULTY.keys()),
                          lambda: self.settings.difficulty, self.set_difficulty, accent=NEON["neon_cyan"]),
                Toggle((60, 260, 400, 56), "Wrap walls", lambda: self.settings.wrap, self.set_wrap,
                       accent=NEON["neon_green"]),
                Toggle((60, 330, 400, 56), "Obstacles", lambda: self.settings.obstacles, self.set_obstacles,
                       accent=NEON["neon_yellow"]),
                Toggle((60, 400, 400, 56), "Level mode", lambda: self.settings.level_mode, self.set_level,
                       accent=NEON["neon_pink"]),
                Toggle((60, 470, 400, 56), "Sound", lambda: self.settings.sound, self.set_sound,
                       accent=NEON["neon_cyan"]),
                Button((60, 560, 190, 54), "BACK", self.to_menu, accent=NEON["stroke"]),
            ]
        elif self.scene == "scores":
            self.controls += [
                Button((60, 560, 190, 54), "BACK", self.to_menu, accent=NEON["stroke"]),
                Button((260, 560, 200, 54), "CLEAR TOP10", self.clear_scores, accent=NEON["danger"]),
            ]
        elif self.scene == "game":
            self.controls += [
                Button((60, 600, 190, 46), "MENU (M)", self.to_menu_from_game, accent=NEON["stroke"]),
                Button((260, 600, 190, 46), "RESTART (R)", self.restart, accent=NEON["neon_pink"]),
            ]

    # -------- scene actions --------
    def play(self):
        self.scene = "game"
        self.game = SnakeGame(self.settings, best=self.best)
        self.game.start()
        self.build_ui()

    def restart(self):
        self.game = SnakeGame(self.settings, best=self.best)
        self.game.start()

    def to_menu(self):
        self.scene = "menu"
        self.build_ui()

    def to_settings(self):
        self.scene = "settings"
        self.build_ui()

    def to_scores(self):
        self.scene = "scores"
        self.build_ui()

    def to_menu_from_game(self):
        if self.game.score > 0:
            add_top_score(self.game.score)
            self.best = max(self.best, self.game.score)
        self.scene = "menu"
        self.build_ui()

    def clear_scores(self):
        clear_top()

    def quit(self):
        pygame.quit()
        raise SystemExit

    # -------- settings setters --------
    def set_difficulty(self, v):
        self.settings.difficulty = v
        self.persist_settings()

    def set_wrap(self, v):
        self.settings.wrap = v
        self.persist_settings()

    def set_obstacles(self, v):
        self.settings.obstacles = v
        self.persist_settings()

    def set_sound(self, v):
        self.settings.sound = v
        self.persist_settings()

    def set_level(self, v):
        self.settings.level_mode = v
        self.persist_settings()

    # =========================
    # 绘制
    # =========================
    def draw_background(self):
        self.screen.fill(NEON["bg"])

        panel = pygame.Rect(30, 30, 240, H - 60)
        draw_card(self.screen, panel, NEON["panel"], NEON["stroke"])
        draw_glow_rect(self.screen, panel, NEON["stroke"], glow=8, alpha=70)

        main = pygame.Rect(300, 30, W - 330, H - 60)
        draw_card(self.screen, main, (10, 16, 26), NEON["stroke"])
        draw_glow_rect(self.screen, main, NEON["stroke"], glow=8, alpha=60)

        hud = pygame.Rect(320, 50, W - 370, 52)
        pygame.draw.rect(self.screen, NEON["panel"], hud, border_radius=16)
        pygame.draw.rect(self.screen, NEON["stroke"], hud, border_radius=16, width=2)

    def draw_title(self):
        title = self.font_big.render("SNAKE // NEON", True, NEON["neon_cyan"])
        self.screen.blit(title, (60, 70))
        sub = self.font_small.render("Cyber UI • Buttons • Toggles • Top10 Save", True, NEON["muted"])
        self.screen.blit(sub, (60, 112))

        best = self.font.render(f"Best: {self.best}", True, NEON["text"])
        self.screen.blit(best, (60, 150))

        hint = self.font_small.render("Keys: Space Pause | R Restart | M Menu | WASD/Arrows Move", True, NEON["muted"])
        self.screen.blit(hint, (60, H - 90))

    def draw_controls(self):
        for c in self.controls:
            if isinstance(c, Button):
                c.draw(self.screen, self.font)
            else:
                c.draw(self.screen, self.font_small)

    def draw_menu(self):
        x0, y0 = 340, 130
        header = self.font_big.render("MAIN MENU", True, NEON["text"])
        self.screen.blit(header, (x0, y0))

        info = [
            "• Neon UI with hover/glow buttons",
            "• Settings page with toggles",
            "• Top10 leaderboard saved locally",
            "• Power-ups + Level mode + Obstacles",
        ]
        for i, line in enumerate(info):
            t = self.font.render(line, True, NEON["muted"])
            self.screen.blit(t, (x0, y0 + 60 + i * 26))

        tip = self.font.render("Click PLAY to start.", True, NEON["neon_pink"])
        self.screen.blit(tip, (x0, y0 + 200))

        hud = pygame.Rect(320, 50, W - 370, 52)
        status = self.font.render("Ready", True, NEON["text"])
        self.screen.blit(status, (hud.x + 18, hud.y + 15))

    def draw_settings(self):
        x0, y0 = 340, 130
        header = self.font_big.render("SETTINGS", True, NEON["text"])
        self.screen.blit(header, (x0, y0))
        t = self.font.render("All changes are saved locally.", True, NEON["muted"])
        self.screen.blit(t, (x0, y0 + 54))

        hud = pygame.Rect(320, 50, W - 370, 52)
        status = self.font.render("Settings", True, NEON["text"])
        self.screen.blit(status, (hud.x + 18, hud.y + 15))

    def draw_scores(self):
        x0, y0 = 340, 130
        header = self.font_big.render("TOP 10 SCORES", True, NEON["text"])
        self.screen.blit(header, (x0, y0))

        d = load_save()
        top = d.get("top", [])

        box = pygame.Rect(340, 200, W - 390, 320)
        draw_card(self.screen, box, NEON["panel"], NEON["stroke"])
        draw_glow_rect(self.screen, box, NEON["stroke"], glow=6, alpha=60)

        if not top:
            t = self.font.render("(No scores yet)", True, NEON["muted"])
            self.screen.blit(t, (box.x + 20, box.y + 30))
        else:
            for i, item in enumerate(top[:10], 1):
                line = f"{i:>2}.  {item.get('score', 0):>4}   {item.get('time', '')}"
                t = self.font.render(line, True, NEON["text"] if i <= 3 else NEON["muted"])
                self.screen.blit(t, (box.x + 20, box.y + 20 + (i - 1) * 28))

        hud = pygame.Rect(320, 50, W - 370, 52)
        status = self.font.render("Leaderboard", True, NEON["text"])
        self.screen.blit(status, (hud.x + 18, hud.y + 15))

    def draw_game(self):
        # 顶部 HUD
        hud = pygame.Rect(320, 50, W - 370, 52)
        score = self.font.render(f"Score: {self.game.score}", True, NEON["text"])
        best = self.font.render(f"Best: {self.best}", True, NEON["muted"])
        diff = self.font.render(f"Diff: {self.settings.difficulty}", True, NEON["muted"])
        level = self.font.render(f"Level: {self.game.level}", True, NEON["muted"])
        self.screen.blit(score, (hud.x + 18, hud.y + 15))
        self.screen.blit(best, (hud.x + 170, hud.y + 15))
        self.screen.blit(diff, (hud.x + 320, hud.y + 15))
        self.screen.blit(level, (hud.x + 520, hud.y + 15))

        # Buff 显示
        buffs = []
        if self.game.buff_active("inv"): buffs.append("INV")
        if self.game.buff_active("slow"): buffs.append("SLOW")
        if self.game.buff_active("wrap"): buffs.append("WRAP")
        if self.game.buff_active("double"): buffs.append("x2")
        if buffs:
            btxt = self.font.render("Buffs: " + ",".join(buffs), True, NEON["neon_pink"])
            self.screen.blit(btxt, (hud.x + 650, hud.y + 15))

        # 玩法区域
        play = self.game.play
        pygame.draw.rect(self.screen, (10, 16, 26), play, border_radius=18)
        pygame.draw.rect(self.screen, NEON["stroke"], play, border_radius=18, width=2)
        draw_glow_rect(self.screen, play, NEON["stroke"], glow=6, alpha=50)

        # 网格弱化线（更精致）
        for x in range(play.x, play.right, GRID * 2):
            pygame.draw.line(self.screen, (14, 22, 34), (x, play.y), (x, play.bottom), 1)
        for y in range(play.y, play.bottom, GRID * 2):
            pygame.draw.line(self.screen, (14, 22, 34), (play.x, y), (play.right, y), 1)

        # 障碍
        if self.settings.obstacles:
            for (ox, oy) in self.game.obstacles:
                r = pygame.Rect(ox, oy, GRID, GRID)
                pygame.draw.rect(self.screen, NEON["neon_yellow"], r, border_radius=6)
                pygame.draw.rect(self.screen, (40, 30, 10), r, width=2, border_radius=6)

        # 食物（发光）
        fx, fy = self.game.food
        fr = pygame.Rect(fx, fy, GRID, GRID)
        draw_glow_rect(self.screen, fr, NEON["neon_pink"], radius=10, glow=10, alpha=90)
        pygame.draw.rect(self.screen, NEON["neon_pink"], fr, border_radius=10)

        # 道具
        if self.game.powerup:
            kind, (px, py) = self.game.powerup
            pr = pygame.Rect(px, py, GRID, GRID)
            col = NEON["neon_cyan"] if kind in ("inv", "wrap") else (NEON["neon_green"] if kind == "slow" else NEON["neon_pink"])
            draw_glow_rect(self.screen, pr, col, radius=10, glow=10, alpha=90)
            pygame.draw.rect(self.screen, col, pr, border_radius=10)

        # 蛇
        for i, (sx, sy) in enumerate(self.game.snake):
            r = pygame.Rect(sx, sy, GRID, GRID)
            if i == 0:
                col = NEON["neon_green"]
                draw_glow_rect(self.screen, r, col, radius=10, glow=12, alpha=90)
                pygame.draw.rect(self.screen, col, r, border_radius=10)
            else:
                col = (40, 160, 140)
                pygame.draw.rect(self.screen, col, r, border_radius=8)

        # 暂停遮罩
        if self.game.paused:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
            t = self.font_big.render("PAUSED", True, NEON["text"])
            self.screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 30)))
            hint = self.font.render("Press Space to resume", True, NEON["muted"])
            self.screen.blit(hint, hint.get_rect(center=(W // 2, H // 2 + 20)))

        # Game Over
        if self.game.game_over:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))
            t = self.font_big.render("GAME OVER", True, NEON["danger"])
            self.screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 40)))
            hint = self.font.render("R: Restart   M: Menu", True, NEON["text"])
            self.screen.blit(hint, hint.get_rect(center=(W // 2, H // 2 + 10)))

    # =========================
    # 事件循环
    # =========================
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()

            # 控件处理
            for c in self.controls:
                c.handle(e)

            # 键盘
            if e.type == pygame.KEYDOWN:
                if self.scene == "game":
                    if e.key in (pygame.K_UP, pygame.K_w):
                        self.game.set_dir(0, -1)
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        self.game.set_dir(0, 1)
                    elif e.key in (pygame.K_LEFT, pygame.K_a):
                        self.game.set_dir(-1, 0)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        self.game.set_dir(1, 0)
                    elif e.key == pygame.K_SPACE:
                        if not self.game.running:
                            self.game.start()
                        else:
                            self.game.toggle_pause()
                    elif e.key == pygame.K_r:
                        self.restart()
                    elif e.key == pygame.K_m:
                        self.to_menu_from_game()

    def update(self, dt):
        if self.scene == "game":
            self.game.update(dt)
            if self.game.game_over:
                # 记录分数一次
                if self.game.score > 0:
                    add_top_score(self.game.score)
                    self.best = max(self.best, self.game.score)
                    self.game.score = 0  # 防止重复写（简化处理）
        # 其他场景无需 update

    def render(self):
        self.draw_background()
        self.draw_title()
        self.draw_controls()

        if self.scene == "menu":
            self.draw_menu()
        elif self.scene == "settings":
            self.draw_settings()
        elif self.scene == "scores":
            self.draw_scores()
        elif self.scene == "game":
            self.draw_game()

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()


if __name__ == "__main__":
    App().run()