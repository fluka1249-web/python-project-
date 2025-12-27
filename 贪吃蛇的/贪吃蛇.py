import turtle
import time
import random

# -----------------------
# 基本设置
# -----------------------
WIDTH, HEIGHT = 600, 600
DELAY = 0.12  # 数值越小，速度越快

wn = turtle.Screen()
wn.title("贪吃蛇 Snake (turtle)")
wn.bgcolor("black")
wn.setup(width=WIDTH, height=HEIGHT)
wn.tracer(0)

# 分数显示
score = 0
best_score = 0

pen = turtle.Turtle()
pen.speed(0)
pen.color("white")
pen.penup()
pen.hideturtle()
pen.goto(0, HEIGHT // 2 - 40)
pen.write("Score: 0  Best: 0", align="center", font=("Consolas", 18, "normal"))

# -----------------------
# 蛇头
# -----------------------
head = turtle.Turtle()
head.speed(0)
head.shape("square")
head.color("lime")
head.penup()
head.goto(0, 0)
head.direction = "stop"

# -----------------------
# 食物
# -----------------------
food = turtle.Turtle()
food.speed(0)
food.shape("circle")
food.color("red")
food.penup()
food.goto(0, 100)

segments = []

# -----------------------
# 工具函数
# -----------------------
def update_score():
    pen.clear()
    pen.write(f"Score: {score}  Best: {best_score}",
              align="center", font=("Consolas", 18, "normal"))

def reset_game():
    global score, best_score
    time.sleep(0.6)

    head.goto(0, 0)
    head.direction = "stop"

    for seg in segments:
        seg.goto(1000, 1000)
    segments.clear()

    if score > best_score:
        best_score = score
    score = 0
    update_score()

def set_direction(new_dir):
    # 防止直接反向
    opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
    if head.direction == "stop":
        head.direction = new_dir
    elif opposite.get(head.direction) != new_dir:
        head.direction = new_dir

def go_up():
    set_direction("up")

def go_down():
    set_direction("down")

def go_left():
    set_direction("left")

def go_right():
    set_direction("right")

def move():
    x, y = head.xcor(), head.ycor()
    step = 20
    if head.direction == "up":
        head.sety(y + step)
    elif head.direction == "down":
        head.sety(y - step)
    elif head.direction == "left":
        head.setx(x - step)
    elif head.direction == "right":
        head.setx(x + step)

def random_food_pos():
    # 让食物落在 20 的网格上
    grid = 20
    max_x = (WIDTH // 2 - 40) // grid
    max_y = (HEIGHT // 2 - 60) // grid
    x = random.randint(-max_x, max_x) * grid
    y = random.randint(-max_y, max_y) * grid
    return x, y

# 键盘绑定
wn.listen()
wn.onkeypress(go_up, "w")
wn.onkeypress(go_down, "s")
wn.onkeypress(go_left, "a")
wn.onkeypress(go_right, "d")
wn.onkeypress(go_up, "Up")
wn.onkeypress(go_down, "Down")
wn.onkeypress(go_left, "Left")
wn.onkeypress(go_right, "Right")

# -----------------------
# 主循环
# -----------------------
while True:
    wn.update()

    # 撞墙检测
    if (head.xcor() > WIDTH // 2 - 20 or head.xcor() < -WIDTH // 2 + 20 or
        head.ycor() > HEIGHT // 2 - 20 or head.ycor() < -HEIGHT // 2 + 20):
        reset_game()

    # 吃到食物
    if head.distance(food) < 18:
        fx, fy = random_food_pos()
        food.goto(fx, fy)

        new_seg = turtle.Turtle()
        new_seg.speed(0)
        new_seg.shape("square")
        new_seg.color("green")
        new_seg.penup()
        segments.append(new_seg)

        score += 10
        update_score()

    # 移动身体：从尾到头跟随
    for i in range(len(segments) - 1, 0, -1):
        segments[i].goto(segments[i - 1].xcor(), segments[i - 1].ycor())
    if segments:
        segments[0].goto(head.xcor(), head.ycor())

    # 移动蛇头
    move()

    # 撞到自己
    for seg in segments:
        if seg.distance(head) < 15:
            reset_game()
            break

    time.sleep(DELAY)