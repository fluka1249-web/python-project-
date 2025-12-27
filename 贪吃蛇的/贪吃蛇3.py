import turtle
import time
import random
import json
import os
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------
# 基础配置
# ---------------------------
WIDTH, HEIGHT = 860, 760
GRID = 20

# HUD/边框留白
HUD_TOP_PAD = 55
PLAY_BOTTOM_PAD = 70
PLAY_SIDE_PAD = 30

SAVE_FILE = "snake_scores.json"

DIFFICULTY = {
    "Easy": 0.13,
    "Normal": 0.10,
    "Hard": 0.075,
    "Insane": 0.055,
}
MIN_DELAY = 0.040

# 每次吃到食物加速
SPEEDUP = 0.0025

# 关卡模式：每到这些分数升级（速度更快、障碍更多、道具更频繁）
LEVEL_SCORE_STEP = 50
MAX_LEVEL = 10

# 道具持续时间（秒）
POWERUP_DURATION = 6.0

# ---------------------------
# 皮肤（可扩展）
# ---------------------------
DEFAULT_SKINS = [
    {
        "name": "Neon",
        "bg": "#0b0f14",
        "border": "#2a3340",
        "text": "#e6edf3",
        "head": "#7CFF6B",
        "body": "#36C275",
        "food": "#ff4d6d",
        "obstacle": "#ffd166",
        "powerup": "#8a5cff",
        "button": "#1f2a37",
        "button_hover": "#334155",
    },
    {
        "name": "Ocean",
        "bg": "#071827",
        "border": "#1f3a52",
        "text": "#e6edf3",
        "head": "#00d9ff",
        "body": "#00a6c8",
        "food": "#ff6b6b",
        "obstacle": "#fcca46",
        "powerup": "#a78bfa",
        "button": "#153046",
        "button_hover": "#1f4b6b",
    },
    {
        "name": "Classic",
        "bg": "black",
        "border": "gray30",
        "text": "white",
        "head": "lime",
        "body": "green",
        "food": "red",
        "obstacle": "yellow",
        "powerup": "magenta",
        "button": "gray20",
        "button_hover": "gray35",
    },
]

# ---------------------------
# 声音（可选）
# ---------------------------
def beep(freq=900, dur=70):
    if not state.sound:
        return
    try:
        import winsound
        winsound.Beep(int(freq), int(dur))
    except Exception:
        # 非 Windows 或失败：尽量不报错
        try:
            print("\a", end="")
        except Exception:
            pass

# ---------------------------
# 持久化（排行榜/最高分/设置）
# ---------------------------
def load_save():
    if not os.path.exists(SAVE_FILE):
        return {"best": 0, "top": [], "settings": {}}
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "top" not in data:
            data["top"] = []
        if "best" not in data:
            data["best"] = 0
        if "settings" not in data:
            data["settings"] = {}
        return data
    except Exception:
        return {"best": 0, "top": [], "settings": {}}

def save_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_score_to_top(score: int):
    data = load_save()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["top"].append({"score": int(score), "time": now})
    data["top"].sort(key=lambda x: x["score"], reverse=True)
    data["top"] = data["top"][:10]
    data["best"] = max(int(data.get("best", 0)), int(score))
    save_save(data)

def clear_top():
    data = load_save()
    data["top"] = []
    save_save(data)

# ---------------------------
# 游戏状态
# ---------------------------
@dataclass
class State:
    # 运行状态
    running: bool = False
    paused: bool = False
    game_over: bool = False

    # 菜单/界面
    show_menu: bool = True
    show_scores: bool = False
    show_settings: bool = False

    # 难度/速度/关卡
    difficulty_name: str = "Normal"
    base_delay: float = DIFFICULTY["Normal"]
    delay: float = DIFFICULTY["Normal"]
    level_mode: bool = True
    level: int = 1

    # 分数
    score: int = 0
    best: int = 0

    # 可切换功能
    wrap_walls: bool = False
    obstacles: bool = True
    moving_obstacles: bool = True
    sound: bool = True

    # 皮肤
    skins: list = field(default_factory=lambda: list(DEFAULT_SKINS))
    skin_index: int = 0

    # 自定义颜色（覆盖当前皮肤部分字段；空表示不用）
    custom_colors: dict = field(default_factory=dict)

    # 道具（buff）
    invincible_until: float = 0.0      # 无敌（撞墙/撞障碍/撞自己都不死）
    slow_until: float = 0.0            # 临时减速
    wrap_until: float = 0.0            # 临时穿墙
    double_until: float = 0.0          # 双倍得分

