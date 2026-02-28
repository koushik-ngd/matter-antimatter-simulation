import pygame
import random
import math
import sys

WIDTH, HEIGHT = 1100, 700
FPS = 60
PARTICLE_MASS = 1.0
ANNIHILATION_RADIUS = 14
PARTICLE_RADIUS = 6
ENERGY_LIFETIME = 90
SPAWN_INTERVAL = 90

BG_DARK        = (6, 6, 18)
MATTER_COL     = (80, 160, 255)
ANTIMATTER_COL = (255, 80, 120)
ENERGY_COL     = (255, 230, 80)
PROTON_COL     = (60, 200, 120)
ANTIPROTON_COL = (220, 100, 255)
TEXT_COL       = (200, 210, 230)
GRID_COL       = (20, 24, 48)

class Particle:
    def __init__(self, x, y, vx, vy, is_anti, ptype="electron"):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.is_anti = is_anti
        self.ptype = ptype
        self.mass = PARTICLE_MASS
        self.alive = True
        self.radius = PARTICLE_RADIUS
        self.trail = []
        self.trail_max = 18

    @property
    def color(self):
        if self.ptype == "proton":
            return ANTIPROTON_COL if self.is_anti else PROTON_COL
        return ANTIMATTER_COL if self.is_anti else MATTER_COL

    def kinetic_energy(self):
        speed = math.sqrt(self.vx**2 + self.vy**2)
        c_norm = 5.0
        beta = min(speed / c_norm, 0.999)
        gamma = 1.0 / math.sqrt(1 - beta**2)
        return (gamma - 1) * self.mass * c_norm**2

    def rest_energy(self):
        return self.mass * 25.0

    def update(self, bounds):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > self.trail_max:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if self.x - self.radius < 0:
            self.x = self.radius; self.vx *= -1
        if self.x + self.radius > bounds[0]:
            self.x = bounds[0] - self.radius; self.vx *= -1
        if self.y - self.radius < 0:
            self.y = self.radius; self.vy *= -1
        if self.y + self.radius > bounds[1]:
            self.y = bounds[1] - self.radius; self.vy *= -1

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            r = max(1, int(self.radius * 0.5 * i / self.trail_max))
            col = tuple(int(c * (i / self.trail_max)) for c in self.color)
            pygame.draw.circle(surf, col, (tx, ty), r)
        glow = pygame.Surface((self.radius*6, self.radius*6), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 40), (self.radius*3, self.radius*3), self.radius*3)
        surf.blit(glow, (int(self.x)-self.radius*3, int(self.y)-self.radius*3))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (255,255,255), (int(self.x), int(self.y)), max(2, self.radius//3))


class EnergyBurst:
    def __init__(self, x, y, energy, num_photons=8):
        self.x, self.y = x, y
        self.energy = energy
        self.life = ENERGY_LIFETIME
        self.max_life = ENERGY_LIFETIME
        self.photons = []
        for i in range(num_photons):
            angle = (2 * math.pi * i / num_photons) + random.uniform(-0.2, 0.2)
            speed = random.uniform(2.5, 5.0)
            self.photons.append([x, y, math.cos(angle)*speed, math.sin(angle)*speed])

    def update(self):
        self.life -= 1
        for p in self.photons:
            p[0] += p[2]; p[1] += p[3]
            p[2] *= 0.97; p[3] *= 0.97

    def draw(self, surf, font):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        alpha = int(255 * t)
        radius = int(50 * (1 - t) + 5)
        ring = pygame.Surface((radius*2+4, radius*2+4), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*ENERGY_COL, alpha//2), (radius+2, radius+2), radius, 2)
        surf.blit(ring, (int(self.x)-radius-2, int(self.y)-radius-2))
        for p in self.photons:
            ray = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(ray, (*ENERGY_COL, alpha), (3, 3), 3)
            surf.blit(ray, (int(p[0])-3, int(p[1])-3))
        if t > 0.4:
            surf.blit(font.render(f"E={self.energy:.1f}", True, ENERGY_COL),
                      (int(self.x)-20, int(self.y)-20))

    @property
    def alive(self):
        return self.life > 0


def elastic_collision(p1, p2):
    dx = p2.x - p1.x; dy = p2.y - p1.y
    dist = math.sqrt(dx**2 + dy**2)
    if dist == 0: return
    nx, ny = dx/dist, dy/dist
    dot = (p1.vx-p2.vx)*nx + (p1.vy-p2.vy)*ny
    if dot <= 0: return
    p1.vx -= dot*nx; p1.vy -= dot*ny
    p2.vx += dot*nx; p2.vy += dot*ny


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Matter-Antimatter Simulation | E = mc2")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier New", 14)
    font_lg = pygame.font.SysFont("Courier New", 18, bold=True)
    font_title = pygame.font.SysFont("Courier New", 22, bold=True)

    particles = []
    bursts = []
    total_annihilations = 0
    total_energy_released = 0.0
    frame = 0
    paused = False
    SIM_W, SIM_H = WIDTH - 260, HEIGHT

    def spawn_pair(ptype="electron"):
        speed = random.uniform(1.0, 3.0)
        for is_anti in [False, True]:
            x = random.randint(30, SIM_W-30)
            y = random.randint(30, SIM_H-30)
            a = random.uniform(0, 2*math.pi)
            particles.append(Particle(x, y, math.cos(a)*speed, math.sin(a)*speed, is_anti, ptype))

    for _ in range(5): spawn_pair("electron")
    for _ in range(3): spawn_pair("proton")

    grid = pygame.Surface((SIM_W, SIM_H))
    grid.fill(BG_DARK)
    for gx in range(0, SIM_W, 40):
        pygame.draw.line(grid, GRID_COL, (gx, 0), (gx, SIM_H))
    for gy in range(0, SIM_H, 40):
        pygame.draw.line(grid, GRID_COL, (0, gy), (SIM_W, gy))

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.key == pygame.K_SPACE: paused = not paused
                if event.key == pygame.K_e: spawn_pair("electron")
                if event.key == pygame.K_p: spawn_pair("proton")
                if event.key == pygame.K_c: particles.clear(); bursts.clear()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if mx < SIM_W:
                    is_anti = event.button == 3
                    ptype = "proton" if pygame.key.get_mods() & pygame.KMOD_SHIFT else "electron"
                    a = random.uniform(0, 2*math.pi)
                    spd = random.uniform(1.5, 2.5)
                    particles.append(Particle(mx, my, math.cos(a)*spd, math.sin(a)*spd, is_anti, ptype))

        if not paused:
            frame += 1
            if frame % SPAWN_INTERVAL == 0 and len(particles) < 60:
                spawn_pair(random.choice(["electron", "proton"]))

            for p in particles:
                p.update((SIM_W, SIM_H))

            alive = [p for p in particles if p.alive]
            for i in range(len(alive)):
                for j in range(i+1, len(alive)):
                    p1, p2 = alive[i], alive[j]
                    dx = p1.x - p2.x; dy = p1.y - p2.y
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < ANNIHILATION_RADIUS:
                        if p1.is_anti != p2.is_anti and p1.ptype == p2.ptype:
                            energy = (p1.rest_energy() + p2.rest_energy() +
                                      p1.kinetic_energy() + p2.kinetic_energy())
                            bursts.append(EnergyBurst((p1.x+p2.x)/2, (p1.y+p2.y)/2, energy))
                            p1.alive = False; p2.alive = False
                            total_annihilations += 1
                            total_energy_released += energy
                        elif p1.is_anti == p2.is_anti and dist < ANNIHILATION_RADIUS * 0.8:
                            elastic_collision(p1, p2)
                            if dist > 0:
                                overlap = ANNIHILATION_RADIUS * 0.8 - dist
                                nx, ny = dx/dist, dy/dist
                                p1.x += nx*overlap*0.5; p1.y += ny*overlap*0.5
                                p2.x -= nx*overlap*0.5; p2.y -= ny*overlap*0.5

            particles = [p for p in particles if p.alive]
            for b in bursts: b.update()
            bursts = [b for b in bursts if b.alive]

        # Draw simulation
        screen.blit(grid, (0, 0))
        pygame.draw.line(screen, (40,50,90), (SIM_W, 0), (SIM_W, HEIGHT), 2)
        for b in bursts: b.draw(screen, font)
        for p in particles: p.draw(screen)

        # Side panel
        px = SIM_W + 10
        pygame.draw.rect(screen, (10,12,28), (SIM_W, 0, 260, HEIGHT))
        y = 15
        screen.blit(font_title.render("E = mc2", True, ENERGY_COL), (px, y)); y += 30
        screen.blit(font.render("Matter-Antimatter Sim", True, TEXT_COL), (px, y)); y += 25
        pygame.draw.line(screen, (40,50,90), (px, y), (px+238, y)); y += 12

        matter = sum(1 for p in particles if not p.is_anti)
        anti   = sum(1 for p in particles if p.is_anti)
        for lbl, val in [("PARTICLES",""), ("  Matter", str(matter)), ("  Antimatter", str(anti)),
                         ("",""), ("ANNIHILATIONS",""), ("  Total", str(total_annihilations)),
                         ("  Energy out", f"{total_energy_released:.1f}"), ("",""),
                         ("ACTIVE BURSTS", str(len(bursts)))]:
            if lbl == "" and val == "": y += 5; continue
            col = ENERGY_COL if lbl in ("PARTICLES","ANNIHILATIONS","ACTIVE BURSTS") else TEXT_COL
            screen.blit(font.render(lbl, True, col), (px, y))
            if val: screen.blit(font.render(val, True, (255,255,255)), (px+160, y))
            y += 18

        pygame.draw.line(screen, (40,50,90), (px, y), (px+238, y)); y += 12
        for col, lbl in [(MATTER_COL,"Electron (e-)"), (ANTIMATTER_COL,"Positron (e+)"),
                         (PROTON_COL,"Proton (p)"), (ANTIPROTON_COL,"Antiproton (p-)"),
                         (ENERGY_COL,"Gamma photon")]:
            pygame.draw.circle(screen, col, (px+8, y+7), 6)
            screen.blit(font.render(lbl, True, TEXT_COL), (px+20, y)); y += 20

        y += 10
        pygame.draw.line(screen, (40,50,90), (px, y), (px+238, y)); y += 12
        for txt, col in [("CONTROLS", ENERGY_COL), ("[E] Spawn electron pair", TEXT_COL),
                         ("[P] Spawn proton pair", TEXT_COL), ("[C] Clear all", TEXT_COL),
                         ("[SPACE] Pause/Resume", TEXT_COL), ("LMB = place matter", TEXT_COL),
                         ("RMB = place antimatter", TEXT_COL), ("+SHIFT for proton type", TEXT_COL)]:
            screen.blit(font.render(txt, True, col), (px, y)); y += 17

        if paused:
            screen.blit(font_lg.render("PAUSED", True, (255,200,60)), (SIM_W//2-30, HEIGHT//2-10))

        screen.blit(font.render(f"FPS: {int(clock.get_fps())}", True, (80,90,120)), (px, HEIGHT-20))
        pygame.display.flip()

if __name__ == "__main__":
    main()