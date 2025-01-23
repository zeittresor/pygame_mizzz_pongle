import pygame
import os
import sys
import math
import time
import array
import random
import traceback

DEBUG_LOG = False
if "-debuglog" in sys.argv:
    DEBUG_LOG = True

NOSPOON_MODE = False
if "-nospoon" in sys.argv:
    NOSPOON_MODE = True

FUNDS_MODE = False
if "-funds" in sys.argv:
    FUNDS_MODE = True

def debug_print(msg):
    if DEBUG_LOG:
        print(msg)

try:
    from pydub import AudioSegment
    PITCH_SHIFT_AVAILABLE = True
    debug_print("pydub import successful. Attempting pitch-shift if ffmpeg is found.")
except ImportError:
    PITCH_SHIFT_AVAILABLE = False
    debug_print("pydub not available. Pitch-shift will not be used.")

SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0
FPS = 60
BALL_SPEED_MODIFIER = 0.8
GRAVITY = 0.25
MAX_SHOTS = 12
HOLES_COUNT = 5
if FUNDS_MODE:
    MAX_SHOTS = 999

BG_COLOR_CYCLE = 0
COLOR_CYCLE_INTERVAL = 45
COLOR_CYCLE_FADE_DURATION = 10
HUE_SHIFT_STEP = 60
COLOR_SHIFT_FPS = 2

FONT_NAME = None
LOG_FILENAME = "score_log.txt"
MUSIC_FILES = []
MUSIC_INDEX = 0

IS_PAUSED = False
SHOW_OPTIONS = False
BRIGHTNESS = 0.6
MUSIC_VOLUME = 1.0

BG_IMAGES = []
BG_INDEX = 0

