import os
import pygame
import csv
import random
import requests
import json
import heapq

# Initialize Pygame
pygame.init()

# Constants
TILE_SIZE = 32  # 16 * 2
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 1200
MAP_WIDTH = 100  # Width of the map in tiles
MAP_HEIGHT = 80  # Height of the map in tiles
WATER_TILE_ID = 283
DEFAULT_TILE_ID = 405
WALKABLE_TILE_IDS = [405, 365, 1201, 532, 326, 286, 246, 0]  # List of walkable tile IDs
BLOOD_SPLAT_FADE_DURATION = 1800  # Frames for 30 seconds at 60 FPS
CHICKEN_SPAWN_TILE_ID = 293

# Day/night cycle constants
DAY_DURATION = 20 * 60  # 5 real-time minutes (300 seconds)
NIGHT_COLOR = (0, 0, 50)  # Dark blue color for night
TRANSITION_DURATION = 120  # Transition duration for sunset/sunrise (1 second)

# Load images
tileset = pygame.image.load('Overworld.png')
blood_puddle_image = pygame.image.load('blood_puddle.png')
character_tileset = pygame.image.load('character.png')
character_sword = pygame.image.load('character_sword.png')
blood_splat_tileset = pygame.image.load('blood_hit.png')
cow_tileset = pygame.image.load('cow_walk.png')
chicken_tileset = pygame.image.load('chicken_walk.png')
pig_tileset = pygame.image.load('pig_walk.png')
wizard_tileset = pygame.image.load('wizard.png')  # Load wizard tileset