state = State()

# 载入 best & settings
save_data = load_save()
state.best = int(save_data.get("best", 0))
settings = save_data.get("settings", {})
state.difficulty_name = settings.get("difficulty_name", state.difficulty_name)
state.base_delay = float(DIFFICULTY.get(state.difficulty_name, DIFFICULTY["Normal"]))
state.delay = state.base_delay
state.wrap_walls = bool(settings.get("wrap_walls", state.wrap_walls))
state.obstacles = bool(settings.get("obstacles", state.obstacles))
state.moving_obstacles = bool(settings.get("moving_obstacles", state.moving_obstacles))
state.sound = bool(settings.get("sound", state.sound))
state.level_mode = bool(settings.get("level_mode", state.level_mode))
state.skin_index = int(settings.get("skin_index", state.skin_index))
state.custom_colors = dict(settings.get("custom_colors", {}))

def persist_settings():
    data = load_save()
    data["settings"] = {
        "difficulty_name": state.difficulty_name,
        "wrap_walls": state.wrap_walls,
        "obstacles": state.obstacles,
        "moving_obstacles": state.moving_obstacles,
        "sound": state.sound,
        "level_mode": state.level_mode,
        "skin_index": state.skin_index,
        "custom_colors": state.custom_colors,
    }
    data["best"] = max(int(data.get("best", 0)), int(state.best))
    save_save(data)

# ---------------------------
# turtle 初始化
# ---------------------------
wn = turtle.Screen()
wn.title("Snake Deluxe Ultimate (turtle)")
wn.setup(WIDTH, HEIGHT)
wn.tracer(0)

hud = turtle.Turtle(visible=False)
hud.penup()
hud.speed(0)

border = turtle.Turtle(visible=False)
border.penup()
border.speed(0)

ui = turtle.Turtle(visible=False)
ui.penup()
ui.speed(0)

# 实体
head = turtle.Turtle()
head.shape("square")
head.penup()
head.speed(0)
head.direction = "stop"

food = turtle.Turtle()
food.shape("circle")
food.penup()
food.speed(0)

# 道具（单个掉落）
powerup = turtle.Turtle(visible=False)
powerup.shape("triangle")
powerup.penup()
powerup.speed(0)
powerup.kind = None  # type: ignore[attr-defined]

segments = []

# 障碍物：静态格子 + 移动障碍（龟）
obstacle_cells = set()
obstacle_turtles = []
moving_obs = []  # list of dict: {"t": turtle, "dx": int, "dy": int}

# UI 按钮区域
buttons = []  # each: {"x1","y1","x2","y2","label","action","hover"}

# ---------------------------
# 颜色/皮肤
# ---------------------------
def skin():
    base = state.skins[state.skin_index % len(state.skins)]
    if not state.custom_colors:
        return base
    merged = dict(base)
    merged.update(state.custom_colors)
    merged["name"] = base.get("name", "Skin") + " (Custom)"
    return merged

def apply_skin():
    s = skin()
    wn.bgcolor(s["bg"])
    hud.color(s["text"])
    border.color(s["border"])
    ui.color(s["text"])
    head.color(s["head"])
    food.color(s["food"])
    powerup.color(s.get("powerup", "magenta"))
    for seg in segments:
        seg.color(s["body"])
    for o in obstacle_turtles:
        o.color(s["obstacle"])
    for mo in moving_obs:
        mo["t"].color(s["obstacle"])

