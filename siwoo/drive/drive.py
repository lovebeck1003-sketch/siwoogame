"""무한한 들판을 달리는 힐링 드라이브 게임.

조작:
  W / ↑    가속        S / ↓    브레이크·후진
  A / ←    좌회전      D / →    우회전
  Shift    부스트      Space    핸드브레이크(드리프트)
  C        시점 전환   ESC      종료
"""

import math
import random

import pygame

W, H = 1100, 700
CHUNK = 400          # 절차적 지형 청크 크기(월드 좌표)
VIEW_PAD = 2         # 화면 밖으로 몇 청크까지 그릴지

# ── 색 팔레트 ────────────────────────────────────────────────
GRASS = [(126, 176, 92), (118, 168, 86), (134, 182, 100), (110, 162, 84)]
TREE_TRUNK = (108, 82, 58)
TREE_LEAF = [(64, 122, 66), (78, 138, 74), (56, 110, 60)]
FLOWER = [(244, 236, 148), (240, 168, 190), (232, 234, 244), (198, 176, 240)]
WATER = (104, 168, 200)
WATER_EDGE = (150, 200, 218)
ROCK = (150, 150, 148)
CAR_BODY = (222, 84, 76)
CAR_DARK = (170, 58, 54)
GLASS = (140, 190, 214)


def chunk_rng(cx, cy):
    """청크 좌표로부터 항상 같은 결과를 주는 난수 생성기."""
    return random.Random((cx * 73856093) ^ (cy * 19349663))


def make_chunk(cx, cy):
    """청크 하나의 장식물 목록을 생성한다. (종류, 월드x, 월드y, 크기, 부가값)"""
    rng = chunk_rng(cx, cy)
    ox, oy = cx * CHUNK, cy * CHUNK
    items = []

    # 잔디 색 얼룩
    for _ in range(3):
        items.append(("patch", ox + rng.random() * CHUNK, oy + rng.random() * CHUNK,
                      rng.uniform(90, 190), rng.choice(GRASS)))

    # 가끔 연못
    if rng.random() < 0.18:
        items.append(("pond", ox + rng.random() * CHUNK, oy + rng.random() * CHUNK,
                      rng.uniform(60, 130), 0))

    for _ in range(rng.randint(2, 7)):
        items.append(("tree", ox + rng.random() * CHUNK, oy + rng.random() * CHUNK,
                      rng.uniform(16, 30), rng.choice(TREE_LEAF)))

    for _ in range(rng.randint(0, 3)):
        items.append(("rock", ox + rng.random() * CHUNK, oy + rng.random() * CHUNK,
                      rng.uniform(6, 13), 0))

    for _ in range(rng.randint(10, 26)):
        items.append(("flower", ox + rng.random() * CHUNK, oy + rng.random() * CHUNK,
                      rng.uniform(2, 3.6), rng.choice(FLOWER)))

    items.sort(key=lambda it: it[2])   # y 정렬 → 겹칠 때 자연스럽게
    return items


class Car:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.angle = -math.pi / 2      # 위쪽을 향해 시작
        self.speed = 0.0               # 전진 속도(px/s)
        self.drift = 0.0               # 드리프트 정도 0~1

    def update(self, dt, keys):
        accel = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            accel += 460
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            accel -= 380

        boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        top = 700 if boost else 440
        handbrake = keys[pygame.K_SPACE]

        self.speed += accel * dt
        # 마찰·공기저항
        self.speed *= math.pow(0.35 if handbrake else 0.86, dt)
        self.speed = max(-220, min(top, self.speed))

        # 속도가 붙어야 핸들이 먹는다
        grip = min(1.0, abs(self.speed) / 160)
        turn = 2.4 * grip * (1.35 if handbrake else 1.0) * (1 if self.speed >= 0 else -1)
        steer = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            steer -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            steer += 1
        self.angle += steer * turn * dt

        target_drift = 1.0 if (handbrake and abs(self.speed) > 120) else 0.0
        self.drift += (target_drift - self.drift) * min(1.0, 6 * dt)

        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt


def draw_car(surf, px, py, angle, drift):
    """차를 (px, py) 화면 좌표에 angle 방향으로 그린다."""
    body = pygame.Surface((60, 32), pygame.SRCALPHA)
    pygame.draw.rect(body, (0, 0, 0, 60), (2, 5, 58, 26), border_radius=9)
    pygame.draw.rect(body, CAR_DARK, (4, 3, 52, 26), border_radius=9)
    pygame.draw.rect(body, CAR_BODY, (6, 5, 48, 22), border_radius=8)
    pygame.draw.rect(body, GLASS, (26, 8, 14, 16), border_radius=4)      # 앞 유리
    pygame.draw.rect(body, GLASS, (13, 9, 8, 14), border_radius=3)       # 뒷 유리
    pygame.draw.rect(body, (255, 244, 210), (52, 8, 4, 6), border_radius=2)
    pygame.draw.rect(body, (255, 244, 210), (52, 18, 4, 6), border_radius=2)
    if drift > 0.3:
        pygame.draw.rect(body, (255, 120, 90), (5, 9, 4, 5), border_radius=2)
        pygame.draw.rect(body, (255, 120, 90), (5, 18, 4, 5), border_radius=2)

    rot = pygame.transform.rotate(body, -math.degrees(angle))
    surf.blit(rot, rot.get_rect(center=(px, py)))


