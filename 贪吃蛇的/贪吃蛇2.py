import turtle
import time
import random
from dataclasses import dataclass

# ---------------------------
# 配置
# ---------------------------
WIDTH, HEIGHT = 700, 700
GRID = 20

# 难度：数值越小越快
DIFFICULTY = {
    "Easy": 0.13,
    "Normal": 0.10,
    "Hard": 0.075,
    "Insane": 0.055,
}

# 每吃一次加速（最小不低于 MIN_DELAY）
SPEEDUP = 0.003
MIN_DELAY = 0.045

COL_BG = "#0b0f14"
COL_BORDER = "#2a3340"
COL_TEXT = "#e6edf3"
COL_SNAKE_HEAD = "#7CFF6B"
COL_SNAKE_BODY = "#36C275"
COL_FOOD = "#ff4d6d"

# ---------------------------
# 状态
# ---------------------------
@dataclass
class GameState:
    running: bool = False
    paused: bool = False
    game_over: bool = False

    difficulty_name: str = "Normal"
    delay: float = DIFFICULTY["Normal"]

    score: int = 0
    best: int = 0


state = GameState()

# ---------------------------
# 屏幕
# ---------------------------
wn = turtle.Screen()
wn.title("贪吃蛇 Snake Deluxe (turtle)")
wn.bgcolor(COL_BG)
wn.setup(WIDTH, HEIGHT)
wn.tracer(0)

# ---------------------------
# 画笔工具
# ---------------------------
hud = turtle.Turtle(visible=False)
hud.penup()
hud.color(COL_TEXT)
hud.speed(0)

border = turtle.Turtle(visible=False)
border.penup()
border.color(COL_BORDER)
border.speed(0)

# ---------------------------
# 实体：蛇、食物
# ---------------------------
head = turtle.Turtle()
head.shape("square")
head.color(COL_SNAKE_HEAD)
head.penup()
head.speed(0)
head.direction = "stop"

food = turtle.Turtle()
food.shape("circle")
food.color(COL_FOOD)
food.penup()
food.speed(0)

segments = []

# ---------------------------
# 工具函数
# ---------------------------
def clamp_to_grid(x, y):
    # 保证落在网格上
    x = int(round(x / GRID)) * GRID
    y = int(round(y / GRID)) * GRID
    return x, y

def random_pos():
    margin_x = WIDTH // 2 - 60
    margin_y = HEIGHT // 2 - 110
    x = random.randrange(-margin_x, margin_x + 1, GRID)
    y = random.randrange(-margin_y, margin_y + 1, GRID)
    return x, y

