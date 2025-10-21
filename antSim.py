"""
Instructions for installing Pygame: https://www.pygame.org/wiki/GettingStarted

Overview:
- Imports: Import necessary libraries (Pygame for graphics and random for ant movement).
- Initialization: Initialize Pygame, set up the game window, and define colors.
- Ant class: Create an Ant class that inherits from pygame.sprite.Sprite.
             This class defines the ant's appearance, movement, and behavior.
- Create ants: Create a group of ants and initialize their positions randomly.
- Game loop: The main game loop handles events, updates the ants' positions, and
             draws them on the screen.

Ideas for Enhancement:
- Food: Add food sources that ants can collect and bring back to a nest.
- Pheromones: Implement pheromone trails that ants follow to find food and the nest.
- Different ant types: Create different types of ants with specialized roles (e.g., workers, soldiers).
- Obstacles: Add obstacles that ants must navigate around.
- Improved movement: Make the ant movement more realistic using steering behaviors or other algorithms.
"""

import pygame
import random
import math

# Initialize Pygame
pygame.init()

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# --- Simulation Parameters ---
TOTAL_ANTS = 40
WORKER_RATIO = 0.8  # 80% of ants will be workers
ANT_SPEED = 1.5       # Slower speed for more realistic movement
ANT_TURN_SPEED = 5.0    # How quickly ants can turn (degrees per frame)

FOOD_PILES = 12
FOOD_AMOUNT_PER_PILE = 80

PHEROMONE_STRENGTH = 255  # How long pheromones last (in frames)
PHEROMONE_DROP_RATE = 10  # Ant can drop a pheromone every 10 frames

# --- Ant State Constants ---
STATE_SEEKING_FOOD = 0
STATE_RETURNING_TO_NEST = 1
STATE_WANDERING = 2 # For soldiers

# --- Colors ---
BLACK = (20, 20, 20)
WHITE = (255, 255, 255)
RED = (255, 0, 0)      # Ant carrying food
GREEN = (0, 150, 0)     # Food
BLUE = (0, 0, 200)      # Nest
GREY = (100, 100, 100)   # Obstacles
PHEROMONE_COLOR = (0, 150, 255) # Pheromone trail
SOLDIER_COLOR = (255, 220, 0) # Bright yellow for soldiers

# --- Screen Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Complex Ant Simulation")
clock = pygame.time.Clock()