def draw_item(surf, kind, sx, sy, size, extra, t):
    if kind == "patch":
        pygame.draw.circle(surf, extra, (int(sx), int(sy)), int(size))
    elif kind == "pond":
        pygame.draw.circle(surf, WATER_EDGE, (int(sx), int(sy)), int(size) + 5)
        pygame.draw.circle(surf, WATER, (int(sx), int(sy)), int(size))
        r = size * 0.55 + math.sin(t * 1.4) * 4
        pygame.draw.circle(surf, WATER_EDGE, (int(sx), int(sy)), int(r), 2)
    elif kind == "tree":
        pygame.draw.ellipse(surf, (96, 138, 78),
                            (sx - size * 0.9, sy + size * 0.2, size * 1.8, size * 0.7))
        pygame.draw.rect(surf, TREE_TRUNK, (sx - 3, sy - 2, 6, size * 0.6))
        sway = math.sin(t * 0.9 + sx * 0.01) * 2
        pygame.draw.circle(surf, extra, (int(sx + sway), int(sy - size * 0.4)), int(size))
        pygame.draw.circle(surf, (min(255, extra[0] + 22), min(255, extra[1] + 26), extra[2] + 12),
                           (int(sx + sway - size * 0.3), int(sy - size * 0.7)), int(size * 0.55))
    elif kind == "rock":
        pygame.draw.circle(surf, (120, 120, 118), (int(sx), int(sy + 2)), int(size))
        pygame.draw.circle(surf, ROCK, (int(sx), int(sy)), int(size))
    elif kind == "flower":
        pygame.draw.circle(surf, extra, (int(sx), int(sy)), int(size))


def main():
    pygame.init()
    pygame.display.set_caption("무한 드라이브 — 힐링 로드")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("malgungothic", 18)
    big = pygame.font.SysFont("malgungothic", 30, bold=True)

    car = Car()
    chunks = {}
    tracks = []          # 드리프트 자국: [월드x, 월드y, 수명]
    chase_cam = True
    t = 0.0

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        t += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_c:
                    chase_cam = not chase_cam

        keys = pygame.key.get_pressed()
        car.update(dt, keys)

        if car.drift > 0.4 and abs(car.speed) > 100:
            back = car.angle + math.pi
            for side in (-1, 1):
                ox = math.cos(back) * 18 + math.cos(back + math.pi / 2) * 9 * side
                oy = math.sin(back) * 18 + math.sin(back + math.pi / 2) * 9 * side
                tracks.append([car.x + ox, car.y + oy, 4.0])
        for tr in tracks:
            tr[2] -= dt
        tracks = [tr for tr in tracks if tr[2] > 0][-900:]

        # ── 카메라 ───────────────────────────────────────────
        if chase_cam:
            cam_rot = -car.angle - math.pi / 2
        else:
            cam_rot = 0.0
        cos_r, sin_r = math.cos(cam_rot), math.sin(cam_rot)

        def to_screen(wx, wy):
            dx, dy = wx - car.x, wy - car.y
            return (dx * cos_r - dy * sin_r + W / 2,
                    dx * sin_r + dy * cos_r + H / 2 + (110 if chase_cam else 0))

        # ── 낮/밤 ────────────────────────────────────────────
        day = (math.sin(t * 0.045) + 1) / 2          # 0=밤, 1=낮
        base = GRASS[0]
        screen.fill((int(base[0] * (0.35 + 0.65 * day)),
                     int(base[1] * (0.38 + 0.62 * day)),
                     int(base[2] * (0.5 + 0.5 * day))))

        ccx, ccy = int(car.x // CHUNK), int(car.y // CHUNK)
        span = int(max(W, H) / CHUNK) + VIEW_PAD
        for cy in range(ccy - span, ccy + span + 1):
            for cx in range(ccx - span, ccx + span + 1):
                key = (cx, cy)
                if key not in chunks:
                    chunks[key] = make_chunk(cx, cy)
                for kind, wx, wy, size, extra in chunks[key]:
                    sx, sy = to_screen(wx, wy)
                    if -200 < sx < W + 200 and -200 < sy < H + 200:
                        draw_item(screen, kind, sx, sy, size, extra, t)

        if len(chunks) > 900:                        # 멀어진 청크 정리
            for key in [k for k in chunks
                        if abs(k[0] - ccx) > span + 3 or abs(k[1] - ccy) > span + 3]:
                del chunks[key]

        for tx, ty, life in tracks:
            sx, sy = to_screen(tx, ty)
            if -40 < sx < W + 40 and -40 < sy < H + 40:
                a = int(70 * (life / 4.0))
                s = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(s, (60, 55, 50, a), (4, 4), 4)
                screen.blit(s, (sx - 4, sy - 4))

        draw_car(screen, W / 2, H / 2 + (110 if chase_cam else 0),
                 car.angle + cam_rot, car.drift)

        # 밤 오버레이
        if day < 0.75:
            night = pygame.Surface((W, H), pygame.SRCALPHA)
            night.fill((16, 22, 60, int((0.75 - day) * 150)))
            screen.blit(night, (0, 0))

        # ── HUD ──────────────────────────────────────────────
        kmh = abs(car.speed) * 0.35
        screen.blit(big.render(f"{kmh:5.0f} km/h", True, (255, 255, 255)), (26, H - 74))
        dist = math.hypot(car.x, car.y) / 1000
        screen.blit(font.render(f"집에서 {dist:.1f} km", True, (235, 240, 235)), (28, H - 36))
        hint = "W/S 가속·브레이크   A/D 조향   Shift 부스트   Space 드리프트   C 시점   ESC 종료"
        screen.blit(font.render(hint, True, (245, 248, 244)), (26, 20))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