def ensure_data_folder():
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    readme_path = os.path.join(data_dir, "readme.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("Possible files and what they are used for:\n")
        f.write("- background.png\n")
        f.write("- backgroundSomething.png\n")
        f.write("- bumper.png\n")
        f.write("- hole.png\n")
        f.write("- corner.png\n")
        f.write("- ball.png\n")
        f.write("- bumper.wav\n")
        f.write("- border.wav\n")
        f.write("- panel.wav\n")
        f.write("- button.wav\n")
        f.write("- panel_left.png / panel_right.png\n")
        f.write("- orgon.png\n")
        f.write("- repulsine.png\n")
        f.write("- Any .mp3 file\n")
        f.write("Game principle:\n")
        f.write("Pinball-like game.\n")
        f.write("Command line parameters:\n")
        f.write("-debuglog\n")
        f.write("-nospoon\n")
        f.write("-funds\n")

def load_music_files_from_data():
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        debug_print("No data folder found. No music can be loaded.")
        return
    global MUSIC_FILES
    for file in os.listdir(data_dir):
        if file.lower().endswith(".mp3"):
            MUSIC_FILES.append(os.path.join(data_dir, file))
    MUSIC_FILES.sort()
    debug_print("Music files found: " + str(MUSIC_FILES))

def load_all_background_images():
    data_dir = os.path.join(os.getcwd(), "data")
    found_files = []
    for file in os.listdir(data_dir):
        if file.lower().startswith("background") and file.lower().endswith(".png"):
            found_files.append(file)
    found_files.sort()
    for fn in found_files:
        path = os.path.join(data_dir, fn)
        try:
            img = pygame.image.load(path).convert_alpha()
            BG_IMAGES.append(img)
            debug_print("Loaded multi-background: " + fn)
        except Exception as e:
            debug_print("Error loading multi-background " + fn + ": " + str(e))

def play_next_song():
    global MUSIC_INDEX
    if not MUSIC_FILES:
        debug_print("No music files present. Skipping play_next_song().")
        return
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.music.load(MUSIC_FILES[MUSIC_INDEX])
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play()
        debug_print("Playing music: " + MUSIC_FILES[MUSIC_INDEX])
        MUSIC_INDEX = (MUSIC_INDEX + 1) % len(MUSIC_FILES)
    except Exception as e:
        debug_print("Error loading/playing MP3: " + str(e))

def check_and_play_music():
    if not MUSIC_FILES:
        return
    if not pygame.mixer.music.get_busy():
        play_next_song()

def log_score(score):
    with open(LOG_FILENAME, "a", encoding="utf-8") as f:
        f.write("Score: " + str(score) + " - Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
    debug_print("Score " + str(score) + " written to log.")

def get_alpha_mask_circle(radius, color=(255, 0, 0)):
    surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (radius, radius), radius)
    mask = pygame.mask.from_surface(surf)
    return surf, mask

def load_image_with_mask(image_path):
    surf = pygame.image.load(image_path).convert_alpha()
    mask = pygame.mask.from_surface(surf)
    rect = surf.get_rect()
    return surf, mask, rect

def create_sine_wave(frequency, length_ms=200, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * (length_ms / 1000.0))
    pcm16 = array.array("h")
    for s in range(n_samples):
        t = float(s) / sample_rate
        val = volume * math.sin(2.0 * math.pi * frequency * t)
        pcm16.append(int(val * 32767))
    return pygame.mixer.Sound(buffer=pcm16.tobytes())

def pitch_shift_wav(wav_path, semitone):
    if not PITCH_SHIFT_AVAILABLE:
        debug_print("Pitch shift not available (pydub or ffmpeg missing).")
        return None
    try:
        from pydub import AudioSegment
        original = AudioSegment.from_file(wav_path)
        new_frame_rate = int(original.frame_rate * (2.0 ** (semitone / 12.0)))
        shifted = original._spawn(original.raw_data, overrides={"frame_rate": new_frame_rate})
        shifted = shifted.set_frame_rate(44100)
        debug_print("Successfully pitch-shifted " + wav_path + " by " + str(semitone))
        return shifted.raw_data
    except Exception as e:
        debug_print("Pitch-shift failed: " + str(e))
        return None

def rgb_to_hsv(r, g, b):
    rf = r / 255.0
    gf = g / 255.0
    bf = b / 255.0
    mx = max(rf, gf, bf)
    mn = min(rf, gf, bf)
    d = mx - mn
    if d == 0:
        h = 0
    elif mx == rf:
        h = (60 * ((gf - bf) / d) + 360) % 360
    elif mx == gf:
        h = (60 * ((bf - rf) / d) + 120) % 360
    else:
        h = (60 * ((rf - gf) / d) + 240) % 360
    s = 0 if mx == 0 else d / mx
    v = mx
    return h, s, v

def hsv_to_rgb(h, s, v):
    c = v * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = v - c
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    r = (r + m) * 255
    g = (g + m) * 255
    b = (b + m) * 255
    return int(round(r)), int(round(g)), int(round(b))

def shift_surface_hue(original_surf, hue_value):
    arr_rgb = pygame.surfarray.array3d(original_surf)
    arr_alpha = pygame.surfarray.array_alpha(original_surf)
    w, h = original_surf.get_size()
    new_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    new_arr_rgb = pygame.surfarray.pixels3d(new_surf)
    new_arr_alpha = pygame.surfarray.pixels_alpha(new_surf)
    for x in range(w):
        for y in range(h):
            r = arr_rgb[x, y, 0]
            g = arr_rgb[x, y, 1]
            b = arr_rgb[x, y, 2]
            a = arr_alpha[x, y]
            h_, s_, v_ = rgb_to_hsv(r, g, b)
            r2, g2, b2 = hsv_to_rgb(hue_value % 360, s_, v_)
            new_arr_rgb[x, y, 0] = r2
            new_arr_rgb[x, y, 1] = g2
            new_arr_rgb[x, y, 2] = b2
            new_arr_alpha[x, y] = a
    del arr_rgb, arr_alpha, new_arr_rgb, new_arr_alpha
    return new_surf

def safe_shift_surface_hue(surf, hue_value):
    try:
        if surf is None:
            debug_print("safe_shift_surface_hue called with None-surface.")
            return None
        w, h = surf.get_size()
        debug_print("Applying hue shift to background " + str(w) + "x" + str(h) + " with hue=" + str(hue_value))
        return shift_surface_hue(surf, hue_value)
    except Exception as e:
        debug_print("Error in shift_surface_hue: " + traceback.format_exc())
        debug_print("Falling back to original surface.")
        return surf

class Wind:
    def __init__(self):
        self.angle = random.uniform(0, 2*math.pi)
        self.strength = random.uniform(0.0, 0.2)
        self.change_timer = 0.0
    def update(self, dt):
        self.change_timer -= dt
        if self.change_timer <= 0:
            self.change_timer = random.uniform(1.5, 4.0)
            self.angle += random.uniform(-0.3, 0.3)
            self.strength += random.uniform(-0.05, 0.05)
            self.strength = max(0, min(0.6, self.strength))
    def apply_to_ball(self, ball):
        wind_x = math.cos(self.angle)*self.strength
        ball.vel.x += wind_x
    def draw(self, screen):
        cx = SCREEN_WIDTH - 60
        cy = 60
        radius = 40
        pygame.draw.circle(screen, (50,50,50), (cx,cy), radius, width=2)
        arrow_len = int(radius * self.strength * 2) + 5
        end_x = cx + arrow_len * math.cos(self.angle)
        end_y = cy + arrow_len * math.sin(self.angle)
        pygame.draw.line(screen, (200,200,0), (cx,cy), (end_x,end_y), width=3)

bounce_sounds = []
bounce_index = 0
border_sound = None
panel_sound = None
button_sound = None

def play_bounce_sound():
    global bounce_index
    if bounce_sounds:
        bounce_sounds[bounce_index].play()
        bounce_index = min(bounce_index + 1, len(bounce_sounds)-1)

def play_border_sound():
    if border_sound:
        border_sound.play()

def play_panel_sound():
    if panel_sound:
        panel_sound.play()

def play_button_sound():
    if button_sound:
        button_sound.play()

class Flipper(pygame.sprite.Sprite):
    def __init__(self, side, pivot_pos, length=60):
        super().__init__()
        self.side = side
        self.angle = 0
        self.pivot = pivot_pos
        self.length = length
        self.angle_up = 45 if side=="left" else -45
        self.rotating = False
        self.time_since_flip = 0.0
        self.flip_duration = 0.15
        self.original_image = None
        self.mask = None
        self.image = None
        self.rect = None
        self._load_or_build_image()
        self._update_rotation()
    def _load_or_build_image(self):
        data_dir = os.path.join(os.getcwd(), "data")
        if self.side=="left" and os.path.exists(os.path.join(data_dir, "panel_left.png")):
            self.original_image = pygame.image.load(os.path.join(data_dir, "panel_left.png")).convert_alpha()
        elif self.side=="right" and os.path.exists(os.path.join(data_dir, "panel_right.png")):
            self.original_image = pygame.image.load(os.path.join(data_dir, "panel_right.png")).convert_alpha()
        else:
            w = self.length
            h = 15
            surf = pygame.Surface((w,h), pygame.SRCALPHA)
            color = (200,200,200)
            pygame.draw.rect(surf, color, (0,0,w,h), border_radius=5)
            self.original_image = surf
    def trigger_flip(self):
        self.rotating = True
        self.time_since_flip = 0.0
    def _update_rotation(self):
        rotated = pygame.transform.rotate(self.original_image, self.angle)
        w, h = rotated.get_size()
        if self.side=="left":
            pivot_offset = (w, h//2)
        else:
            pivot_offset = (0, h//2)
        self.rect = rotated.get_rect()
        self.rect.topleft = (self.pivot[0] - pivot_offset[0], self.pivot[1] - pivot_offset[1])
        self.image = rotated
        self.mask = pygame.mask.from_surface(rotated)
    def update(self, dt, ball):
        if self.rotating:
            self.time_since_flip += dt
            alpha = self.time_since_flip / self.flip_duration
            if alpha < 1.0:
                self.angle = alpha*self.angle_up
            else:
                self.rotating=False
                self.angle=0
            self._update_rotation()
        if pygame.sprite.collide_mask(ball, self):
            if self.side in ("left","right"):
                ball.vel.x = -ball.vel.x
            play_panel_sound()

class Hole(pygame.sprite.Sprite):
    def __init__(self, pos, w, h, hole_surf=None, hole_mask=None):
        super().__init__()
        self.pos = pos
        self.width = w
        self.height = h
        self.original_surf = hole_surf
        self.original_mask = hole_mask
        self.image = None
        self.mask = None
        self.rect = None
        self._update_surface(w,h)
    def _update_surface(self, w,h):
        if self.original_surf:
            new_surf = pygame.transform.scale(self.original_surf, (w,h))
            self.image = new_surf
            self.mask = pygame.mask.from_surface(new_surf)
            self.rect = self.image.get_rect(midtop=self.pos)
        else:
            surf = pygame.Surface((w,h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (0,255,0,50), (0,0,w,h), border_radius=10)
            self.image = surf
            self.mask = pygame.mask.from_surface(surf)
            self.rect = self.image.get_rect(midtop=self.pos)
    def enlarge(self, amount=10):
        self.width += amount
        self._update_surface(self.width, self.height)

class Bumper(pygame.sprite.Sprite):
    def __init__(self, pos, surf, mask):
        super().__init__()
        self.image = surf
        self.mask = mask
        self.rect = self.image.get_rect(center=pos)
    def on_hit(self):
        self.kill()

class Ball(pygame.sprite.Sprite):
    def __init__(self, pos, ball_surf, ball_mask):
        super().__init__()
        self.original_image = ball_surf
        self.image = self.original_image.copy()
        self.mask = ball_mask
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(0,0)
        self.fired = False
        self.active = True
        self.bottom_bounce_count = 0
    def update(self):
        if not self.fired or not self.active:
            return
        self.vel.y += GRAVITY * BALL_SPEED_MODIFIER
        self.pos += self.vel * BALL_SPEED_MODIFIER
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if self.rect.left < 0:
            self.rect.left = 0
            self.pos.x = self.rect.centerx
            self.vel.x = -self.vel.x
            play_border_sound()
            self.bottom_bounce_count = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.pos.x = self.rect.centerx
            self.vel.x = -self.vel.x
            play_border_sound()
            self.bottom_bounce_count = 0
        if self.rect.top < 0:
            self.rect.top = 0
            self.pos.y = self.rect.centery
            self.vel.y = -self.vel.y
            play_border_sound()
            self.bottom_bounce_count = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.pos.y = self.rect.centery
            self.vel.y = -self.vel.y
            play_border_sound()
            self.bottom_bounce_count += 1

def place_bumpers(bumper_count, bumper_surf, bumper_mask):
    bumpers = pygame.sprite.Group()
    attempts = 0
    max_attempts = 500
    radius_estimate = bumper_surf.get_width() // 2
    debug_print("Placing " + str(bumper_count) + " bumpers with radius estimate " + str(radius_estimate) + ".")
    while len(bumpers) < bumper_count and attempts < max_attempts:
        x = random.randint(150, SCREEN_WIDTH - 150)
        y = random.randint(100, SCREEN_HEIGHT // 2)
        candidate = Bumper((x,y), bumper_surf, bumper_mask)
        overlap = False
        for b in bumpers:
            dx = b.rect.centerx - candidate.rect.centerx
            dy = b.rect.centery - candidate.rect.centery
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < radius_estimate*2:
                overlap = True
                break
        if not overlap:
            bumpers.add(candidate)
        attempts += 1
    if len(bumpers) < bumper_count:
        debug_print("Could only place " + str(len(bumpers)) + " bumpers (wanted " + str(bumper_count) + ").")
    else:
        debug_print("Successfully placed " + str(len(bumpers)) + " bumpers.")
    return bumpers

def make_pre_darkened_copy(original, brightness):
    if original is None:
        return None
    w, h = original.get_size()
    copy_surf = original.copy()
    if brightness >= 1.0:
        return copy_surf
    alpha_val = int((1.0 - brightness)*255)
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0,0,0,alpha_val))
    copy_surf.blit(overlay, (0,0))
    return copy_surf

def main():
    again = True
    while again:
        debug_print("Starting new main loop iteration.")
        ensure_data_folder()
        try:
            pygame.mixer.pre_init(44100, -16, 1)
            pygame.init()
            pygame.mixer.init()
            debug_print("Pygame and mixer initialized successfully.")
        except Exception as e:
            debug_print("Error initializing Pygame or mixer: " + str(e))
            sys.exit(1)
        info = pygame.display.Info()
        global SCREEN_WIDTH, SCREEN_HEIGHT
        SCREEN_WIDTH = info.current_w
        SCREEN_HEIGHT = info.current_h
        debug_print("Detected screen size: " + str(SCREEN_WIDTH) + "x" + str(SCREEN_HEIGHT))
        try:
            screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        except Exception as e:
            debug_print("Error setting fullscreen mode: " + str(e))
            sys.exit(1)
        pygame.display.set_caption("OpenSource-Pinball-like-Game")
        clock = pygame.time.Clock()
        global FONT_NAME
        FONT_NAME = pygame.font.get_default_font()
        font_big = pygame.font.SysFont(FONT_NAME, 60)
        font_small = pygame.font.SysFont(FONT_NAME, 30)
        load_music_files_from_data()
        load_all_background_images()
        check_and_play_music()
        data_dir = os.path.join(os.getcwd(), "data")
        original_background_surf = None
        if os.path.exists(os.path.join(data_dir, "background.png")):
            try:
                original_background_surf = pygame.image.load(os.path.join(data_dir, "background.png")).convert_alpha()
                debug_print("Loaded background.png successfully.")
            except Exception as e:
                debug_print("Error loading background.png: " + str(e))
        else:
            debug_print("No background.png found. Using plain color fill.")
        if os.path.exists(os.path.join(data_dir, "bumper.png")):
            try:
                bumper_surf, bumper_mask, _ = load_image_with_mask(os.path.join(data_dir, "bumper.png"))
                debug_print("Loaded bumper.png successfully.")
            except Exception as e:
                debug_print("Error loading bumper.png: " + str(e))
                bumper_surf, bumper_mask = get_alpha_mask_circle(20, color=(255,100,100))
        else:
            debug_print("No bumper.png found. Using fallback circle for bumpers.")
            bumper_surf, bumper_mask = get_alpha_mask_circle(20, color=(255,100,100))
        if os.path.exists(os.path.join(data_dir, "ball.png")):
            try:
                ball_surf, ball_mask, _ = load_image_with_mask(os.path.join(data_dir, "ball.png"))
                debug_print("Loaded ball.png successfully.")
            except Exception as e:
                debug_print("Error loading ball.png: " + str(e))
                ball_surf, ball_mask = get_alpha_mask_circle(10, color=(120,120,120))
        else:
            debug_print("No ball.png found. Using fallback circle for ball.")
            ball_surf, ball_mask = get_alpha_mask_circle(10, color=(120,120,120))
        hole_surf = None
        hole_mask = None
        if os.path.exists(os.path.join(data_dir, "hole.png")):
            try:
                hole_surf, hole_mask, _ = load_image_with_mask(os.path.join(data_dir, "hole.png"))
                debug_print("Loaded hole.png successfully.")
            except Exception as e:
                debug_print("Error loading hole.png: " + str(e))
                hole_surf = None
                hole_mask = None
        else:
            debug_print("No hole.png found. Will use fallback rect for holes.")
        corner_surf = None
        if os.path.exists(os.path.join(data_dir, "corner.png")):
            try:
                corner_surf = pygame.image.load(os.path.join(data_dir, "corner.png")).convert_alpha()
                debug_print("Loaded corner.png successfully.")
            except Exception as e:
                debug_print("Error loading corner.png: " + str(e))
        holes_group = pygame.sprite.Group()
        flipper_group = pygame.sprite.Group()
        gap = SCREEN_WIDTH // (HOLES_COUNT+1)
        hole_width = 80
        hole_height = 30
        hole_positions = []
        for i in range(HOLES_COUNT):
            pos_x = (i+1)*gap
            pos_y = SCREEN_HEIGHT - 80
            hole_obj = Hole((pos_x, pos_y), hole_width, hole_height, hole_surf, hole_mask)
            holes_group.add(hole_obj)
            hole_positions.append((pos_x, pos_y))
            lf_pivot = (pos_x - hole_width//2, pos_y+10)
            left_flipper = Flipper("left", lf_pivot, length=60)
            flipper_group.add(left_flipper)
            rf_pivot = (pos_x + hole_width//2, pos_y+10)
            right_flipper = Flipper("right", rf_pivot, length=60)
            flipper_group.add(right_flipper)
        global bounce_sounds, bounce_index, border_sound, panel_sound, button_sound
        bounce_sounds = []
        bounce_index = 0
        bumper_wav = os.path.join(data_dir,"bumper.wav")
        pitch_steps = 15
        if os.path.exists(bumper_wav):
            debug_print("Found bumper.wav. Attempting pitch shifts up to " + str(pitch_steps))
            tested_pitch_shift = pitch_shift_wav(bumper_wav, 0.0)
            if tested_pitch_shift is not None:
                for i in range(pitch_steps):
                    raw_data = pitch_shift_wav(bumper_wav, i*0.35)
                    if raw_data is not None:
                        s = pygame.mixer.Sound(buffer=raw_data)
                        bounce_sounds.append(s)
                    else:
                        one_sound = pygame.mixer.Sound(bumper_wav)
                        bounce_sounds.append(one_sound)
            else:
                debug_print("Pitch shift unavailable. Using non-shifted bumper.wav repeatedly.")
                one_sound = pygame.mixer.Sound(bumper_wav)
                bounce_sounds = [one_sound]*pitch_steps
        else:
            debug_print("No bumper.wav found. Generating sine waves.")
            base_freq = 220
            for i in range(pitch_steps):
                freq = base_freq*(1.04**i)
                s = create_sine_wave(freq,200,0.3)
                bounce_sounds.append(s)
        if not bounce_sounds:
            debug_print("No bounce sounds => adding fallback sine wave.")
            bounce_sounds.append(create_sine_wave(220,200,0.3))
        border_sound = None
        border_wav = os.path.join(data_dir,"border.wav")
        if os.path.exists(border_wav):
            try:
                border_sound = pygame.mixer.Sound(border_wav)
                debug_print("border.wav loaded.")
            except Exception as e:
                debug_print("Failed to load border.wav: " + str(e))
                border_sound = create_sine_wave(80,150,0.4)
        else:
            debug_print("No border.wav => fallback sine wave.")
            border_sound = create_sine_wave(80,150,0.4)
        panel_sound = None
        panel_wav = os.path.join(data_dir,"panel.wav")
        if os.path.exists(panel_wav):
            try:
                panel_sound = pygame.mixer.Sound(panel_wav)
                debug_print("panel.wav loaded.")
            except Exception as e:
                debug_print("Failed panel.wav => fallback.")
                panel_sound = create_sine_wave(100,200,0.4)
        else:
            debug_print("No panel.wav => fallback.")
            panel_sound = create_sine_wave(100,200,0.4)
        button_sound = None
        button_wav = os.path.join(data_dir,"button.wav")
        if os.path.exists(button_wav):
            try:
                button_sound = pygame.mixer.Sound(button_wav)
                debug_print("button.wav loaded.")
            except Exception as e:
                debug_print("Failed button.wav => no button sound.")
        wind = Wind()
        total_score = 0
        level = 1
        running = True
        color_cycle_start_time = 0.0
        old_hue = 0.0
        new_hue = HUE_SHIFT_STEP
        next_hue_update = 0.0
        bg_interpolated_surf = None
        global IS_PAUSED, SHOW_OPTIONS, BRIGHTNESS, MUSIC_VOLUME
        orgon_button_state = "HIDDEN"
        orgon_button_timer = 0.0
        repulsine_button_state = "HIDDEN"
        repulsine_button_timer = 0.0
        ORGON_BUTTON_VISIBLE_TIME = 30.0
        ORGON_BUTTON_HIDDEN_TIME = 30.0
        REPULSINE_BUTTON_VISIBLE_TIME = 20.0
        REPULSINE_BUTTON_HIDDEN_TIME = 20.0
        orgon_button_width = 140
        orgon_button_height = 50
        repulsine_button_width = 140
        repulsine_button_height = 50
        orgon_button_rect = pygame.Rect(SCREEN_WIDTH - orgon_button_width - 10, SCREEN_HEIGHT - orgon_button_height - 10, orgon_button_width, orgon_button_height)
        repulsine_button_rect = pygame.Rect(SCREEN_WIDTH - repulsine_button_width - 10, SCREEN_HEIGHT - orgon_button_height - 10 - repulsine_button_height - 10, repulsine_button_width, repulsine_button_height)
        options_button_rect = pygame.Rect(10, SCREEN_HEIGHT - 60, 140, 50)
        brightness_slider_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 - 30, 300, 20)
        music_slider_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 30, 300, 20)
        dragging_slider = None
        while running:
            if BG_IMAGES:
                BG_INDEX = (level - 1) % len(BG_IMAGES)
                debug_print("Using background index " + str(BG_INDEX) + "/" + str(len(BG_IMAGES)))
            bumper_group = place_bumpers(level, bumper_surf, bumper_mask)
            shots_left = MAX_SHOTS
            level_score = 0
            ball = Ball((SCREEN_WIDTH//2,50), ball_surf, ball_mask)
            ball_group = pygame.sprite.GroupSingle(ball)
            level_active = True
            if BG_IMAGES:
                current_level_bg = BG_IMAGES[BG_INDEX]
            else:
                current_level_bg = original_background_surf
            pre_dark_bg = make_pre_darkened_copy(current_level_bg, BRIGHTNESS)
            while running and level_active:
                dt = clock.tick(FPS)/1000.0
                check_and_play_music()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        debug_print("QUIT event")
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            debug_print("ESC => exit")
                            running = False
                        elif event.key in (pygame.K_LEFT, pygame.K_w):
                            if not IS_PAUSED:
                                for f in flipper_group:
                                    if f.side=="left":
                                        f.trigger_flip()
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            if not IS_PAUSED:
                                for f in flipper_group:
                                    if f.side=="right":
                                        f.trigger_flip()
                        elif event.key == pygame.K_p:
                            IS_PAUSED = not IS_PAUSED
                            debug_print("Paused toggled => " + str(IS_PAUSED))
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            if options_button_rect.collidepoint(event.pos):
                                play_button_sound()
                                SHOW_OPTIONS = not SHOW_OPTIONS
                                if SHOW_OPTIONS:
                                    IS_PAUSED = True
                                else:
                                    IS_PAUSED = False
                                pre_dark_bg = make_pre_darkened_copy(current_level_bg, BRIGHTNESS)
                            else:
                                if SHOW_OPTIONS:
                                    if brightness_slider_rect.collidepoint(event.pos):
                                        dragging_slider = "brightness"
                                    elif music_slider_rect.collidepoint(event.pos):
                                        dragging_slider = "music"
                                else:
                                    if not IS_PAUSED:
                                        if orgon_button_state == "VISIBLE" and orgon_button_rect.collidepoint(event.pos):
                                            play_button_sound()
                                            wind.angle = random.uniform(0, 2 * math.pi)
                                            wind.strength = random.uniform(0.0, 0.6)
                                            orgon_button_state = "HIDDEN"
                                            orgon_button_timer = 0.0
                                        elif repulsine_button_state == "VISIBLE" and repulsine_button_rect.collidepoint(event.pos):
                                            play_button_sound()
                                            if ball.fired and ball.active:
                                                ball.vel.y = -abs(ball.vel.y) * 2.0
                                            repulsine_button_state = "HIDDEN"
                                            repulsine_button_timer = 0.0
                                        elif not ball.fired and shots_left > 0:
                                            mx, my = pygame.mouse.get_pos()
                                            dx = mx - ball.pos.x
                                            dy = my - ball.pos.y
                                            angle = math.atan2(dy,dx)
                                            speed = 25 * BALL_SPEED_MODIFIER
                                            ball.vel.x = speed*math.cos(angle)
                                            ball.vel.y = speed*math.sin(angle)
                                            ball.fired = True
                                            shots_left -= 1
                                            bounce_index = 0
                                            debug_print("Ball fired angle " + str(angle) + " speed " + str(speed))
                                        else:
                                            for f in flipper_group:
                                                if f.side=="left":
                                                    f.trigger_flip()
                        elif event.button == 3:
                            if not IS_PAUSED and not SHOW_OPTIONS:
                                for f in flipper_group:
                                    if f.side=="right":
                                        f.trigger_flip()
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            dragging_slider = None
                    elif event.type == pygame.MOUSEMOTION:
                        if SHOW_OPTIONS and dragging_slider is not None:
                            mx, my = event.pos
                            if dragging_slider == "brightness":
                                rel_x = mx - brightness_slider_rect.x
                                rel_x = max(0, min(rel_x, brightness_slider_rect.width))
                                BRIGHTNESS = rel_x / brightness_slider_rect.width
                                pre_dark_bg = make_pre_darkened_copy(current_level_bg, BRIGHTNESS)
                                debug_print("BRIGHTNESS => " + str(BRIGHTNESS))
                            elif dragging_slider == "music":
                                rel_x = mx - music_slider_rect.x
                                rel_x = max(0, min(rel_x, music_slider_rect.width))
                                MUSIC_VOLUME = rel_x / music_slider_rect.width
                                pygame.mixer.music.set_volume(MUSIC_VOLUME)
                                debug_print("MUSIC_VOLUME => " + str(MUSIC_VOLUME))
                if not NOSPOON_MODE:
                    if not IS_PAUSED:
                        orgon_button_timer += dt
                        if orgon_button_state == "HIDDEN":
                            if orgon_button_timer >= 30.0:
                                orgon_button_state = "VISIBLE"
                                orgon_button_timer = 0.0
                        elif orgon_button_state == "VISIBLE":
                            if orgon_button_timer >= 30.0:
                                orgon_button_state = "HIDDEN"
                                orgon_button_timer = 0.0
                        repulsine_button_timer += dt
                        if repulsine_button_state == "HIDDEN":
                            if repulsine_button_timer >= 20.0:
                                repulsine_button_state = "VISIBLE"
                                repulsine_button_timer = 0.0
                        elif repulsine_button_state == "VISIBLE":
                            if repulsine_button_timer >= 20.0:
                                repulsine_button_state = "HIDDEN"
                                repulsine_button_timer = 0.0
                if not IS_PAUSED:
                    wind.update(dt)
                    if ball.fired and ball.active:
                        wind.apply_to_ball(ball)
                    ball_group.update()
                    for f in flipper_group:
                        f.update(dt, ball)
                    for bump in bumper_group:
                        if pygame.sprite.collide_mask(ball, bump):
                            debug_print("Collision => +50")
                            level_score += 50
                            ball.vel.y = -ball.vel.y
                            bump.on_hit()
                            play_bounce_sound()
                            ball.bottom_bounce_count = 0
                    for hobj in holes_group:
                        if ball.rect.colliderect(hobj.rect):
                            debug_print("Ball => hole => -25")
                            level_score -= 25
                            ball.active = False
                            ball_group.empty()
                            ball.bottom_bounce_count = 0
                            break
                    if not ball.active and len(ball_group)==0:
                        debug_print("Ball inactive => new ball top")
                        ball = Ball((SCREEN_WIDTH//2,50), ball_surf, ball_mask)
                        ball_group.add(ball)
                    if ball.bottom_bounce_count >= 5:
                        debug_print("bottom bounce too often => enlarge holes")
                        for hobj in holes_group:
                            hobj.enlarge(10)
                        ball.bottom_bounce_count = 0
                    if len(bumper_group) == 0:
                        total_score += level_score
                        debug_print("Level " + str(level) + " complete => total " + str(total_score))
                        txt = font_big.render("Level " + str(level) + " complete (score change: " + str(level_score) + ")", True, (255,255,255))
                        screen.fill((0,0,0))
                        screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2))
                        pygame.display.flip()
                        pygame.time.wait(2000)
                        level += 1
                        level_active = False
                        continue
                    if shots_left <= 0 and not ball.fired and len(bumper_group) > 0:
                        debug_print("Out of shots => Game Over")
                        msg = font_big.render("Game Over", True, (255,50,50))
                        info = font_small.render("Score: " + str(total_score), True, (255,255,255))
                        screen.fill((0,0,0))
                        screen.blit(msg, (SCREEN_WIDTH//2-msg.get_width()//2,SCREEN_HEIGHT//2-40))
                        screen.blit(info,(SCREEN_WIDTH//2-info.get_width()//2,SCREEN_HEIGHT//2+20))
                        again_surf = font_small.render("Again? y/n", True, (255,255,255))
                        screen.blit(again_surf, (SCREEN_WIDTH//2-again_surf.get_width()//2, SCREEN_HEIGHT//2+60))
                        pygame.display.flip()
                        log_score(total_score)
                        asking = True
                        while asking:
                            for ev in pygame.event.get():
                                if ev.type == pygame.KEYDOWN:
                                    if ev.key == pygame.K_y:
                                        debug_print("User => play again")
                                        shots_left = MAX_SHOTS
                                        total_score = 0
                                        level = 1
                                        asking = False
                                        break
                                    elif ev.key == pygame.K_n:
                                        debug_print("User => not again => exit")
                                        running = False
                                        asking = False
                                        break
                        break
                if BG_COLOR_CYCLE == 1 and original_background_surf:
                    current_time = time.time()
                    elapsed = current_time - color_cycle_start_time
                    if elapsed > COLOR_CYCLE_INTERVAL:
                        old_hue = new_hue
                        new_hue = (old_hue + HUE_SHIFT_STEP) % 360
                        color_cycle_start_time = current_time
                        elapsed = 0.0
                    if elapsed < COLOR_CYCLE_FADE_DURATION:
                        alpha = elapsed / COLOR_CYCLE_FADE_DURATION
                        current_hue = (1 - alpha)*old_hue + alpha*new_hue
                    else:
                        current_hue = new_hue
                    if current_time >= next_hue_update:
                        next_hue_update = current_time + 1.0 / COLOR_SHIFT_FPS
                        bg_interpolated_surf = safe_shift_surface_hue(original_background_surf, current_hue)
                    if bg_interpolated_surf:
                        bg_scaled = pygame.transform.scale(bg_interpolated_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                        screen.blit(bg_scaled,(0,0))
                    else:
                        screen.fill((0,0,0))
                else:
                    if pre_dark_bg:
                        bg_scaled = pygame.transform.scale(pre_dark_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                        screen.blit(bg_scaled,(0,0))
                    else:
                        screen.fill((0,0,0))
                bumper_group.draw(screen)
                holes_group.draw(screen)
                flipper_group.draw(screen)
                if corner_surf:
                    sorted_positions = sorted(hole_positions, key=lambda p: p[0])
                    for i in range(len(sorted_positions)-1):
                        left_x = sorted_positions[i][0]
                        right_x = sorted_positions[i+1][0]
                        mid_x = (left_x+right_x)//2
                        y = SCREEN_HEIGHT - 80
                        c_rect = corner_surf.get_rect(midtop=(mid_x,y))
                        screen.blit(corner_surf, c_rect)
                ball_group.draw(screen)
                wind.draw(screen)
                lvl_surf = font_small.render("Level: " + str(level), True, (255,255,255))
                screen.blit(lvl_surf,(10,10))
                shot_surf = font_small.render("Shots left: " + str(shots_left), True, (255,255,255))
                screen.blit(shot_surf,(10,40))
                score_surf = font_small.render("Score: " + str(total_score+level_score), True, (255,255,255))
                screen.blit(score_surf,(10,70))
                pygame.draw.rect(screen, (180,180,180), options_button_rect, border_radius=8)
                opt_txt = font_small.render("Options", True, (0,0,0))
                screen.blit(opt_txt, (options_button_rect.centerx - opt_txt.get_width()/2, options_button_rect.centery - opt_txt.get_height()/2))
                if not NOSPOON_MODE:
                    if orgon_button_state == "VISIBLE":
                        pygame.draw.rect(screen, (150,220,150), orgon_button_rect, border_radius=8)
                        line1 = font_small.render("Orgon", True, (0,0,0))
                        line2 = font_small.render("Akkumulator", True, (0,0,0))
                        screen.blit(line1, (orgon_button_rect.centerx - line1.get_width()/2, orgon_button_rect.y + 5))
                        screen.blit(line2, (orgon_button_rect.centerx - line2.get_width()/2, orgon_button_rect.y + 5 + line1.get_height()))
                    if repulsine_button_state == "VISIBLE":
                        pygame.draw.rect(screen, (150,150,220), repulsine_button_rect, border_radius=8)
                        repulsine_txt = font_small.render("Repulsine", True, (0,0,0))
                        screen.blit(repulsine_txt, (repulsine_button_rect.centerx - repulsine_txt.get_width()/2, repulsine_button_rect.centery - repulsine_txt.get_height()/2))
                if SHOW_OPTIONS:
                    menu_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    menu_bg.fill((50,50,50,200))
                    screen.blit(menu_bg, (0,0))
                    menu_title = font_big.render("OPTIONS", True, (255,255,255))
                    screen.blit(menu_title, (SCREEN_WIDTH//2 - menu_title.get_width()//2, SCREEN_HEIGHT//2 - 100))
                    pygame.draw.rect(screen, (200,200,200), brightness_slider_rect)
                    fill_w = int(brightness_slider_rect.width * BRIGHTNESS)
                    fill_rect = pygame.Rect(brightness_slider_rect.x, brightness_slider_rect.y, fill_w, brightness_slider_rect.height)
                    pygame.draw.rect(screen, (0,255,0), fill_rect)
                    bri_label = font_small.render("Brightness: " + str(int(BRIGHTNESS*100)) + "%", True, (255,255,255))
                    screen.blit(bri_label, (brightness_slider_rect.centerx - bri_label.get_width()//2, brightness_slider_rect.y - 25))
                    pygame.draw.rect(screen, (200,200,200), music_slider_rect)
                    fill_w2 = int(music_slider_rect.width * MUSIC_VOLUME)
                    fill2_rect = pygame.Rect(music_slider_rect.x, music_slider_rect.y, fill_w2, music_slider_rect.height)
                    pygame.draw.rect(screen, (0,255,0), fill2_rect)
                    vol_label = font_small.render("Music Volume: " + str(int(MUSIC_VOLUME*100)) + "%", True, (255,255,255))
                    screen.blit(vol_label, (music_slider_rect.centerx - vol_label.get_width()//2, music_slider_rect.y - 25))
                pygame.display.flip()
        pygame.quit()
        debug_print("Pygame quit. Exiting application.")
        sys.exit()

if __name__=="__main__":
    main()