# ---------------------------
# 坐标/边界
# ---------------------------
def play_bounds():
    left = -WIDTH // 2 + PLAY_SIDE_PAD
    right = WIDTH // 2 - PLAY_SIDE_PAD
    bottom = -HEIGHT // 2 + PLAY_BOTTOM_PAD
    top = HEIGHT // 2 - HUD_TOP_PAD
    return left, right, bottom, top

def in_play_bounds(x, y):
    left, right, bottom, top = play_bounds()
    return left <= x <= right and bottom <= y <= top

def wrap_position(x, y):
    left, right, bottom, top = play_bounds()
    if x > right:
        x = left
    elif x < left:
        x = right
    if y > top:
        y = bottom
    elif y < bottom:
        y = top
    return x, y

def random_cell():
    left, right, bottom, top = play_bounds()
    x = random.randrange(left // GRID * GRID, right // GRID * GRID + 1, GRID)
    y = random.randrange(bottom // GRID * GRID, top // GRID * GRID + 1, GRID)
    x = int(round(x / GRID)) * GRID
    y = int(round(y / GRID)) * GRID
    return x, y

# ---------------------------
# 绘制与 HUD
# ---------------------------
def draw_border():
    s = skin()
    border.clear()
    border.color(s["border"])
    left, right, bottom, top = play_bounds()
    border.goto(left - 10, bottom - 10)
    border.pendown()
    border.pensize(3)
    border.setheading(0)
    border.forward((right - left) + 20)
    border.left(90)
    border.forward((top - bottom) + 20)
    border.left(90)
    border.forward((right - left) + 20)
    border.left(90)
    border.forward((top - bottom) + 20)
    border.left(90)
    border.penup()

def fmt_onoff(v):
    return "ON" if v else "OFF"

def active_buff(name: str):
    now = time.time()
    if name == "inv":
        return now < state.invincible_until
    if name == "slow":
        return now < state.slow_until
    if name == "wrap":
        return now < state.wrap_until
    if name == "double":
        return now < state.double_until
    return False

def update_hud():
    hud.clear()
    s = skin()
    hud.color(s["text"])
    top_y = HEIGHT // 2 - 25

    status = "MENU"
    if state.game_over:
        status = "GAME OVER"
    elif state.paused:
        status = "PAUSED"
    elif state.running:
        status = "RUNNING"
    else:
        status = "READY"

    buffs = []
    if active_buff("inv"):
        buffs.append("INV")
    if active_buff("slow"):
        buffs.append("SLOW")
    if active_buff("wrap"):
        buffs.append("WRAP")
    if active_buff("double"):
        buffs.append("x2")
    buff_text = (" Buffs: " + ",".join(buffs)) if buffs else ""

    level_text = f" Level: {state.level}/{MAX_LEVEL}" if state.level_mode else ""
    hud.goto(0, top_y)
    hud.write(
        f"Score: {state.score}  Best: {state.best}  "
        f"Difficulty: {state.difficulty_name}  Speed: {state.delay:.3f}s  "
        f"{level_text} [{status}] {buff_text}",
        align="center",
        font=("Consolas", 13, "normal"),
    )

def draw_center_text(text, y=0, size=18):
    ui.clear()
    s = skin()
    ui.color(s["text"])
    ui.goto(0, y)
    ui.write(text, align="center", font=("Consolas", size, "normal"))

# ---------------------------
# UI 按钮（可点击菜单）
# ---------------------------
def clear_buttons():
    buttons.clear()

def draw_button(x, y, w, h, label, action):
    # 记录点击区域（以中心点 x,y 绘制矩形）
    x1, y1 = x - w // 2, y - h // 2
    x2, y2 = x + w // 2, y + h // 2
    buttons.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "action": action})

    s = skin()
    ui.goto(x1, y1)
    ui.pendown()
    ui.pensize(2)
    ui.color(s["button"])
    ui.begin_fill()
    ui.setheading(0)
    ui.forward(w)
    ui.left(90)
    ui.forward(h)
    ui.left(90)
    ui.forward(w)
    ui.left(90)
    ui.forward(h)
    ui.end_fill()
    ui.penup()

    ui.color(s["text"])
    ui.goto(x, y - 10)
    ui.write(label, align="center", font=("Consolas", 14, "normal"))

