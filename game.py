import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, TRAP = 0, 1, 2, 3, 4
SPEED = 3
GUARD_SPEED = 2
TRAP_COUNT = 6
MINI_TILE = 5   # pixel size of one tile in the mini-map

def can_reach(grid, start, goal, blocked=()):
    """BFS over tiles (col,row). WALL, TRAP and `blocked` tiles are impassable."""
    seen, queue = {start}, [start]
    while queue:
        c, r = queue.pop(0)
        if (c, r) == goal:
            return True
        for nc, nr in ((c+1,r),(c-1,r),(c,r+1),(c,r-1)):
            if (0 <= nr < ROWS and 0 <= nc < COLS and (nc,nr) not in seen
                    and grid[nr][nc] not in (WALL, TRAP) and (nc,nr) not in blocked):
                seen.add((nc,nr))
                queue.append((nc,nr))
    return False


def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]
        grid[cr.centery][cr.centerx] = CHEST
        grid[ck.centery][ck.centerx] = KEY

    # Traps: any room floor tile except the spawn area, the key/chest tiles and the
    # ring around the chest (kept clear so the guard has room to patrol)
    if len(rooms) >= 2:
        sx0, sy0 = rooms[0].topleft
        ccx, ccy = rooms[-1].center
        spots = [(x, y) for rm in rooms
                 for y in range(rm.top, rm.bottom) for x in range(rm.left, rm.right)
                 if grid[y][x] == FLOOR
                 and max(abs(x-sx0), abs(y-sy0)) > 1
                 and max(abs(x-ccx), abs(y-ccy)) > 1]
        random.shuffle(spots)
        placed = 0
        for x, y in spots:
            if placed >= TRAP_COUNT:
                break
            grid[y][x] = TRAP
            if (can_reach(grid, rooms[0].topleft, rooms[-1].center) and
                    can_reach(grid, rooms[0].topleft, rooms[-2].center)):
                placed += 1
            else:
                grid[y][x] = FLOOR   # this trap would block the level, undo it
    start = rooms[0] if rooms else None
    return grid, start

COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    TRAP: (110,45,45),
}

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=SPEED
        self._try_move(dx,0,grid,rows,cols)
        self._try_move(0,dy,grid,rows,cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx,dy)
        for px,py in [(new.left,new.top),(new.right-1,new.top),(new.left,new.bottom-1),(new.right-1,new.bottom-1)]:
            c,r=px//TILE,py//TILE
            if not(0<=r<rows and 0<=c<cols) or grid[r][c]==WALL:
                return
        self.rect=new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(screen, (220,220,60), (self.rect.right-6, self.rect.top+6), 5)