def draw_border():
    border.clear()
    border.goto(-WIDTH // 2 + 20, -HEIGHT // 2 + 60)
    border.pendown()
    border.pensize(3)
    border.setheading(0)
    border.forward(WIDTH - 40)
    border.left(90)
    border.forward(HEIGHT - 110)
    border.left(90)
    border.forward(WIDTH - 40)
    border.left(90)
    border.forward(HEIGHT - 110)
    border.left(90)
    border.penup()

def hud_text(lines, y_top):
    hud.goto(0, y_top)
    hud.write(lines, align="center", font=("Consolas", 16, "normal"))

def update_hud():
    hud.clear()
    top = HEIGHT // 2 - 40
    hud.goto(0, top)
    status = "RUNNING" if state.running else "READY"
    if state.paused:
        status = "PAUSED"
    if state.game_over:
        status = "GAME OVER"

    hud.write(
        f"Score: {state.score}   Best: {state.best}   "
        f"Difficulty: {state.difficulty_name}   Speed: {state.delay:.3f}s   [{status}]",
        align="center",
        font=("Consolas", 14, "normal"),
    )

def show_start_screen():
    hud.clear()
    draw_border()
    update_hud()
    info = (
        "贪吃蛇 Snake Deluxe\n\n"
        "操作：方向键 / WASD\n"
        "空格：开始/暂停   R：重开\n"
        "1~4：切换难度 (Easy/Normal/Hard/Insane)\n\n"
        "按 空格 开始"
    )
    hud.goto(0, 40)
    hud.write(info, align="center", font=("Consolas", 16, "normal"))

def set_difficulty(name):
    if name in DIFFICULTY:
        state.difficulty_name = name
        state.delay = DIFFICULTY[name]
        update_hud()

def reset_entities():
    head.goto(0, 0)
    head.direction = "stop"

    for seg in segments:
        seg.goto(10000, 10000)
    segments.clear()

    food.goto(*random_pos())

def reset_game(keep_best=True):
    if keep_best:
        state.best = max(state.best, state.score)
    state.score = 0
    state.game_over = False
    state.paused = False
    state.running = False
    # 重置速度到当前难度初始值
    state.delay = DIFFICULTY[state.difficulty_name]
    reset_entities()
    show_start_screen()

def add_segment():
    seg = turtle.Turtle()
    seg.shape("square")
    seg.color(COL_SNAKE_BODY)
    seg.penup()
    seg.speed(0)
    segments.append(seg)

def set_direction(new_dir):
    if not state.running or state.paused or state.game_over:
        return
    opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
    if head.direction == "stop":
        head.direction = new_dir
    elif opposite.get(head.direction) != new_dir:
        head.direction = new_dir

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
    head.goto(x, y)

def in_bounds(x, y):
    left = -WIDTH // 2 + 25
    right = WIDTH // 2 - 25
    bottom = -HEIGHT // 2 + 65
    top = HEIGHT // 2 - 55
    return left <= x <= right and bottom <= y <= top

def toggle_start_pause():
    if state.game_over:
        return
    if not state.running:
        state.running = True
        state.paused = False
        update_hud()
        return
    state.paused = not state.paused
    update_hud()

def game_over():
    state.game_over = True
    state.running = False
    state.paused = False
    state.best = max(state.best, state.score)

    update_hud()
    hud.goto(0, 10)
    hud.write("按 R 重新开始", align="center", font=("Consolas", 18, "normal"))

def eat_food():
    state.score += 10
    # 速度逐步加快
    state.delay = max(MIN_DELAY, state.delay - SPEEDUP)
    add_segment()
    food.goto(*random_pos())
    update_hud()

# ---------------------------
# 键盘控制
# ---------------------------
wn.listen()
wn.onkeypress(lambda: set_direction("up"), "Up")
wn.onkeypress(lambda: set_direction("down"), "Down")
wn.onkeypress(lambda: set_direction("left"), "Left")
wn.onkeypress(lambda: set_direction("right"), "Right")

wn.onkeypress(lambda: set_direction("up"), "w")
wn.onkeypress(lambda: set_direction("down"), "s")
wn.onkeypress(lambda: set_direction("left"), "a")
wn.onkeypress(lambda: set_direction("right"), "d")

wn.onkeypress(toggle_start_pause, "space")
wn.onkeypress(lambda: reset_game(keep_best=True), "r")

wn.onkeypress(lambda: set_difficulty("Easy"), "1")
wn.onkeypress(lambda: set_difficulty("Normal"), "2")
wn.onkeypress(lambda: set_difficulty("Hard"), "3")
wn.onkeypress(lambda: set_difficulty("Insane"), "4")

# ---------------------------
# 初始化
# ---------------------------
reset_entities()
show_start_screen()

# ---------------------------
# 主循环
# ---------------------------
while True:
    wn.update()

    if state.running and (not state.paused) and (not state.game_over):
        # 身体跟随
        for i in range(len(segments) - 1, 0, -1):
            segments[i].goto(segments[i - 1].xcor(), segments[i - 1].ycor())
        if segments:
            segments[0].goto(head.xcor(), head.ycor())

        move_head()

        # 撞墙
        if not in_bounds(head.xcor(), head.ycor()):
            game_over()

        # 吃食物
        if head.distance(food) < 15:
            eat_food()

        # 撞自己
        for seg in segments:
            if seg.distance(head) < 10:
                game_over()
                break

    time.sleep(state.delay)