def point_in_button(x, y, b):
    return b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]

def on_click(x, y):
    # 只有菜单/分数/设置界面响应点击
    if not (state.show_menu or state.show_scores or state.show_settings):
        return
    for b in buttons:
        if point_in_button(x, y, b):
            try:
                b["action"]()
            except Exception:
                pass
            break

wn.onscreenclick(on_click)

# ---------------------------
# 障碍物（静态 + 移动）
# ---------------------------
def clear_obstacles():
    obstacle_cells.clear()
    for t in obstacle_turtles:
        t.goto(10000, 10000)
    obstacle_turtles.clear()
    for mo in moving_obs:
        mo["t"].goto(10000, 10000)
    moving_obs.clear()

def generate_static_obstacles(count):
    if not state.obstacles:
        return
    tries = 0
    while len(obstacle_cells) < count and tries < 2000:
        tries += 1
        x, y = random_cell()
        cell = (x, y)
        # 避免贴脸
        if abs(x - head.xcor()) <= GRID * 2 and abs(y - head.ycor()) <= GRID * 2:
            continue
        if abs(x - food.xcor()) <= GRID and abs(y - food.ycor()) <= GRID:
            continue
        if cell in obstacle_cells:
            continue
        obstacle_cells.add(cell)

    for (x, y) in obstacle_cells:
        t = turtle.Turtle()
        t.shape("square")
        t.penup()
        t.speed(0)
        t.color(skin()["obstacle"])
        t.goto(x, y)
        obstacle_turtles.append(t)

def generate_moving_obstacles(count):
    if not (state.obstacles and state.moving_obstacles):
        return
    for _ in range(count):
        x, y = random_cell()
        t = turtle.Turtle()
        t.shape("square")
        t.penup()
        t.speed(0)
        t.color(skin()["obstacle"])
        t.goto(x, y)
        dx, dy = random.choice([(GRID, 0), (-GRID, 0), (0, GRID), (0, -GRID)])
        moving_obs.append({"t": t, "dx": dx, "dy": dy})

def move_moving_obstacles():
    if not (state.obstacles and state.moving_obstacles):
        return
    left, right, bottom, top = play_bounds()
    for mo in moving_obs:
        t = mo["t"]
        nx = t.xcor() + mo["dx"]
        ny = t.ycor() + mo["dy"]

        # 撞边反弹（移动障碍不穿墙）
        if nx < left or nx > right:
            mo["dx"] *= -1
            nx = t.xcor() + mo["dx"]
        if ny < bottom or ny > top:
            mo["dy"] *= -1
            ny = t.ycor() + mo["dy"]

        # 不要直接撞到蛇头（简单避让）
        if abs(nx - head.xcor()) < GRID and abs(ny - head.ycor()) < GRID:
            mo["dx"] *= -1
            mo["dy"] *= -1
            nx = t.xcor() + mo["dx"]
            ny = t.ycor() + mo["dy"]

        t.goto(nx, ny)

def obstacle_hit(x, y):
    if (x, y) in obstacle_cells:
        return True
    for mo in moving_obs:
        if mo["t"].xcor() == x and mo["t"].ycor() == y:
            return True
    return False

# ---------------------------
# 道具系统
# ---------------------------
POWERUPS = [
    ("INVINCIBLE", "inv"),  # 无敌
    ("SLOW", "slow"),       # 减速
    ("WRAP", "wrap"),       # 临时穿墙
    ("DOUBLE", "double"),   # 双倍得分
    ("BONUS", "bonus"),     # 直接加分
]

def hide_powerup():
    powerup.hideturtle()
    powerup.kind = None  # type: ignore[attr-defined]