class Guard:
    def __init__(self, p1, p2):
        # p1, p2 are (col,row) tiles; patrol runs along one row or one column
        self.points = [(p1[0]*TILE+6, p1[1]*TILE+6), (p2[0]*TILE+6, p2[1]*TILE+6)]
        self.target = 1
        self.rect = pygame.Rect(self.points[0][0], self.points[0][1], 28, 28)

    def update(self):
        tx, ty = self.points[self.target]
        dx = max(-GUARD_SPEED, min(GUARD_SPEED, tx - self.rect.x))
        dy = max(-GUARD_SPEED, min(GUARD_SPEED, ty - self.rect.y))
        self.rect.move_ip(dx, dy)
        if self.rect.topleft == (tx, ty):
            self.target = 1 - self.target      # turn around

    def draw(self, screen):
        pygame.draw.rect(screen, (200,50,50), self.rect, border_radius=6)
        pygame.draw.rect(screen, (255,255,255), self.rect, 2, border_radius=6)


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.reset()

    def reset(self):
        self.grid, start = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6
        self.player = Player(sx, sy)
        self.start_pos = (sx, sy)
        self.guard = self.make_guard()
        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def respawn_player(self, message):
        self.player.rect.topleft = self.start_pos
        self.status = message

    def make_guard(self):
        def find(tile):
            return next(((c, r) for r in range(ROWS) for c in range(COLS)
                         if self.grid[r][c] == tile), None)
        chest, key = find(CHEST), find(KEY)
        if chest is None or key is None:
            return None
        cc, cr = chest
        start_tile = (self.start_pos[0] // TILE, self.start_pos[1] // TILE)
        # patrol beside the chest: row above, row below, column left, column right
        lines = [((cc-1,cr-1),(cc+1,cr-1)), ((cc-1,cr+1),(cc+1,cr+1)),
                 ((cc-1,cr-1),(cc-1,cr+1)), ((cc+1,cr-1),(cc+1,cr+1))]
        # fallback: shorter 1-tile patrols (each half of a line) if a full line blocks a route
        halves = []
        for a, b in lines:
            m = ((a[0]+b[0])//2, (a[1]+b[1])//2)
            halves += [(a, m), (m, b)]
        for a, b in lines + halves:
            tiles = {a, b, ((a[0]+b[0])//2, (a[1]+b[1])//2)}
            if (all(0 <= c < COLS and 0 <= r < ROWS and self.grid[r][c] == FLOOR
                    for c, r in tiles)
                    # key AND chest must stay reachable without crossing the patrol line
                    and all(can_reach(self.grid, start_tile, goal, tiles)
                            for goal in (chest, key))):
                return Guard(a, b)
        return None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
        return True

    def update(self):
        if self.won: return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)
        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE
        if 0<=pr<ROWS and 0<=pc<COLS:
            cell = self.grid[pr][pc]
            if cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"
            elif cell == TRAP:
                self.respawn_player("Trap! Back to start.")

        if self.guard and not self.won:
            self.guard.update()
            if self.player.rect.colliderect(self.guard.rect):
                self.respawn_player("Caught by the guard!")

    def draw_minimap(self):
        s = MINI_TILE
        ox, oy = WIDTH - COLS*s - 8, 8
        pygame.draw.rect(self.screen, (10,10,15), (ox-2, oy-2, COLS*s+4, ROWS*s+4))
        for r in range(ROWS):
            for c in range(COLS):
                color = (80,70,100) if self.grid[r][c] == WALL else (200,190,170)
                pygame.draw.rect(self.screen, color, (ox+c*s, oy+r*s, s, s))
        px = ox + self.player.rect.centerx * s // TILE
        py = oy + self.player.rect.centery * s // TILE
        pygame.draw.circle(self.screen, (60,120,220), (px, py), 3)

    def draw_inventory(self):
        slot = pygame.Rect(WIDTH - 48, ROWS*TILE + 7, 36, 36)
        pygame.draw.rect(self.screen, (45,45,65), slot, border_radius=4)
        pygame.draw.rect(self.screen, (120,120,150), slot, 2, border_radius=4)
        if self.player.has_key:
            gold = (255,240,60)
            pygame.draw.circle(self.screen, gold, (slot.x+12, slot.centery), 7)
            pygame.draw.rect(self.screen, gold, (slot.x+16, slot.centery-2, 16, 4))
            pygame.draw.rect(self.screen, gold, (slot.x+26, slot.centery, 3, 7))

    def draw(self):
        self.screen.fill((30,25,40))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)
                if cell == KEY:
                    pygame.draw.circle(self.screen, (255,240,60),(c*TILE+TILE//2, r*TILE+TILE//2),10)
                elif cell == CHEST:
                    pygame.draw.rect(self.screen,(180,120,20),rect.inflate(-12,-12),border_radius=4)
                elif cell == TRAP:
                    t = rect.inflate(-14,-14)
                    pygame.draw.line(self.screen,(230,50,50),t.topleft,t.bottomright,4)
                    pygame.draw.line(self.screen,(230,50,50),t.topright,t.bottomleft,4)
        if self.guard:
            self.guard.draw(self.screen)
        self.player.draw(self.screen)
        self.draw_minimap()
        hud = pygame.Rect(0,ROWS*TILE,WIDTH,50)
        pygame.draw.rect(self.screen,(20,20,35),hud)
        st = self.font.render(self.status+"  |  R=Restart", True, (200,200,200))
        self.screen.blit(st,(8,ROWS*TILE+13))
        self.draw_inventory()
        if self.won:
            ov=pygame.Surface((WIDTH,ROWS*TILE),pygame.SRCALPHA)
            ov.fill((0,0,0,140))
            self.screen.blit(ov,(0,0))
            msg=self.big_font.render("TREASURE FOUND!", True,(220,180,30))
            sub=self.font.render("Press R to Play Again",True,(180,180,180))
            self.screen.blit(msg,(WIDTH//2-msg.get_width()//2,ROWS*TILE//2-30))
            self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,ROWS*TILE//2+20))
        pygame.display.flip()

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()