# Function to get tile image from tileset
def get_tile_image(tileset, tile_id):
    tile_x = (tile_id % (tileset.get_width() // (TILE_SIZE // 2))) * (TILE_SIZE // 2)
    tile_y = (tile_id // (tileset.get_width() // (TILE_SIZE // 2))) * (TILE_SIZE // 2)
    tile_image = tileset.subsurface(pygame.Rect(tile_x, tile_y, TILE_SIZE // 2, TILE_SIZE // 2))
    return pygame.transform.scale(tile_image, (TILE_SIZE, TILE_SIZE))

# Default tile
default_tile = get_tile_image(tileset, DEFAULT_TILE_ID)


# Function to draw blood puddle
def draw_blood_puddle(map_surface, blood_puddle_image, x, y, scale_factor, map_data):
    tile_x = x // TILE_SIZE
    tile_y = y // TILE_SIZE
    if map_data.map_data[tile_y][tile_x] in WALKABLE_TILE_IDS:  # Access map_data attribute
        scaled_image = pygame.transform.scale(blood_puddle_image, (
            int(blood_puddle_image.get_width() * scale_factor), int(blood_puddle_image.get_height() * scale_factor)))
        random_angle = random.uniform(0, 360)
        rotated_image = pygame.transform.rotate(scaled_image, random_angle)
        offset_x = x + TILE_SIZE // 2 - rotated_image.get_width() // 2
        offset_y = y + TILE_SIZE // 2 - rotated_image.get_height() // 2
        map_surface.blit(rotated_image, (offset_x, offset_y))



def find_tile_position(map_data, tile_id):
    for y, row in enumerate(map_data.map_data):
        for x, tile in enumerate(row):
            if tile == tile_id:
                return x * TILE_SIZE, y * TILE_SIZE
    return None

# Map class
class Map:
    def __init__(self, filename, tileset, default_tile):
        self.map_data = self.load_map(filename)
        self.tileset = tileset
        self.default_tile = default_tile
        self.surface = pygame.Surface((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
        self.draw_map()

    def load_map(self, filename):
        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            return [list(map(int, row)) for row in reader]

    def is_walkable(self, x, y, character_width, character_height):
        center_x = x + character_width // 2
        center_y = y + character_height // 2
        tile_x = center_x // TILE_SIZE
        tile_y = center_y // TILE_SIZE
        if tile_x < 0 or tile_x >= MAP_WIDTH or tile_y < 0 or tile_y >= MAP_HEIGHT or self.map_data[tile_y][tile_x] not in WALKABLE_TILE_IDS:
            return False
        return True

    def draw_map(self):
        for y, row in enumerate(self.map_data):
            for x, tile in enumerate(row):
                self.surface.blit(self.default_tile, (x * TILE_SIZE, y * TILE_SIZE))
                if tile >= 0:
                    tile_image = get_tile_image(self.tileset, tile)
                    self.surface.blit(tile_image, (x * TILE_SIZE, y * TILE_SIZE))

# Character class
class Character:
    def __init__(self, tileset, sword_tileset, blood_splat_frames, x, y):
        self.tileset = tileset
        self.sword_tileset = sword_tileset
        self.blood_splat_frames = blood_splat_frames
        self.x = x
        self.y = y
        self.width = 32
        self.height = 64
        self.direction = 0
        self.frame = 0
        self.frame_counter = 0
        self.animation_speed = 10
        self.speed = 4
        self.attacking = False
        self.attack_duration = 20
        self.attack_counter = 0
        self.walk_frames = self.load_frames(self.tileset, self.width, self.height)
        self.jump_frames = self.load_frames(self.tileset, self.width, self.height, offset_x=80)
        self.attack_frames = self.load_frames(self.sword_tileset, 64, 64)
        self.offset_x, self.offset_y = 0, 0

    def load_frames(self, tileset, frame_width, frame_height, offset_x=0):
        frames = [[], [], [], []]
        for direction in range(4):
            for frame in range(4):
                rect = pygame.Rect(frame * (frame_width // 2) + offset_x, direction * (frame_height // 2), frame_width // 2, frame_height // 2)
                frames[direction].append(pygame.transform.scale(tileset.subsurface(rect), (frame_width, frame_height)))
        return frames

    def update(self, keys, map_data):
        moving = False
        jumping = False
        new_x, new_y = self.x, self.y

        if keys[pygame.K_SPACE]:
            jumping = True

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= self.speed
            self.direction = 3
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += self.speed
            self.direction = 1
            moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= self.speed
            self.direction = 2
            moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += self.speed
            self.direction = 0
            moving = True

        if map_data.is_walkable(new_x, new_y, self.width, self.height):
            self.x, self.y = new_x, new_y
        else:
            self.frame = 0

        self.x = max(0, min(self.x, MAP_WIDTH * TILE_SIZE - self.width))
        self.y = max(0, min(self.y, MAP_HEIGHT * TILE_SIZE - self.height))

        if self.x - self.offset_x < SCREEN_WIDTH // 4:
            self.offset_x = max(0, self.x - SCREEN_WIDTH // 4)
        if self.x - self.offset_x > SCREEN_WIDTH * 3 // 4:
            self.offset_x = min(MAP_WIDTH * TILE_SIZE - SCREEN_WIDTH, self.x - SCREEN_WIDTH * 3 // 4)
        if self.y - self.offset_y < SCREEN_HEIGHT // 4:
            self.offset_y = max(0, self.y - SCREEN_HEIGHT // 4)
        if self.y - self.offset_y > SCREEN_HEIGHT * 3 // 4:
            self.offset_y = min(MAP_HEIGHT * TILE_SIZE - SCREEN_HEIGHT, self.y - SCREEN_HEIGHT * 3 // 4)

        self.frame_counter += 1
        if self.frame_counter >= self.animation_speed:
            self.frame_counter = 0
            if jumping:
                self.frame = (self.frame + 1) % 3
            elif moving:
                self.frame = (self.frame + 1) % 4
            elif self.attacking:
                self.frame = (self.frame + 1) % 4

    def draw(self, screen):
        if self.attacking:
            screen.blit(self.attack_frames[self.direction][self.frame], (self.x - self.offset_x, self.y - self.offset_y))
        else:
            screen.blit(self.walk_frames[self.direction][self.frame], (self.x - self.offset_x, self.y - self.offset_y))

    def attack(self):
        self.attacking = True
        self.attack_counter = self.attack_duration

    def update_attack(self, npcs, map_surface):
        if self.attacking:
            attack_rect = None
            if self.direction == 0:  # Down
                attack_rect = pygame.Rect(self.x, self.y + self.height, self.width, self.height // 2)
            elif self.direction == 1:  # Right
                attack_rect = pygame.Rect(self.x + self.width, self.y, self.width // 2, self.height)
            elif self.direction == 2:  # Up
                attack_rect = pygame.Rect(self.x, self.y - self.height // 2, self.width, self.height // 2)
            elif self.direction == 3:  # Left
                attack_rect = pygame.Rect(self.x - self.width // 2, self.y, self.width // 2, self.height)

            if attack_rect:
                for npc in npcs:
                    npc_rect = npc.get_rect()
                    if npc_rect.colliderect(attack_rect) and npc.alive:
                        npc.take_damage(1, self.x, self.y, map_surface)

            self.attack_counter -= 1
            if self.attack_counter <= 0:
                self.attacking = False
                self.frame = 0

class NPC:
    def __init__(self, x, y, tileset, tile_size, frame_count, speed, blood_splat_frames):
        self.x = x
        self.y = y
        self.tileset = tileset
        self.tile_size = tile_size
        self.frame_count = frame_count
        self.speed = speed
        self.direction = random.choice([0, 1, 2, 3])
        self.frame = 0
        self.frame_counter = 0
        self.animation_speed = 10
        self.frames = self.load_frames()
        self.hp = 100
        self.alive = True
        self.blood_splat_timer = 0
        self.blood_splat_frames = blood_splat_frames
        self.blood_splat_frame = 0
        self.show_blood_splat = False
        self.blood_splat_offset_x = 0
        self.blood_splat_offset_y = 0
        self.scaled_blood_splat_frames = []
        self.fleeing = False
        self.flee_timer = 0
        self.max_flee_time = 60
        self.moving = False
        self.path = []
        self.target = None  # Add a target attribute

    def load_frames(self):
        frames = [[], [], [], []]
        for direction in range(4):
            for frame in range(self.frame_count):
                rect = pygame.Rect(frame * self.tile_size, direction * self.tile_size, self.tile_size, self.tile_size)
                frames[direction].append(self.tileset.subsurface(rect))
        return frames

    def update(self, map_data, other_npcs, character_rect):
        self.map_data = map_data
        if not self.alive:
            return

        self.moving = False
        if self.fleeing:
            self.flee_timer += 1
            self.speed = random.randint(3, 10)
            if self.flee_timer >= self.max_flee_time:
                self.fleeing = False
                self.speed = 1
                self.flee_timer = 0
            directions = [self.direction, (self.direction + 1) % 4, (self.direction - 1) % 4]
            for direction in directions:
                new_x, new_y = self.x, self.y
                if direction == 0:
                    new_y -= self.speed
                elif direction == 1:
                    new_x -= self.speed
                elif direction == 2:
                    new_y += self.speed
                elif direction == 3:
                    new_x += self.speed

                new_rect = pygame.Rect(new_x, new_y, self.tile_size, self.tile_size)
                if map_data.is_walkable(int(new_x), int(new_y), self.tile_size, self.tile_size):
                    self.x, self.y = new_x, new_y
                    self.direction = direction
                    self.moving = True
                    break
        else:
            if random.random() < 0.01:
                self.direction = random.choice([0, 1, 2, 3])

            new_x, new_y = self.x, self.y
            if self.direction == 2:
                new_y += self.speed
            elif self.direction == 3:
                new_x += self.speed
            elif self.direction == 0:
                new_y -= self.speed
            elif self.direction == 1:
                new_x -= self.speed

            new_rect = pygame.Rect(new_x, new_y, self.tile_size, self.tile_size)
            collision = False
            overlap_area = 0

            for other_npc in other_npcs:
                if other_npc != self:
                    if new_rect.colliderect(other_npc.get_rect()):
                        overlap_rect = new_rect.clip(other_npc.get_rect())
                        overlap_area = overlap_rect.width * overlap_rect.height
                        collision = True
                        #print(f"Collision with NPC, overlap area: {overlap_area}")

                        if overlap_area > 200 and map_data.is_walkable(int(new_x), int(new_y), self.tile_size, self.tile_size):
                            self.x, self.y = new_x, new_y
                            self.moving = True
                        break

            if not collision and map_data.is_walkable(int(new_x), int(new_y), self.tile_size, self.tile_size):
                self.x, self.y = new_x, new_y
                self.moving = True

        self.frame_counter += 1
        if self.frame_counter >= self.animation_speed:
            self.frame_counter = 0
            if self.moving:
                self.frame = (self.frame + 1) % self.frame_count

    def draw(self, screen, offset_x, offset_y):
        if self.alive:
            screen.blit(self.frames[self.direction][self.frame], (self.x - offset_x, self.y - offset_y))

        if self.show_blood_splat:
            screen.blit(self.scaled_blood_splat_frames[self.blood_splat_frame], (self.x - offset_x + self.blood_splat_offset_x, self.y - offset_y + self.blood_splat_offset_y))
            self.blood_splat_timer += 1
            if self.blood_splat_timer >= 3:
                self.blood_splat_timer = 0
                self.blood_splat_frame += 1
                if self.blood_splat_frame >= len(self.scaled_blood_splat_frames):
                    self.show_blood_splat = False

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.tile_size, self.tile_size)

    def take_damage(self, damage, attacker_x, attacker_y, map_surface):
        self.hp -= damage
        if self.hp <= 0:
            self.die()
            scale_factor = .5
            draw_blood_puddle(map_surface, blood_puddle_image, self.x, self.y, scale_factor, self.map_data)  # Pass map_data

        self.show_blood_splat = True
        self.blood_splat_frame = 0
        blood_splat_center_x = self.tile_size // 2
        blood_splat_center_y = self.tile_size // 2
        self.blood_splat_offset_x = blood_splat_center_x - (self.blood_splat_frames[0].get_width() // 2)
        self.blood_splat_offset_y = blood_splat_center_y - (self.blood_splat_frames[0].get_height() // 2)

        scale_factor = random.uniform(1, 2)
        self.scaled_blood_splat_frames = [
            pygame.transform.scale(frame, (int(frame.get_width() * scale_factor), int(frame.get_height() * scale_factor)))
            for frame in self.blood_splat_frames
        ]

        self.fleeing = True
        self.flee_timer = 0
        if attacker_x < self.x:
            self.direction = 3
        elif attacker_x > self.x:
            self.direction = 1
        if attacker_y < self.y:
            self.direction = 2
        elif attacker_y > self.y:
            self.direction = 0



    def die(self):
        self.alive = False
        self.blood_splat_timer = 0

    def attack(self, target, map_surface):
        if target.hp > 0:
            target.take_damage(10, self.x, self.y, map_surface)

    def chase(self, target, map_surface):
        if self.alive and target.alive:
            self_center_x = self.x + self.tile_size // 2
            self_center_y = self.y + self.tile_size // 2
            target_center_x = target.x + target.tile_size // 2
            target_center_y = target.y + target.tile_size // 2

            dx = target_center_x - self_center_x
            dy = target_center_y - self_center_y
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < 200:
                if distance > target.tile_size:
                    step_x = self.speed * dx / distance * 2
                    step_y = self.speed * dy / distance * 2
                    new_x = self.x + step_x
                    new_y = self.y + step_y

                    if self.map_data.is_walkable(int(new_x), int(new_y), self.tile_size, self.tile_size):
                        self.x, self.y = new_x, new_y
                        if abs(dx) > abs(dy):
                            self.direction = 3 if dx > 0 else 1
                        else:
                            self.direction = 2 if dy > 0 else 0
                        self.moving = True
                if distance < target.tile_size:
                    self.attack(target, map_surface)

# Function to check if position is valid for NPC placement
def is_position_valid(x, y, npcs, map_data):
    new_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
    if any(new_rect.colliderect(npc.get_rect()) for npc in npcs):
        return False
    return map_data.is_walkable(x, y, TILE_SIZE, TILE_SIZE)

def loading_screen(screen):
    font = pygame.font.SysFont('Arial', 36)
    loading_text = font.render("Loading...", True, (255, 255, 255))
    screen.fill((0, 0, 0))
    screen.blit(loading_text, (SCREEN_WIDTH // 2 - loading_text.get_width() // 2, SCREEN_HEIGHT // 2 - loading_text.get_height() // 2))
    pygame.display.flip()

# Define the default dialog tree
template_dialog_tree = {
    "start": {
        "text": "...",
        "options": [
            {
                "text": "...",
                "response": {
                    "text": "..."
                },
                "options": [
                    {
                        "text": "...",
                        "response": {
                            "text": "..."
                        },
                        "options": [
                            {
                                "text": "...",
                                "response": {
                                    "text": "..."
                                }
                            },
                            {
                                "text": "...",
                                "response": {
                                    "text": "..."
                                }
                            }
                        ]
                    },
                    {
                        "text": "...",
                        "response": {
                            "text": "..."
                        }
                    }
                ]
            }]
    }
}

# load default dialog tree from a file
def load_dialog_tree(filename):
    try:
        with open(filename, 'r') as file:
            dialog_tree = json.load(file)
            return dialog_tree
    except Exception as e:
        print("Error loading dialog tree:", e)
        return None

default_dialog_tree = load_dialog_tree("dialog_tree.json")

# Modify the API call function to use the default dialog tree in case of an error
def call_openai_api():
    return None
    api_url = "https://api.openai.com/v1/chat/completions"
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        print("API key not found.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": f"Generate a dialog tree of an evil wizard npc in a world where the chickens are being attacked by the pigs, but make it like animal farm. Output in json using this structure, make sure there are multiple options: {template_dialog_tree}"
            }
        ]
    }

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        print(response.json()["choices"][0]["message"]["content"])
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        print("API call failed:", e)
        return None  # Return None in case of failure

# Adjust the EvilWizard class to initialize with the dialog tree
class EvilWizard(NPC):
    def __init__(self, x, y, tileset, tile_size, blood_splat_frames, dialog_tree):
        super().__init__(x, y, tileset, tile_size, 3, 1, blood_splat_frames)
        self.dialog_tree = dialog_tree
        self.start_dialog = dialog_tree['start']
        self.current_dialog = self.start_dialog
        self.current_options = self.start_dialog.get('options', [])
        self.speech_text = self.current_dialog['text']
        self.speech_options = self.current_dialog.get('options', [])
        self.speech_duration = 180
        self.speech_timer = 0  # Set to 0 to disable by default
        self.end_dialog_timer = None
        self.end_dialog_duration = 500

        print(f"Initial dialog: {self.speech_text}")
        for i, option in enumerate(self.speech_options):
            print(f"Initial Option {i + 1}: {option['text']}")

    def load_frames(self):
        frames = [[], [], [], []]  # Down, left, right, up
        for direction in range(4):
            for frame in range(3):  # Only 3 frames per direction
                rect = pygame.Rect(frame * self.tile_size, direction * 64, self.tile_size, 64)
                frames[direction].append(self.tileset.subsurface(rect))
        return frames

    def talk(self, player):
        self.speech_text = self.current_dialog['text']
        self.speech_options = self.current_options
        self.speech_timer = self.speech_duration  # Set the timer to enable speech

    def is_player_close(self, player, range):
        distance = ((self.x - player.x) ** 2 + (self.y - player.y) ** 2) ** 0.5
        return distance < range

    def draw(self, screen, offset_x, offset_y, font):
        super().draw(screen, offset_x, offset_y)
        if self.speech_timer > 0:
            wrapped_text = self.wrap_text(self.speech_text, font, 500)
            bubble_width = max(line.get_width() for line in wrapped_text) + 10
            bubble_height = sum(line.get_height() for line in wrapped_text) + 10
            bubble_x = self.x - offset_x + self.tile_size // 2 - bubble_width // 2
            bubble_y = self.y - offset_y - bubble_height - 10
            pygame.draw.rect(screen, (0, 0, 0), (bubble_x, bubble_y, bubble_width, bubble_height))  # White background
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x, bubble_y, bubble_width, bubble_height), 2)  # Black border

            text_y = bubble_y + 5
            for line in wrapped_text:
                screen.blit(line, (bubble_x + 5, text_y))
                text_y += line.get_height()

            option_y = bubble_y + bubble_height + 5
            for i, option in enumerate(self.speech_options):
                option_text = f"{i + 1}. {option['text']}"
                option_surface = font.render(option_text, True, (0, 0, 0))  # Black text
                option_bubble_width = option_surface.get_width() + 10
                option_bubble_height = option_surface.get_height() + 10
                option_bubble_x = bubble_x
                option_bubble_y = option_y
                pygame.draw.rect(screen, (255, 255, 255), (option_bubble_x, option_bubble_y, option_bubble_width, option_bubble_height))  # White background
                pygame.draw.rect(screen, (0, 0, 0), (option_bubble_x, option_bubble_y, option_bubble_width, option_bubble_height), 2)  # Black border
                screen.blit(option_surface, (option_bubble_x + 5, option_bubble_y + 5))
                option_y += option_bubble_height + 5

            self.speech_timer -= 1

        if not self.speech_options and self.current_dialog != self.start_dialog:
            if self.end_dialog_timer is None:
                self.end_dialog_timer = 0
            self.end_dialog_timer += 1
            if self.end_dialog_timer >= self.end_dialog_duration:
                self.current_dialog = self.start_dialog
                self.current_options = self.start_dialog.get('options', [])
                self.talk(None)

    def handle_input(self, key):
        if self.speech_options and self.speech_timer > 0:
            option_index = key - pygame.K_1
            if 0 <= option_index < len(self.speech_options):
                selected_option = self.speech_options[option_index]

                if 'options' not in selected_option:
                    self.speech_options = []
                    self.current_options = []
                    self.end_dialog_timer = None
                    self.current_dialog = selected_option['response']
                else:
                    self.speech_timer = self.speech_duration  # Reset the timer when a new dialog is set

                    self.current_dialog = selected_option['response']
                    self.current_options = selected_option['options']
                    self.talk(None)

                    print(f"Selected Option: {selected_option['text']}")
                    print(f"New dialog: {self.current_dialog['text']}")
                    for i, option in enumerate(self.current_options):
                        print(f"New Option {i + 1}: {option['text']}")

    def wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            width, _ = font.size(' '.join(current_line))
            if width > max_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]

        lines.append(' '.join(current_line))
        return [font.render(line, True, (255, 255, 255)) for line in lines]

def draw_debug_info(screen, font, character, map_data):
    tile_x = character.x // TILE_SIZE
    tile_y = character.y // TILE_SIZE
    tile_id = map_data.map_data[tile_y][tile_x]
    debug_text = f'Tile X: {tile_x}, Tile Y: {tile_y}, Tile ID: {tile_id}'
    text_surface = font.render(debug_text, True, (255, 255, 255))
    screen.blit(text_surface, (SCREEN_WIDTH - text_surface.get_width() - 10, 10))

def draw_clock(screen, font, game_time):
    minutes = (game_time // 60) % 24
    seconds = game_time % 60
    time_str = f'{minutes:02}:{seconds:02}'
    text_surface = font.render(time_str, True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))

def draw_night_overlay(screen, alpha):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(alpha)
    overlay.fill(NIGHT_COLOR)
    screen.blit(overlay, (0, 0))

def is_daytime(game_time):
    return game_time % (2 * DAY_DURATION) < DAY_DURATION

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Barnyard Chaos")
    clock = pygame.time.Clock()

    # Initialize font
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 18)

    # Show loading screen
    loading_screen(screen)

    # Call the OpenAI API
    dialog_tree_json = call_openai_api()

    if dialog_tree_json:
        try:
            dialog_tree = json.loads(dialog_tree_json)
        except json.JSONDecodeError:
            print("Failed to decode JSON, using default dialog tree")
            print(dialog_tree_json)
            dialog_tree = default_dialog_tree
    else:
        dialog_tree = default_dialog_tree

    game_map = Map('map.csv', tileset, default_tile)
    blood_splat_frames = [blood_splat_tileset.subsurface(pygame.Rect(i * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)) for i in range(13)]
    character = Character(character_tileset, character_sword, blood_splat_frames, 2000, 1500)

    # Load the cow tileset (4x4 tileset, 128px tiles)
    cow_tile_size = 128
    cow_speed = 1
    cows = []

    # Load the chicken tileset (4x4 tileset, 32px tiles)
    chicken_tile_size = 32
    chicken_speed = 1
    chickens = []

    # Load the pig tileset (4x4 tileset, 128px tiles)
    pig_tile_size = 128
    pig_speed = 1
    pigs = []

    # Create some cows
    for _ in range(5):
        while True:
            cow_x = random.randint(0, MAP_WIDTH * TILE_SIZE - cow_tile_size)
            cow_y = random.randint(0, MAP_HEIGHT * TILE_SIZE - cow_tile_size)
            if is_position_valid(cow_x, cow_y, cows, game_map):
                cows.append(NPC(cow_x, cow_y, cow_tileset, cow_tile_size, 4, cow_speed, blood_splat_frames))
                break

    # Create some chickens
    for _ in range(50):
        while True:
            chicken_x = random.randint(0, MAP_WIDTH * TILE_SIZE - chicken_tile_size)
            chicken_y = random.randint(0, MAP_HEIGHT * TILE_SIZE - chicken_tile_size)
            if is_position_valid(chicken_x, chicken_y, chickens, game_map):
                chickens.append(NPC(chicken_x, chicken_y, chicken_tileset, chicken_tile_size, 4, chicken_speed, blood_splat_frames))
                break

    # Create some pigs
    for _ in range(10):
        while True:
            pig_x = random.randint(0, MAP_WIDTH * TILE_SIZE - pig_tile_size)
            pig_y = random.randint(0, MAP_HEIGHT * TILE_SIZE - pig_tile_size)
            if is_position_valid(pig_x, pig_y, pigs, game_map):
                pigs.append(NPC(pig_x, pig_y, pig_tileset, pig_tile_size, 4, pig_speed, blood_splat_frames))
                break

    # Create the evil wizard
    wizard_tile_size = 48
    evil_wizard = EvilWizard(1500, 1500, wizard_tileset, wizard_tile_size, blood_splat_frames, dialog_tree)

    # Initialize game time
    game_time = 0

    chicken_spawn_position = find_tile_position(game_map, CHICKEN_SPAWN_TILE_ID)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mouse_x, mouse_y = event.pos
                chicken_x = mouse_x + character.offset_x
                chicken_y = mouse_y + character.offset_y
                if is_position_valid(chicken_x, chicken_y, chickens, game_map):
                    chickens.append(NPC(chicken_x, chicken_y, chicken_tileset, chicken_tile_size, 4, chicken_speed, blood_splat_frames))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                character.attack()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                evil_wizard.talk(character)  # Trigger wizard talk manually
            elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
                evil_wizard.handle_input(event.key)

        keys = pygame.key.get_pressed()
        character.update(keys, game_map)

        screen.fill((0, 0, 0))
        screen.blit(game_map.surface, (-character.offset_x, -character.offset_y))
        character.draw(screen)
        character.update_attack(cows + chickens + pigs + [evil_wizard], game_map.surface)

        for npc_list in [cows, chickens, pigs]:
            for npc in npc_list:
                npc.update(game_map, cows + chickens + pigs + [evil_wizard], pygame.Rect(character.x, character.y, character.width, character.height))
                npc.draw(screen, character.offset_x, character.offset_y)

        # Make pigs chase and attack chickens
        if is_daytime(game_time):
            for pig in pigs:
                if pig.alive:
                    closest_chicken = None
                    closest_distance = float('inf')
                    for chicken in chickens:
                        if chicken.alive:
                            distance = ((pig.x - chicken.x) ** 2 + (pig.y - chicken.y) ** 2) ** 0.5
                            if distance < closest_distance:
                                closest_distance = distance
                                closest_chicken = chicken
                    if closest_chicken and closest_distance < 200:
                        pig.chase(closest_chicken, game_map.surface)

        evil_wizard.update(game_map, cows + chickens + pigs, pygame.Rect(character.x, character.y, character.width, character.height))
        evil_wizard.draw(screen, character.offset_x, character.offset_y, font)

        # Check if wizard is close to the player
        if evil_wizard.is_player_close(character, 100):  # Example range of 100 pixels
            evil_wizard.talk(character)

        draw_debug_info(screen, font, character, game_map)
        draw_clock(screen, font, game_time)

        # Apply night overlay if necessary
        if game_time % (2 * DAY_DURATION) >= DAY_DURATION:
            #night
            if game_time % DAY_DURATION > DAY_DURATION - TRANSITION_DURATION:
                #sunrise
                alpha = int(200 * (DAY_DURATION - (game_time % DAY_DURATION)) / TRANSITION_DURATION)
            else:
                #print("night")
                alpha = 200
            draw_night_overlay(screen, alpha)
        else:
            #daytime
            if game_time % DAY_DURATION > DAY_DURATION - TRANSITION_DURATION:
                #sunset
                alpha = int(200 * ((game_time % DAY_DURATION) - (DAY_DURATION - TRANSITION_DURATION)) / TRANSITION_DURATION)
            else:
                #print("day")
                alpha = 0
            draw_night_overlay(screen, alpha)


        if is_daytime(game_time) and game_time % DAY_DURATION == 0 and chicken_spawn_position:
            chicken_x, chicken_y = chicken_spawn_position
            chicken_y += TILE_SIZE
            if is_position_valid(chicken_x, chicken_y, chickens, game_map):
                for _ in range(1):
                    chicken = NPC(chicken_x, chicken_y, chicken_tileset, chicken_tile_size, 4, chicken_speed, blood_splat_frames)
                    chicken.fleeing = True
                    chickens.append(chicken)
    

        pygame.display.flip()
        clock.tick(60)
        game_time = (game_time + 1) % (2 * DAY_DURATION)

    pygame.quit()

if __name__ == '__main__':
    main()