def maybe_spawn_powerup():
    # 概率随关卡提升
    if powerup.isvisible():
        return
    base = 0.08  # 基础概率
    p = base + (state.level - 1) * 0.01
    if random.random() > min(0.20, p):
        return

    kind_name, kind_code = random.choice(POWERUPS)
    x, y = random_cell()

    # 避开障碍/蛇
    if obstacle_hit(x, y):
        return
    if head.distance((x, y)) < GRID * 2:
        return
    for seg in segments:
        if seg.distance((x, y)) < 1:
            return

    powerup.kind = kind_code  # type: ignore[attr-defined]
    powerup.goto(x, y)
    powerup.showturtle()

def apply_powerup(kind):
    now = time.time()
    if kind == "inv":
        state.invincible_until = now + POWERUP_DURATION
        beep(1200, 70)
    elif kind == "slow":
        state.slow_until = now + POWERUP_DURATION
        beep(700, 70)
    elif kind == "wrap":
        state.wrap_until = now + POWERUP_DURATION
        beep(950, 70)
    elif kind == "double":
        state.double_until = now + POWERUP_DURATION
        beep(1050, 70)
    elif kind == "bonus":
        add = 30 if not active_buff("double") else 60
        state.score += add
        beep(1300, 50)
    hide_powerup()
    update_hud()

def current_delay():
    d = state.delay
    if active_buff("slow"):
        d = min(0.16, d + 0.05)
    return max(MIN_DELAY, d)

# ---------------------------
# 蛇/游戏逻辑
# ---------------------------
def clear_snake():
    for seg in segments:
        seg.goto(10000, 10000)
    segments.clear()

def reset_entities():
    head.goto(0, 0)
    head.direction = "stop"
    clear_snake()
    hide_powerup()
    food.goto(*random_cell())
    clear_obstacles()