# --- Helper Function ---
def get_angle_to(p1, p2):
    """Calculates the angle in degrees from point p1 to point p2. The ant then uses this angle to steer"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx))

# --- Pheromone Class ---
class Pheromone(pygame.sprite.Sprite):
    """ Represents a pheromone drop. Fades over time. """
    def __init__(self, x, y):
        super().__init__()
        # Create a 3x3 pixel surface
        self.image = pygame.Surface((3, 3))
        self.image.fill(PHEROMONE_COLOR)
        self.rect = self.image.get_rect(center=(x, y))
        self.strength = PHEROMONE_STRENGTH

    def update(self):
        """ Fades the pheromone and removes it if strength is zero. """
        self.strength -= 1
        if self.strength <= 0:
            self.kill()
        else:
            # Update alpha transparency as it fades
            alpha = max(0, min(255, self.strength))
            self.image.set_alpha(alpha)

# --- Food Class ---
class Food(pygame.sprite.Sprite):
    """ Represents a pile of food that ants can take from. """
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((12, 12))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(center=(x, y))
        self.amount = FOOD_AMOUNT_PER_PILE

    def take_chunk(self):
        """ Called when an ant collides with the food. """
        self.amount -= 1
        if self.amount <= 0:
            self.kill()

# --- Obstacle Class ---
class Obstacle(pygame.sprite.Sprite):
    """ Represents a solid wall ants must avoid. """
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(GREY)
        self.rect = self.image.get_rect(topleft=(x, y))


# --- Base Ant Class ---
class Ant(pygame.sprite.Sprite):
    """
    Base class for all ants.
    Contains shared logic for movement and obstacle avoidance.
    """
    def __init__(self, x, y, color):
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        
        self.x = float(x)
        self.y = float(y)
        
        self.speed = ANT_SPEED
        self.direction = random.uniform(0, 360) # Angle in degrees
        self.turn_speed = ANT_TURN_SPEED

    def steer(self, target_angle):
        """ Gradually turns the ant towards a target angle. """
        # Find the shortest way to turn
        diff = (target_angle - self.direction + 180) % 360 - 180
        
        if abs(diff) < self.turn_speed:
            self.direction = target_angle
        elif diff > 0:
            self.direction += self.turn_speed
        else:
            self.direction -= self.turn_speed
        
        # Keep direction between 0-360
        self.direction %= 360

    def move(self, obstacle_group):
        """ Moves the ant forward and handles obstacle avoidance. """
        # Store old position in case of collision
        old_x, old_y = self.x, self.y
        
        # Calculate new position based on direction and speed
        rad = math.radians(self.direction)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed
        self.rect.center = (self.x, self.y)

        # 1. Screen Boundary Check (Bounce)
        if self.x <= 0 or self.x >= SCREEN_WIDTH:
            self.direction = 180 - self.direction
            self.x = old_x
        if self.y <= 0 or self.y >= SCREEN_HEIGHT:
            self.direction = -self.direction
            self.y = old_y
            
        self.rect.center = (self.x, self.y)

        # 2. Obstacle Collision Check (Bounce)
        if pygame.sprite.spritecollide(self, obstacle_group, False):
            self.x, self.y = old_x, old_y # Revert position
            self.direction += random.uniform(90, 270) # Turn randomly
            self.rect.center = (self.x, self.y)


# --- Worker Ant Class ---
class WorkerAnt(Ant):
    """
    Inherits from Ant.
    This ant seeks food, brings it home, and follows/leaves pheromones.
    """
    def __init__(self, x, y, nest_rect):
        super().__init__(x, y, BLACK)
        self.nest_rect = nest_rect
        self.state = STATE_SEEKING_FOOD
        self.pheromone_cooldown = 0
    
    def drop_pheromone(self, pheromone_group, all_sprites):
        """ Drops a pheromone at the current location. """
        if self.pheromone_cooldown <= 0:
            p = Pheromone(self.x, self.y)
            all_sprites.add(p)
            pheromone_group.add(p)
            self.pheromone_cooldown = PHEROMONE_DROP_RATE
        else:
            self.pheromone_cooldown -= 1

    def update(self, food_group, pheromone_group, obstacle_group, all_sprites):
        target = None
        if self.state == STATE_SEEKING_FOOD:
            # 1. Try to find pheromones
            # (Simple version: find any pheromone within 50px)
            for p in pheromone_group:
                dist = math.hypot(p.rect.centerx - self.x, p.rect.centery - self.y)
                if dist < 50:
                    target = p.rect.center
                    break # Follow the first one it "smells"
            
            # 2. If no pheromones, try to find food
            if target is None and food_group:
                closest_food = min(food_group, 
                                   key=lambda f: math.hypot(f.rect.centerx - self.x, f.rect.centery - self.y))
                dist = math.hypot(closest_food.rect.centerx - self.x, closest_food.rect.centery - self.y)
                
                # Only "see" food if it's within 100 pixels
                if dist < 100:
                    target = closest_food.rect.center

            # 3. Check for collision with food
            collided_food = pygame.sprite.spritecollide(self, food_group, False)
            if collided_food:
                self.state = STATE_RETURNING_TO_NEST
                self.image.fill(RED)  # Carrying food
                collided_food[0].take_chunk()
        
        elif self.state == STATE_RETURNING_TO_NEST:
            target = self.nest_rect.center
            self.drop_pheromone(pheromone_group, all_sprites)

            # Check for collision with nest
            if self.rect.colliderect(self.nest_rect):
                self.state = STATE_SEEKING_FOOD
                self.image.fill(BLACK) # Drop off food
                self.direction += 180 # Turn around

        # --- Movement Logic ---
        if target:
            # Steer towards target
            target_angle = get_angle_to(self.rect.center, target)
            self.steer(target_angle)
        else:
            # Wander: slightly change direction
            self.direction += random.uniform(-self.turn_speed, self.turn_speed)

        # Finally, move and avoid obstacles
        self.move(obstacle_group)


# --- Soldier Ant Class ---
class SoldierAnt(Ant):
    """
    Inherits from Ant.
    This ant just wanders and avoids obstacles.
    """
    def __init__(self, x, y):
        super().__init__(x, y, SOLDIER_COLOR) 
        self.state = STATE_WANDERING

    def update(self, food_group, pheromone_group, obstacle_group, all_sprites):
        # Soldiers just wander
        self.direction += random.uniform(-self.turn_speed, self.turn_speed)
        
        # Move and avoid obstacles
        self.move(obstacle_group)


# --- Legend Drawing Function ---
def draw_legend(screen, font):
    """ Draws the game legend in the top-left corner. """
    start_x = 10
    start_y = 10
    line_height = 25
    box_width = 15  # Width of the box to draw graphics in
    
    # Helper list of items to draw
    # (color, size, text)
    legend_items = [
        (BLACK, (5, 5), ": Worker Ant (Seeking)"),
        (RED, (5, 5), ": Worker Ant (Carrying)"),
        # --- *** CHANGED THIS LINE *** ---
        (SOLDIER_COLOR, (5, 5), ": Soldier Ant"),
        (GREEN, (12, 12), ": Food Pile"),
        (BLUE, (12, 12), ": Nest"),
        (GREY, (12, 12), ": Obstacle"),
        (PHEROMONE_COLOR, (3, 3), ": Pheromone Trail")
    ]
    
    current_y = start_y
    for color, size, text in legend_items:
        # Calculate Y position to center the graphic vertically in the line
        y_pos = current_y + (line_height - size[1]) // 2
        
        # Draw the graphic
        pygame.draw.rect(screen, color, (start_x, y_pos, size[0], size[1]))
        
        # Render and draw the text
        text_surf = font.render(text, True, BLACK)
        screen.blit(text_surf, (start_x + box_width + 5, current_y))
        
        # Move down to the next line
        current_y += line_height


# --- Main Game Function ---
def main():
    
    # Define the nest
    nest_rect = pygame.Rect(SCREEN_WIDTH // 2 - 20, SCREEN_HEIGHT // 2 - 20, 40, 40)
    
    # Initialize Font
    # We use the default system font, size 24
    legend_font = pygame.font.SysFont(None, 24)
    
    # Create Sprite Groups
    all_sprites = pygame.sprite.Group()
    ant_group = pygame.sprite.Group()
    food_group = pygame.sprite.Group()
    pheromone_group = pygame.sprite.Group()
    obstacle_group = pygame.sprite.Group()

    # Create ants at the nest
    for i in range(TOTAL_ANTS):
        x = nest_rect.centerx + random.randint(-10, 10)
        y = nest_rect.centery + random.randint(-10, 10)
        
        if random.random() < WORKER_RATIO:
            ant = WorkerAnt(x, y, nest_rect)
        else:
            ant = SoldierAnt(x, y)
            
        all_sprites.add(ant)
        ant_group.add(ant)

    # Create food piles
    for _ in range(FOOD_PILES):
        x = random.randint(20, SCREEN_WIDTH - 20)
        y = random.randint(20, SCREEN_HEIGHT - 20)
        food = Food(x, y)
        all_sprites.add(food)
        food_group.add(food)
        
    # Create obstacles
    obs1 = Obstacle(100, 150, 20, 300)
    obs2 = Obstacle(600, 150, 20, 300)
    obs3 = Obstacle(300, 100, 200, 20)
    obs4 = Obstacle(300, 480, 200, 20)
    obstacle_list = [obs1, obs2, obs3, obs4]
    
    for obs in obstacle_list:
        all_sprites.add(obs)
        obstacle_group.add(obs)


    # --- Game Loop ---
    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update ---
        # Note: We must pass all_sprites so ants can add pheromones
        ant_group.update(food_group, pheromone_group, obstacle_group, all_sprites)
        pheromone_group.update() # Makes pheromones fade

        # --- Draw ---
        screen.fill(WHITE)
        
        # Draw all sprites (food, pheromones, obstacles, ants)
        # Pheromones are drawn first so they are "under" the ants
        pheromone_group.draw(screen)
        all_sprites.draw(screen) 
        
        # Draw the nest on top of everything
        pygame.draw.rect(screen, BLUE, nest_rect)
        
        # Draw the legend on top of everything else
        draw_legend(screen, legend_font)
        
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    print("Running antSim.py")
    main()