def recompute_level():
    if not state.level_mode:
        state.level = 1
        return
    state.level = min(MAX_LEVEL, 1 + state.score // LEVEL_SCORE_STEP)

def rebuild_level_features():
    clear_obstacles()
    if not state.obstacles:
        return
    # 障碍数量随关卡增长
    static_count = 10 + (state.level - 1) * 3
    moving_count = 0 if not state.moving_obstacles else max(0, (state.level - 3) // 2)
    generate_static_obstacles(static_count)
    generate_moving_obstacles(moving_count)

def set_difficulty(name):
    if name not in DIFFICULTY:
        return
    state.difficulty_name = name
    state.base_delay = DIFFICULTY[name]
    # 若没开始则直接用基础速度
    if not state.running:
        state.delay = state.base_delay
    persist_settings()
    beep(800, 50)
    show_main_menu()

def set_direction(new_dir):
    if not state.running or state.paused or state.game_over:
        return
    opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
    if head.direction == "stop":
        head.direction = new_dir
    elif opposite.get(head.direction) != new_dir:
        head.direction = new_dir

def add_segment():
    seg = turtle.Turtle()
    seg.shape("square")
    seg.penup()
    seg.speed(0)
    seg.color(skin()["body"])
    segments.append(seg)

def countdown():
    # 3 秒倒计时
    for i in [3, 2, 1]:
        draw_center_text(f"Starting in {i}", y=0, size=24)
        beep(700 + i * 120, 60)
        wn.update()
        time.sleep(0.5)
    ui.clear()

def start_game():
    if state.game_over:
        return
    state.show_menu = False
    state.show_scores = False
    state.show_settings = False

    ui.clear()
    hud.clear()
    draw_border()
    update_hud()
    clear_buttons()

    state.running = True
    state.paused = False
    state.delay = state.base_delay
    recompute_level()
    rebuild_level_features()
    countdown()
    beep(900, 60)

def toggle_pause():
    if not state.running or state.game_over:
        return
    state.paused = not state.paused
    update_hud()
    beep(650 if state.paused else 900, 60)

def game_over():
    state.game_over = True
    state.running = False
    state.paused = False

    state.best = max(state.best, state.score)
    add_score_to_top(state.score)
    state.best = max(state.best, int(load_save().get("best", state.best)))

    update_hud()
    death_animation()
    draw_center_text("GAME OVER\nPress R to Restart\nPress M for Menu", y=20, size=20)
    beep(300, 120)
    beep(220, 140)

def reset_game():
    state.best = max(state.best, state.score)
    persist_settings()

    state.score = 0
    state.game_over = False
    state.paused = False
    state.running = False
    state.delay = state.base_delay
    state.invincible_until = 0
    state.slow_until = 0
    state.wrap_until = 0
    state.double_until = 0
    state.level = 1

    reset_entities()
    apply_skin()
    show_main_menu()

def death_animation():
    # 简单死亡动画：蛇闪烁并散开
    for _ in range(3):
        head.hideturtle()
        wn.update()
        time.sleep(0.08)
        head.showturtle()
        wn.update()
        time.sleep(0.08)
    # 把身体散到边上
    for seg in segments:
        seg.goto(seg.xcor() + random.choice([-1, 1]) * GRID * 3,
                seg.ycor() + random.choice([-1, 1]) * GRID * 3)
    wn.update()
    time.sleep(0.2)

def eat_food():
    mult = 2 if active_buff("double") else 1
    state.score += 10 * mult
    # 吃到食物加速
    state.delay = max(MIN_DELAY, state.delay - SPEEDUP)
    add_segment()

    # 食物重新生成（避开障碍/蛇）
    tries = 0
    while True:
        tries += 1
        x, y = random_cell()
        if obstacle_hit(x, y):
            continue
        ok = True
        if head.distance((x, y)) < GRID * 2:
            ok = False
        for seg in segments:
            if seg.distance((x, y)) < 1:
                ok = False
                break
        if ok or tries > 500:
            food.goto(x, y)
            break

    # 关卡模式：升级后重建障碍
    old_level = state.level
    recompute_level()
    if state.level_mode and state.level != old_level:
        rebuild_level_features()
        beep(1100, 80)

    update_hud()
    beep(1000, 45)

def move_head():
    x, y = head.xcor(), head.ycor()
    if head.direction == "up":
        y += GRID
    elif head.direction == "down":
        y -= GRID
    elif head.direction == "left":
        x -= GRID
    elif head.direction == "right":
        x += GRID

    # 临时穿墙 buff 优先于设置
    wrap = state.wrap_walls or active_buff("wrap")
    if wrap:
        x, y = wrap_position(x, y)

    head.goto(x, y)

def collides_with_self():
    for seg in segments:
        if seg.distance(head) < 10:
            return True
    return False

def collides_with_wall():
    if state.wrap_walls or active_buff("wrap"):
        return False
    return not in_play_bounds(head.xcor(), head.ycor())

def collides_with_obstacles():
    if not state.obstacles:
        return False
    return obstacle_hit(head.xcor(), head.ycor())

def invincible():
    return active_buff("inv")

# ---------------------------
# 菜单：主菜单/排行榜/设置（可点击 + 键盘）
# ---------------------------
def show_main_menu():
    state.show_menu = True
    state.show_scores = False
    state.show_settings = False

    ui.clear()
    hud.clear()
    draw_border()
    update_hud()
    clear_buttons()

    s = skin()
    title = "Snake Deluxe Ultimate"
    subtitle = (
        "Click Buttons or Use Keys\n"
        "Space: Start/Pause   R: Restart   M: Menu\n"
        "Arrows/WASD: Move"
    )
    draw_center_text(title, y=210, size=26)
    ui.goto(0, 170)
    ui.color(s["text"])
    ui.write(subtitle, align="center", font=("Consolas", 14, "normal"))

    # 按钮布局
    bx, by = 0, 90
    draw_button(bx, by, 280, 52, "Start (Space)", start_game)
    draw_button(bx, by - 70, 280, 52, "Scores (Top10)", show_scores_screen)
    draw_button(bx, by - 140, 280, 52, "Settings", show_settings_screen)
    draw_button(bx, by - 210, 280, 52, "Restart (R)", reset_game)

    ui.goto(0, -210)
    ui.write(
        f"Difficulty: {state.difficulty_name} | Level Mode: {fmt_onoff(state.level_mode)} | "
        f"Wrap: {fmt_onoff(state.wrap_walls)} | Obstacles: {fmt_onoff(state.obstacles)} | "
        f"Moving Obs: {fmt_onoff(state.moving_obstacles)} | Sound: {fmt_onoff(state.sound)} | "
        f"Skin: {skin().get('name')}",
        align="center",
        font=("Consolas", 12, "normal"),
    )

def show_scores_screen():
    state.show_menu = False
    state.show_scores = True
    state.show_settings = False

    ui.clear()
    hud.clear()
    draw_border()
    update_hud()
    clear_buttons()

    data = load_save()
    top = data.get("top", [])

    draw_center_text("Top 10 Scores", y=220, size=24)
    lines = []
    for i, item in enumerate(top, 1):
        lines.append(f"{i:>2}. {item.get('score', 0):>4}   {item.get('time', '')}")
    if not lines:
        lines = ["(No scores yet)"]

    ui.goto(0, 150)
    ui.write("\n".join(lines), align="center", font=("Consolas", 14, "normal"))

    draw_button(0, -140, 280, 52, "Back", show_main_menu)
    draw_button(0, -210, 280, 52, "Clear Top10", clear_top_and_refresh)

def clear_top_and_refresh():
    clear_top()
    beep(700, 70)
    show_scores_screen()

def show_settings_screen():
    state.show_menu = False
    state.show_scores = False
    state.show_settings = True

    ui.clear()
    hud.clear()
    draw_border()
    update_hud()
    clear_buttons()

    draw_center_text("Settings", y=240, size=24)

    # 一些设置按钮
    y = 160
    draw_button(0, y, 340, 50, f"Difficulty: {state.difficulty_name} (1-4)", cycle_difficulty)
    y -= 65
    draw_button(0, y, 340, 50, f"Level Mode: {fmt_onoff(state.level_mode)} (L)", toggle_level_mode)
    y -= 65
    draw_button(0, y, 340, 50, f"Wrap Walls: {fmt_onoff(state.wrap_walls)} (T)", toggle_wrap)
    y -= 65
    draw_button(0, y, 340, 50, f"Obstacles: {fmt_onoff(state.obstacles)} (O)", toggle_obstacles)
    y -= 65
    draw_button(0, y, 340, 50, f"Moving Obstacles: {fmt_onoff(state.moving_obstacles)} (V)", toggle_moving_obstacles)
    y -= 65
    draw_button(0, y, 340, 50, f"Sound: {fmt_onoff(state.sound)} (K)", toggle_sound)
    y -= 65
    draw_button(0, y, 340, 50, f"Skin: {skin().get('name')} (P)", next_skin)
    y -= 65
    draw_button(0, y, 340, 50, "Customize Colors (C)", customize_colors)
    y -= 80
    draw_button(0, y, 280, 52, "Back", show_main_menu)

    ui.goto(0, -240)
    ui.write("提示：自定义颜色会覆盖当前皮肤（可随时清空恢复）", align="center", font=("Consolas", 12, "normal"))

def cycle_difficulty():
    keys = list(DIFFICULTY.keys())
    idx = keys.index(state.difficulty_name) if state.difficulty_name in keys else 1
    idx = (idx + 1) % len(keys)
    set_difficulty(keys[idx])
    # 仍在设置页
    show_settings_screen()

def toggle_level_mode():
    state.level_mode = not state.level_mode
    persist_settings()
    beep(750, 50)
    show_settings_screen()

def toggle_wrap():
    state.wrap_walls = not state.wrap_walls
    persist_settings()
    beep(750, 50)
    show_settings_screen()

def toggle_obstacles():
    state.obstacles = not state.obstacles
    persist_settings()
    beep(750, 50)
    # 障碍开关会影响局内布局，回到菜单更直观
    show_settings_screen()

def toggle_moving_obstacles():
    state.moving_obstacles = not state.moving_obstacles
    persist_settings()
    beep(750, 50)
    show_settings_screen()

def toggle_sound():
    state.sound = not state.sound
    persist_settings()
    if state.sound:
        beep(900, 60)
    show_settings_screen()

def next_skin():
    state.skin_index = (state.skin_index + 1) % len(state.skins)
    persist_settings()
    apply_skin()
    beep(880, 50)
    show_settings_screen()

def customize_colors():
    """
    简易自定义：用屏幕 textinput 输入颜色。
    可填：red / #RRGGBB 之类。
    留空=跳过；输入 CLEAR=清空自定义恢复皮肤。
    """
    try:
        s = skin()
        prompt = (
            "输入自定义颜色（示例 #ff00aa 或 red）。\n"
            "留空=跳过；输入 CLEAR=清空自定义。\n\n"
            "你要改哪个？可选键：bg,border,text,head,body,food,obstacle,powerup"
        )
        key = wn.textinput("Customize", prompt)
        if key is None:
            return
        key = key.strip()
        if not key:
            return
        if key.upper() == "CLEAR":
            state.custom_colors = {}
            persist_settings()
            apply_skin()
            show_settings_screen()
            return
        if key not in ["bg","border","text","head","body","food","obstacle","powerup"]:
            return
        val = wn.textinput("Color", f"当前 {key}={s.get(key)}，输入新颜色：")
        if val is None:
            return
        val = val.strip()
        if not val:
            return
        if val.upper() == "CLEAR":
            state.custom_colors = {}
        else:
            state.custom_colors[key] = val
        persist_settings()
        apply_skin()
        show_settings_screen()
    except Exception:
        pass

# ---------------------------
# 键盘绑定
# ---------------------------
wn.listen()

# 移动
wn.onkeypress(lambda: set_direction("up"), "Up")
wn.onkeypress(lambda: set_direction("down"), "Down")
wn.onkeypress(lambda: set_direction("left"), "Left")
wn.onkeypress(lambda: set_direction("right"), "Right")
wn.onkeypress(lambda: set_direction("up"), "w")
wn.onkeypress(lambda: set_direction("down"), "s")
wn.onkeypress(lambda: set_direction("left"), "a")
wn.onkeypress(lambda: set_direction("right"), "d")

# 开始/暂停/菜单/重开
def space_action():
    if state.show_menu or state.show_scores or state.show_settings:
        start_game()
        return
    if not state.running:
        start_game()
    else:
        toggle_pause()

wn.onkeypress(space_action, "space")
wn.onkeypress(show_main_menu, "m")
wn.onkeypress(reset_game, "r")

# 设置快捷键
wn.onkeypress(lambda: set_difficulty("Easy"), "1")
wn.onkeypress(lambda: set_difficulty("Normal"), "2")
wn.onkeypress(lambda: set_difficulty("Hard"), "3")
wn.onkeypress(lambda: set_difficulty("Insane"), "4")

wn.onkeypress(toggle_wrap, "t")
wn.onkeypress(toggle_obstacles, "o")
wn.onkeypress(toggle_moving_obstacles, "v")
wn.onkeypress(toggle_sound, "k")
wn.onkeypress(next_skin, "p")
wn.onkeypress(toggle_level_mode, "l")
wn.onkeypress(customize_colors, "c")

# ---------------------------
# 初始化
# ---------------------------
apply_skin()
reset_entities()
show_main_menu()

# ---------------------------
# 主循环
# ---------------------------
while True:
    wn.update()

    if state.running and (not state.paused) and (not state.game_over):
        # 移动身体：尾跟头
        for i in range(len(segments) - 1, 0, -1):
            segments[i].goto(segments[i - 1].xcor(), segments[i - 1].ycor())
        if segments:
            segments[0].goto(head.xcor(), head.ycor())

        # 移动蛇头
        move_head()

        # 移动障碍
        move_moving_obstacles()

        # 生成道具
        maybe_spawn_powerup()

        # 撞墙/障碍/自己
        if (not invincible()) and collides_with_wall():
            game_over()
        elif (not invincible()) and collides_with_obstacles():
            game_over()
        elif (not invincible()) and collides_with_self():
            game_over()

        # 吃到食物
        if head.distance(food) < 15:
            eat_food()

        # 吃到道具
        if powerup.isvisible() and head.distance(powerup) < 15:
            apply_powerup(powerup.kind)

    time.sleep(current_delay())